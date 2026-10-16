"""Two native Reset owners, passive clients, native payload/foreign isolation."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from .auto_respawn_reset_validation import ResetTrials, counts, activation, events
from .auto_respawn_reset_contract import PLAN
from .auto_respawn_helpers_contract import require
from .auto_respawn_helpers_network_validation import token, owner_state, Server as OriginalServer
from .auto_respawn_helpers_validation import Validation
from .auto_respawn_helpers_validation import instances, specs, native_state
from .auto_respawn_helpers_mixin import CLASS
from .jump_network_validation import Server as PlayingFixture, PEERS, arg
from uep_lyra_world.effect_pad_mixin import valid, ability_system

TRIALS, TOTAL = len(PLAN)*2, len(PLAN)*4


def finish_peer(value, error=None):
    if value.finished: return
    value.close_observer(); value.finished = True
    try:
        if value.peer == "server": value.restore_owners()
        elif hasattr(value, "original_profile"):
            ue.set_mixin_profile(value.ability, value.original_profile)
            value.report["original_profile_restored"] = str(ue.get_mixin_profile(value.ability)) == value.original_profile
            value.report["original_specs_restored"] = specs(value.asc) == value.original_specs
    except Exception: error = (error or "")+traceback.format_exc()
    value.report.update(status="failed" if error else "awaiting_shutdown", error=error)
    value.write(); (ue.log_error if error else ue.log)("UEP_AUTO_RESPAWN_RESET_NETWORK_"+("FAILED "+error if error else "READY"))
    ue.request_exit()


def finalize_peer(value):
    value.close_observer()
    value.report["observer_shutdown"] = dict(created=value.observers_created, closed=value.observers_closed, active=int(value.reset_observer is not None))
    if value.report["status"] == "awaiting_shutdown": value.report["status"] = "passed"
    value.write()
    marker = "UEP_AUTO_RESPAWN_RESET_NETWORK_" if value.peer == "server" else "UEP_AUTO_RESPAWN_RESET_SHUTDOWN_"
    (ue.log if value.report["status"] == "passed" else ue.log_error)(marker+value.report["status"].upper())


class Client(ResetTrials):
    def __init__(self, path, peer, run):
        super().__init__(path)
        self.root, self.peer, self.run, self.position = Path(path).parent, peer, run, -1
        self.require_auto_active = self.require_local_playing_phase = self.allow_native_equipment_recovery = False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, foreign_cases=[], local_reset_requests=0,
            local_damage_applied=False, gameplay_state_delivered_by_files=False, native_rpc_bypassed=False, authority_phase_gate_observed=False)

    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is not None:
            require(gate["native_playing_phase"], "actual native Playing gate missing")
            self.report["authority_phase_gate_observed"] = True
            Validation.ready(self)

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        require(str(bridge.call_function("CaptureSnapshot").NetMode) == "Client", "Reset client is not a real native client")
        self.report.update(player_id=int(self.controller.PlayerState.PlayerId), native_net_mode="Client")
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, peer=self.peer, player_id=self.report["player_id"]))
        self.enter("idle")

    def arm(self, command):
        if not self.attach(self.world, self.controller): return
        self.position, self.command = command["position"], command
        self.index, self.name, self.profile = command["index"], command["name"], command["profile"]
        self.is_owner = command["target"] == self.peer
        ue.set_mixin_profile(self.ability, self.profile)
        if self.is_owner: self.prepare_reset(); self.enter("owner-wait")
        else:
            self.foreign_before = owner_state(self.controller)
            self.foreign_activation_before = activation.instance_snapshot(self.ability)
            self.open_observer(); self.enter("foreign")
        atomic_write(self.root/(self.peer+"-armed.json"), dict(run_id=self.run, peer=self.peer, position=self.position))

    def complete_reset(self):
        self.row.update(position=self.position, target=self.peer, index=self.index)
        self.report["cases"].append(copy.deepcopy(self.row))
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-ack.json"), dict(run_id=self.run, peer=self.peer, position=self.position, index=self.index, row=copy.deepcopy(self.row)))
        self.write(); self.enter("idle")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 470, "native Reset client total timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "owner-wait":
                require(time.monotonic()-self.phase_started < 20, "native Reset owning client producer timeout")
                if "pending-long" in self.name and getattr(self, "death_observed_position", None) != self.position:
                    if valid(self.health) and self.health.call_function("GetHealth") == 0 and self.death.get_property("bIsActive"):
                        if "switch" in self.name: ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
                        self.death_observed_position = self.position
                        atomic_write(self.root/(self.peer+"-death-ready.json"), dict(run_id=self.run, peer=self.peer, position=self.position))
                if self.reset_messages:
                    self.row.update(trigger_entry="SendGameplayEventToActor(GameplayEvent.RequestReset)", native_reset_requests=1)
                    self.enter("reset-respawn")
            elif self.phase == "reset-respawn":
                require(time.monotonic()-self.phase_started < 30, "native Reset client respawn timeout")
                self.observe_reset()
            elif self.phase == "foreign":
                require(owner_state(self.controller) == self.foreign_before, "foreign native Reset changed this client's owner state")
                if token(self.root, "trial-complete.json", self.run, self.position) is not None:
                    self.close_observer()
                    row = dict(position=self.position, target=self.command["target"], local_owner_unchanged=True,
                        reset_messages=copy.deepcopy(self.reset_messages), event_messages=copy.deepcopy(self.event_messages),
                        activation_counters=counts(activation, self.ability, self.foreign_activation_before), observer_closed=True)
                    self.report["foreign_cases"].append(row)
                    atomic_write(self.root/(self.peer+"-"+str(self.position)+"-foreign-ack.json"), dict(run_id=self.run, peer=self.peer, position=self.position, row=row))
                    self.write(); self.enter("idle")
            elif token(self.root, "release.json", self.run) is not None: self.finish()
            else:
                command = token(self.root, "arm.json", self.run, self.position+1)
                if command is not None: self.arm(command)
            self.status(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def status(self):
        if time.monotonic()-getattr(self, "last_status", 0.) > 1.:
            self.last_status = time.monotonic()
            atomic_write(self.root/(self.peer+"-status.json"), dict(phase=self.phase, position=self.position, elapsed_seconds=time.monotonic()-self.started,
                readiness=self.report.get("last_readiness"), reset_messages=getattr(self, "reset_messages", [])))

    def finish(self, error=None): finish_peer(self, error)
    def finalize(self): finalize_peer(self)


class Server(ResetTrials):
    def __init__(self, path, run):
        super().__init__(path)
        self.root, self.run, self.peer, self.position = Path(path).parent, run, "server", 0
        self.require_auto_active, self.contexts, self.restored = False, {}, False
        self.fixture = PlayingFixture(path, run); self.fixture.ability_class = CLASS
        self.report.update(peer="server", run_id=run, network_acceptance=True, player_ids={}, owner_restoration={},
            server_waited_for_client_process_exit=False, owners_restored_before_client_release=False, all_owners_restored=False,
            gameplay_state_delivered_by_files=False, native_rpc_bypassed=False)
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
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        require(time.monotonic()-self.phase_started < 20, "native Reset authority readiness timeout")
        context = self.contexts.get(self.target)
        for field, key in (("original_profile", "profile"), ("original_specs", "specs"), ("original_delay", "delay")):
            if context is not None: setattr(self, field, context[key])
            elif hasattr(self, field): delattr(self, field)
        controller = self.fixture.owners[self.target]["controller"]
        if not self.attach(self.world, controller) or not self.respawn_ready(): return
        if context is None: self.contexts[self.target] = dict(profile=self.original_profile, specs=self.original_specs, delay=self.original_delay,
            ability=self.ability, asc=self.asc, controller=controller)
        self.other_peer = PEERS[1] if self.target == PEERS[0] else PEERS[0]
        self.other = self.fixture.owners[self.other_peer]["controller"]
        other_asc = ability_system(self.other.get_controlled_pawn())
        self.other_ability, = instances(other_asc, ue.load_class(CLASS))
        if self.other_peer not in self.contexts:
            self.contexts[self.other_peer] = dict(profile=str(ue.get_mixin_profile(self.other_ability)), specs=specs(other_asc),
                delay=float(self.other_ability.RespawnDelayDuration), ability=self.other_ability, asc=other_asc, controller=self.other)
        ue.set_mixin_profile(self.other_ability, self.profile)
        self.other_before = owner_state(self.other)
        self.other_activation_before = activation.instance_snapshot(self.other_ability)
        atomic_write(self.root/"arm.json", dict(run_id=self.run, position=self.position, target=self.target, index=self.index, name=self.name, profile=self.profile))
        self.enter("armed")

    def respawn_ready(self): return OriginalServer.respawn_ready(self)
    def restore_owners(self): return OriginalServer.restore_owners(self)

    def complete_reset(self):
        self.row.update(position=self.position, target=self.target, index=self.index, foreign_owner_unchanged=owner_state(self.other) == self.other_before,
            foreign_activation_counters=counts(activation, self.other_ability, self.other_activation_before))
        atomic_write(self.root/"trial-complete.json", dict(run_id=self.run, position=self.position)); self.enter("ack")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 470, "native Reset authority total timeout: "+self.phase)
            if self.phase == "setup": self.setup()
            elif self.phase == "prepare": self.prepare()
            elif self.phase == "armed":
                require(time.monotonic()-self.phase_started < 20, "native Reset clients did not arm")
                if all(token(self.root, peer+"-armed.json", self.run, self.position) is not None for peer in PEERS): self.begin_reset()
            elif self.phase == "wait-reset":
                if self.game_time()-self.trial_started >= .3 and token(self.root, self.target+"-death-ready.json", self.run, self.position) is not None: self.trigger_reset()
                require(time.monotonic()-self.phase_started < 20, "owning client did not observe native lethal death before Reset")
            elif self.phase == "reset-respawn":
                require(time.monotonic()-self.phase_started < 30, "native Reset authority restart timeout")
                self.observe_reset()
            elif self.phase == "ack":
                require(time.monotonic()-self.phase_started < 20, "native Reset owner/foreign ack timeout")
                own = token(self.root, self.target+"-"+str(self.position)+"-ack.json", self.run, self.position)
                foreign = token(self.root, self.other_peer+"-"+str(self.position)+"-foreign-ack.json", self.run, self.position)
                if own is not None and foreign is not None:
                    self.row.update(owner_ack=own, foreign_ack=foreign); self.report["cases"].append(copy.deepcopy(self.row)); self.write()
                    self.position += 1; self.enter("release" if self.position == TOTAL else "prepare")
            elif self.phase == "release":
                self.restore_owners(); self.report["owners_restored_before_client_release"] = True
                atomic_write(self.root/"release.json", dict(run_id=self.run))
                exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                if all(row is not None and row["exit_code"] == 0 for row in exits): self.report["server_waited_for_client_process_exit"] = True; self.finish()
            if self.phase in ("wait-reset", "reset-respawn", "ack"):
                require(owner_state(self.other) == self.other_before, "native Reset changed foreign authority owner state")
            Client.status(self); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None): finish_peer(self, error)
    def finalize(self): finalize_peer(self)


if any(value.startswith("-UEPAutoRespawnResetNetworkResult=") for value in sys.argv):
    path, peer, run = arg("-UEPAutoRespawnResetNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(path, run) if peer == "server" else Client(path, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
