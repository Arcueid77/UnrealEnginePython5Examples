"""Real two-owner predicted Jump; files schedule tests, not GAS replication."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_bots import isolate_bots
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from . import jump_mixin as policy
from .jump_validation import Validation as NativeJump
from .jump_contract import PLAN, require

PEERS = ("A", "B0")


def arg(prefix):
    return next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))


def counts(before):
    return {key: value-before[key] for key, value in policy.snapshot().items()
            if type(value) is int and key != "active_count"}


class Client(NativeJump):
    def __init__(self, path, peer, run):
        super().__init__(path)
        self.peer, self.run, self.root = peer, run, Path(path).parent
        self.complete, self.minimum_hold_seconds = False, .35
        self.require_combat_ready = True
        self.report.update(peer=peer, run_id=run, network_transport="native GAS and CharacterMovement RPCs",
            packet_loss_tested=False, travel_rejoin_tested=False)

    def ready(self):
        gate = read_json(self.root/"playing-ready.json")
        if gate is None: return
        require(gate["run_id"] == self.run and gate["native_playing_phase"], "foreign/nonplaying readiness gate")
        NativeJump.ready(self)

    def begin(self):
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, peer=self.peer,
            player_id=self.report["player_id"], pawn=self.pawn.get_path_name()))
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def record_trial(self, row, counters):
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run,
            peer=self.peer, index=self.index, row=copy.deepcopy(row), counters=counters))

    def tick(self, delta):
        if self.phase == "network-permit":
            try:
                require(time.monotonic()-self.started < 480., "native network Jump permit timeout")
                permission = read_json(self.root/(self.peer+"-permit.json"))
                if permission is not None:
                    require(permission["run_id"] == self.run, "foreign native Jump permit")
                    if permission["index"] == self.index: NativeJump.begin(self)
                return True
            except Exception: self.finish(traceback.format_exc()); return False
        if self.phase == "network-complete":
            try:
                require(time.monotonic()-self.started < 480., "native network Jump release timeout")
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run, "foreign native Jump release")
                    NativeJump.finish(self)
                return not self.finished
            except Exception: NativeJump.finish(self, traceback.format_exc()); return False
        return NativeJump.tick(self, delta)

    def finish(self, failure=None):
        if failure: return NativeJump.finish(self, failure)
        self.complete = True
        atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")


class Server:
    def __init__(self, path, run):
        self.path, self.root, self.run = Path(path), Path(path).parent, run
        self.started, self.finished, self.position = time.monotonic(), False, 0
        self.owners, self.current = {}, None
        self.playing_fingerprint, self.playing_stable_since, self.playing_gate = None, 0., False
        self.waiting_reason = "native Playing phase and stable combat-ready authority pawns"
        self.report = dict(schema_version=1, status="running", error=None, run_id=run, peer="server", cases=[],
            server_waited_for_client_process_exit=False, full_acceptance=False, packaged_runtime=False,
            physical_input_tested=False, ability_activation_called_by_probe=False, callback_replay=False,
            authoritative_movement_written=False, packet_loss_tested=False, travel_rejoin_tested=False)
        self.statics = ue.find_class("GameplayStatics").get_cdo()

    def wait_playing(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5) or "L_Expanse" not in world.get_name(): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            native = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetWorldSubsystem", world, ue.find_class("LyraGamePhaseSubsystem"))
            if not valid(native) or not native.call_function("IsPhaseActive", GameplayTag(TagName="ShooterGame.GamePhase.Playing")):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            rows = list(bridge.call_function("CapturePlayerSnapshots"))
            # Remote authority Pawns do not bind a local InputComponent.
            # Local-input readiness belongs exclusively to each Client.ready.
            self.report["authority_readiness"] = [dict(player_id=int(row.PlayerId),
                pawn=str(row.PawnPath), health_ready=bool(row.bHealthReady), health=float(row.Health),
                ability_system_ready=bool(row.bAbilitySystemReady), damage_immune=bool(row.bDamageImmune)) for row in rows]
            if len(rows) != 2 or not all(row.bPlayerStateReady and row.bAbilitySystemReady and row.bHealthReady and row.Health > 0 and
                    not row.bDamageImmune for row in rows): continue
            pawns = [ue.find_object(str(row.PawnPath)) for row in rows]
            if not all(valid(pawn) and int(pawn.CharacterMovement.MovementMode) == 1 for pawn in pawns): continue
            fingerprint = sorted((int(row.PlayerId), str(row.PawnPath)) for row in rows)
            if fingerprint != self.playing_fingerprint:
                self.playing_fingerprint, self.playing_stable_since = fingerprint, time.monotonic(); return
            if time.monotonic()-self.playing_stable_since < .5: return
            self.playing_gate = True
            self.report["native_playing_gate"] = dict(native_playing_phase=True, stable_authority_pawns=fingerprint)
            atomic_write(self.root/"playing-ready.json", dict(run_id=self.run, native_playing_phase=True))
            return

    def setup(self):
        ready = {peer: read_json(self.root/(peer+"-ready.json")) for peer in PEERS}
        if not all(ready.values()): return
        require(all(row["run_id"] == self.run for row in ready.values()) and
                len({row["player_id"] for row in ready.values()}) == 2, "native Jump owners are not distinct")
        cls = ue.load_class(getattr(self, "ability_class", policy.CLASS))
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5) or "L_Expanse" not in world.get_name(): continue
            controllers, = self.statics.call_function("GetAllActorsOfClass", world, ue.find_class("LyraPlayerController"))
            found = {}
            for controller in controllers:
                if not valid(controller.PlayerState): continue
                for peer, row in ready.items():
                    if int(controller.PlayerState.PlayerId) != row["player_id"]: continue
                    pawn = controller.get_controlled_pawn()
                    if not valid(pawn): continue
                    asc = ability_system(pawn)
                    if not valid(asc): continue
                    abilities = [value for spec in asc.get_property("ActivatableAbilities").Items
                        if valid(spec.Ability) and spec.Ability.get_class() == cls
                        for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
                    if len(abilities) != 1: continue
                    found[peer] = dict(pawn=pawn, controller=controller, ability=abilities[0], player_id=row["player_id"])
            if set(found) == set(PEERS):
                self.world, self.owners = world, found
                self.report["player_ids"] = {peer: row["player_id"] for peer, row in found.items()}
                return

    def start_case(self):
        peer, index = PEERS[self.position//(len(PLAN)*2)], self.position % (len(PLAN)*2)
        request = read_json(self.root/(peer+"-request.json"))
        if request is None or request["index"] != index: return
        require(request["run_id"] == self.run, "foreign native Jump request")
        if not all(int(owner["pawn"].CharacterMovement.MovementMode) == 1 and
                   not owner["ability"].get_property("bIsActive") for owner in self.owners.values()): return
        profile = ("BlueprintFallback", "Python")[index % 2]
        ability = self.owners[peer]["ability"]
        ue.set_mixin_profile(ability, profile)
        require(str(ue.get_mixin_profile(ability)) == profile, "authority Jump Profile not selected")
        pawn = self.owners[peer]["pawn"]
        require(int(pawn.call_function("GetLocalRole")) == 3, "Jump observer is not authoritative")
        self.current = dict(target=peer, index=index, name=PLAN[index//2], profile=profile,
            native_active_observed=False, max_authority_rise=0., other_owner_stayed_idle=True,
            start_z=float(pawn.get_actor_location().z), authoritative_role=3)
        self.before, self.case_started = policy.snapshot(), time.monotonic()
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        target = self.owners[peer]
        pawn, ability = target["pawn"], target["ability"]
        row["max_authority_rise"] = max(row["max_authority_rise"], float(pawn.get_actor_location().z)-row["start_z"])
        row["native_active_observed"] |= bool(ability.get_property("bIsActive"))
        for name, other in self.owners.items():
            if name != peer:
                point = other["pawn"].get_actor_location()
                native = dict(peer=name, ability_active=bool(other["ability"].get_property("bIsActive")),
                    movement_mode=int(other["pawn"].CharacterMovement.MovementMode),
                    position=[float(getattr(point, key)) for key in ("x", "y", "z")],
                    health=float(other["pawn"].get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth")))
                row["other_owner_stayed_idle"] &= not native["ability_active"] and native["movement_mode"] == 1
                if not row["other_owner_stayed_idle"]:
                    self.report["foreign_owner_failure"] = native
        require(row["other_owner_stayed_idle"], "foreign native owner jumped/activated: "+repr(self.report.get("foreign_owner_failure")))
        ack = read_json(self.root/(peer+"-"+str(row["index"])+"-ack.json"))
        if ack is None or ability.get_property("bIsActive") or int(pawn.CharacterMovement.MovementMode) != 1:
            require(time.monotonic()-self.case_started < 20., "authority/client Jump case did not complete")
            return
        require(ack["run_id"] == self.run and ack["peer"] == peer and ack["index"] == row["index"], "foreign native Jump ack")
        require(row["native_active_observed"] and row["max_authority_rise"] > 20., "client Jump was not observed in native authority GAS/physics")
        row.update(authority_final_inactive=True, authority_final_grounded=True,
            authority_counters=counts(self.before), client=ack)
        self.report["cases"].append(row)
        ue.log("UEP_JUMP_NETWORK_CASE_PASSED "+peer+"/"+str(row["index"]))
        self.position += 1; self.current = None

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native Jump server timeout")
            if not self.playing_gate:
                self.wait_playing()
            elif not self.owners:
                for world in ue.all_worlds():
                    if world.get_world_type() in (1, 3, 5) and "L_Expanse" in world.get_name():
                        isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
                self.setup()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS)*len(PLAN)*2:
                    completed = [read_json(self.root/(peer+"-complete.json")) for peer in PEERS]
                    if all(row is not None and row["run_id"] == self.run for row in completed):
                        atomic_write(self.root/"release.json", dict(run_id=self.run))
                        exits = [read_json(self.root/(peer+"-exited.json")) for peer in PEERS]
                        if all(row is not None and row["exit_code"] == 0 for row in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(ready=bool(self.owners), position=self.position,
                native_playing_gate=self.playing_gate, waiting_reason=self.waiting_reason if not self.playing_gate else None,
                authority_readiness=self.report.get("authority_readiness"), current=self.current,
                elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, failure=None):
        if self.finished: return
        self.finished = True
        self.report.update(status="failed" if failure else "awaiting_shutdown", error=failure)
        atomic_write(self.path, self.report)
        (ue.log_error if failure else ue.log)("UEP_JUMP_NETWORK_READY" if not failure else failure)
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                require(len(self.report["cases"]) == 28 and self.report["server_waited_for_client_process_exit"],
                        "native Jump authority cases/exit barrier incomplete")
                stats = self.report["policy_shutdown"]
                require(stats["activations"] == 14 and stats["scopes_created"] == stats["scopes_closed"] == 14 and
                        stats["active_count"] == 0 and stats["errors"] == [], "authority Jump policy proof/leak")
                self.report["status"] = "passed"
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_JUMP_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPJumpNetworkResult=") for value in sys.argv):
    path, peer, run = arg("-UEPJumpNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(path, run) if peer == "server" else Client(path, peer, run)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
