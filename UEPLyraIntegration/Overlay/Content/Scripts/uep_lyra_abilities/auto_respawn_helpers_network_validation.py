"""Native authority damage/restart, two real owners; files only schedule/ack."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from . import auto_respawn_helpers_mixin as policy
from .auto_respawn_helpers_validation import Validation as Native, instances, specs, native_state, counters
from .auto_respawn_helpers_contract import NETWORK_PLAN, require
from .jump_network_validation import Server as PlayingFixture, PEERS, arg

TRIALS, TOTAL = len(NETWORK_PLAN)*2, len(NETWORK_PLAN)*4


def token(root, name, run, position=None):
    row = read_json(root/name)
    if row is None: return None
    require(row["run_id"] == run, "foreign AutoRespawn helper fixture run")
    return row if position is None or row["position"] == position else None


def owner_state(controller):
    from uep_lyra_world.effect_pad_mixin import ability_system
    asc = ability_system(controller.get_controlled_pawn())
    ability, = instances(asc, ue.load_class(policy.CLASS))
    return dict(native=native_state(controller), specs=specs(asc), profile=str(ue.get_mixin_profile(ability)),
        helper_counts=policy.instance_snapshot(ability), auto_active=bool(ability.get_property("bIsActive")))


def finalize_network(value, server=False):
    value.report["policy_shutdown"] = policy.snapshot()
    if value.report["status"] == "awaiting_shutdown": value.report["status"] = "passed"
    value.write()
    marker = "UEP_AUTO_RESPAWN_HELPERS_NETWORK_" if server else "UEP_AUTO_RESPAWN_HELPERS_SHUTDOWN_"
    (ue.log if value.report["status"] == "passed" else ue.log_error)(marker+value.report["status"].upper())


class Client(Native):
    def __init__(self, path, peer, run):
        super().__init__(path)
        self.peer, self.run, self.root, self.position = peer, run, Path(path).parent, -1
        self.require_auto_active, self.require_local_playing_phase = False, False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, foreign_cases=[],
            local_damage_applied=False, local_ability_activation_called=False, gameplay_state_delivered_by_files=False,
            native_rpc_bypassed=False, packet_loss_tested=False, travel_rejoin_tested=False, authority_phase_gate_observed=False)

    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is not None:
            require(gate["native_playing_phase"], "native AutoRespawn Playing gate missing")
            self.report["authority_phase_gate_observed"] = True
            Native.ready(self)

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        require(str(bridge.call_function("CaptureSnapshot").NetMode) == "Client", "not a real AutoRespawn client")
        self.report.update(player_id=int(self.controller.PlayerState.PlayerId), native_net_mode="Client")
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, peer=self.peer, player_id=self.report["player_id"]))
        self.enter("idle")

    def arm(self, command):
        self.is_owner = command["target"] == self.peer
        if self.is_owner and not self.attach(self.world, self.controller): return
        self.position, self.command = command["position"], command
        if self.is_owner:
            self.index, self.name, self.profile = command["index"], command["name"], command["profile"]
            ue.set_mixin_profile(self.ability, self.profile)
            self.before = policy.instance_snapshot(self.ability)
            self.old_pawn, self.old_death = self.pawn.get_path_name(), self.death
            self.switched = self.paused = self.unpaused = False
            self.row = dict(living_query=self.query(), old_pawn=self.old_pawn,
                health_before=float(self.health.call_function("GetHealth")), original_delay=float(self.ability.RespawnDelayDuration),
                native_type_preserved=self.ability.get_class().get_path_name() == policy.CLASS,
                native_auto_respawn_active=bool(self.ability.get_property("bIsActive")),
                native_net_policy=int(self.ability.NetExecutionPolicy), native_security_policy=int(self.ability.NetSecurityPolicy),
                native_owner_role=int(self.pawn.call_function("GetLocalRole")), profile_switched=False,
                native_pause_observed=False, native_death_active_observed=False, specs_before=copy.deepcopy(self.original_specs),
                native_authority_before=self.authority_state())
            self.enter("death")
        else:
            self.foreign_before = owner_state(self.controller); self.enter("foreign")
        atomic_write(self.root/(self.peer+"-armed.json"), dict(run_id=self.run, peer=self.peer, position=self.position))

    def await_native_death(self):
        require(time.monotonic()-self.phase_started < 20, "owning client did not observe real lethal death")
        if self.health.call_function("GetHealth") != 0 or not self.old_death.get_property("bIsActive"): return
        self.trial_started = self.game_time()
        self.row.update(health_after_damage=0., dead_query=self.query(), native_death_active_observed=True,
            native_authority_at_death=self.authority_state())
        self.report["real_lethal_gas_damage"] = True
        self.enter("respawn")

    def complete_trial(self):
        self.row.update(position=self.position, target=self.peer, index=self.index, name=self.name, profile=self.profile)
        self.report["cases"].append(copy.deepcopy(self.row))
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-ack.json"), dict(run_id=self.run, peer=self.peer,
            position=self.position, index=self.index, row=copy.deepcopy(self.row)))
        self.write(); self.enter("idle")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 470, "AutoRespawn client total timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "death": self.await_native_death()
            elif self.phase == "respawn":
                require(time.monotonic()-self.phase_started < 30, "AutoRespawn owner restart timeout")
                self.observe()
            elif self.phase == "foreign":
                require(owner_state(self.controller) == self.foreign_before, "foreign death changed local owner state/helper Profile/specs")
                if token(self.root, "trial-complete.json", self.run, self.position) is not None:
                    row = dict(position=self.position, target=self.command["target"], local_owner_unchanged=True)
                    self.report["foreign_cases"].append(row)
                    atomic_write(self.root/(self.peer+"-"+str(self.position)+"-foreign-ack.json"), dict(run_id=self.run,
                        peer=self.peer, position=self.position, row=row))
                    self.write(); self.enter("idle")
            elif token(self.root, "release.json", self.run) is not None: self.finish()
            else:
                command = token(self.root, "arm.json", self.run, self.position+1)
                if command is not None: self.arm(command)
            if time.monotonic()-getattr(self, "last_progress_write", 0.) > 1.:
                self.last_progress_write = time.monotonic()
                atomic_write(self.root/(self.peer+"-status.json"), dict(phase=self.phase, position=self.position,
                    elapsed_seconds=time.monotonic()-self.started, native_readiness=self.report.get("last_readiness"),
                    attach_readiness=self.report.get("attach_readiness")))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finalize(self): finalize_network(self)


class Server(Native):
    def __init__(self, path, run):
        super().__init__(path)
        self.root, self.run, self.position = Path(path).parent, run, 0
        self.require_auto_active, self.contexts, self.restored = False, {}, False
        self.fixture = PlayingFixture(path, run); self.fixture.ability_class = policy.CLASS
        self.report.update(peer="server", run_id=run, network_acceptance=True, player_ids={},
            server_waited_for_client_process_exit=False, all_owners_restored=False, owner_restoration={},
            owners_restored_before_client_release=False,
            gameplay_state_delivered_by_files=False, native_rpc_bypassed=False,
            packet_loss_tested=False, travel_rejoin_tested=False)
        self.enter("setup")

    def setup(self):
        if not self.fixture.playing_gate: self.fixture.wait_playing()
        elif not self.fixture.owners: self.fixture.setup()
        else:
            self.world = self.fixture.world
            self.bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
            self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"])
            self.enter("prepare")

    def prepare(self):
        self.target, self.index = PEERS[self.position//TRIALS], self.position % TRIALS
        require(time.monotonic()-self.phase_started < 20, "native AutoRespawn authority prepare timeout")
        if self.target in self.contexts:
            context = self.contexts[self.target]
            self.original_profile, self.original_specs, self.original_delay = context["profile"], context["specs"], context["delay"]
        else:
            for field in ("original_profile", "original_specs", "original_delay"):
                if hasattr(self, field): delattr(self, field)
        controller = self.fixture.owners[self.target]["controller"]
        if not self.attach(self.world, controller) or not self.respawn_ready(): return
        if self.target not in self.contexts:
            self.contexts[self.target] = dict(profile=self.original_profile, specs=self.original_specs,
                delay=self.original_delay, ability=self.ability, asc=self.asc, controller=controller)
        self.other_peer = PEERS[1] if self.target == PEERS[0] else PEERS[0]
        self.other = self.fixture.owners[self.other_peer]["controller"]
        self.other_before = owner_state(self.other)
        ue.set_mixin_profile(self.ability, ("BlueprintFallback", "Python")[self.index % 2])
        atomic_write(self.root/"arm.json", dict(run_id=self.run, position=self.position, target=self.target,
            index=self.index, name=NETWORK_PLAN[self.index//2], profile=("BlueprintFallback", "Python")[self.index % 2]))
        self.enter("armed")

    def respawn_ready(self):
        rows = [row for row in self.bridge.call_function("CapturePlayerSnapshots") if int(row.PlayerId) == int(self.controller.PlayerState.PlayerId)]
        return len(rows) == 1 and rows[0].bHealthReady and rows[0].Health > 0 and not rows[0].bDamageImmune

    def complete_trial(self):
        self.row.update(position=self.position, target=self.target, index=self.index, name=self.name, profile=self.profile,
            foreign_owner_unchanged=owner_state(self.other) == self.other_before)
        atomic_write(self.root/"trial-complete.json", dict(run_id=self.run, position=self.position))
        self.enter("ack")

    def acknowledge(self):
        require(time.monotonic()-self.phase_started < 20, "native AutoRespawn owner/foreign ack timeout")
        own = token(self.root, self.target+"-"+str(self.position)+"-ack.json", self.run, self.position)
        foreign = token(self.root, self.other_peer+"-"+str(self.position)+"-foreign-ack.json", self.run, self.position)
        if own is None or foreign is None: return
        require((own["peer"], own["index"], foreign["peer"]) == (self.target, self.index, self.other_peer), "wrong native helper acknowledgement identity")
        self.row.update(owner_ack=own, foreign_ack=foreign)
        self.report["cases"].append(copy.deepcopy(self.row)); self.write()
        ue.log("UEP_AUTO_RESPAWN_HELPERS_NETWORK_CASE_OBSERVED "+str(self.position)+"/"+self.target)
        self.position += 1; self.enter("release" if self.position == TOTAL else "prepare")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 470, "AutoRespawn authority total timeout: "+self.phase)
            if self.phase == "setup": self.setup()
            elif self.phase == "prepare": self.prepare()
            elif self.phase == "armed":
                require(time.monotonic()-self.phase_started < 20, "native AutoRespawn clients did not arm")
                if all(token(self.root, peer+"-armed.json", self.run, self.position) is not None for peer in PEERS): Native.begin(self)
            elif self.phase == "respawn":
                require(time.monotonic()-self.phase_started < 30, "authority native restart timeout")
                self.observe()
            elif self.phase == "ack": self.acknowledge()
            elif self.phase == "release":
                self.restore_owners()
                self.report["owners_restored_before_client_release"] = True
                atomic_write(self.root/"release.json", dict(run_id=self.run))
                exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                if all(row is not None and row["exit_code"] == 0 for row in exits):
                    self.report["server_waited_for_client_process_exit"] = True; self.finish()
            if self.phase in ("respawn", "ack"):
                require(owner_state(self.other) == self.other_before, "authority death changed foreign owner native state/helper counts")
            atomic_write(self.root/"server-status.json", dict(run_id=self.run, phase=self.phase, position=self.position,
                elapsed_seconds=time.monotonic()-self.started, native_playing=self.fixture.playing_gate,
                authority_readiness=self.fixture.report.get("authority_readiness"), attach_readiness=self.report.get("attach_readiness")))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def restore_owners(self):
        if self.restored: return
        for peer, context in self.contexts.items():
            ability = context["ability"]; ue.set_mixin_profile(ability, context["profile"])
            state = native_state(context["controller"])
            restored = dict(profile=str(ue.get_mixin_profile(ability)) == context["profile"],
                specs=specs(context["asc"]) == context["specs"], delay=float(ability.RespawnDelayDuration) == context["delay"],
                alive=state is not None and state["health"] > 0 and state["death"] == 0)
            self.report["owner_restoration"][peer] = restored
        self.report["all_owners_restored"] = set(self.contexts) == set(PEERS) and all(all(row.values()) for row in self.report["owner_restoration"].values())
        require(self.report["all_owners_restored"], "native AutoRespawn owners not restored")
        self.report["original_profile_restored"] = self.report["original_specs_restored"] = True
        self.restored = True

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.restore_owners()
        except Exception: error = (error or "")+traceback.format_exc()
        # After actual client exits their Controllers are destroyed. Restoration
        # above is idempotent; never re-read dead ownership through Native.finish.
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write()
        (ue.log_error if error else ue.log)("UEP_AUTO_RESPAWN_HELPERS_NETWORK_"+("FAILED "+error if error else "READY"))
        ue.request_exit()

    def finalize(self): finalize_network(self, server=True)


if any(value.startswith("-UEPAutoRespawnHelpersNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPAutoRespawnHelpersNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
