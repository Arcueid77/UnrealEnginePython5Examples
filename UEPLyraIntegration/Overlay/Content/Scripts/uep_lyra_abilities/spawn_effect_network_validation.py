"""Real ServerInitiated GAS: authority activates, clients only observe native RPC."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_world.effect_pad_mixin import valid
from . import spawn_effect_mixin as policy
from .spawn_effect_validation import Validation as NativeSpawn
from .spawn_effect_contract import require
from .spawn_effect_network_contract import NETWORK_PLAN
from .jump_network_validation import Server as PlayingFixture, arg, PEERS

TOTAL = len(NETWORK_PLAN)*4


def token(root, file, run, position=None):
    value = read_json(root/file)
    if value is None: return None
    require(value["run_id"] == run, "foreign native spawn fixture token")
    return value if position is None or value["position"] == position else None


class Client(NativeSpawn):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.root, self.peer, self.run, self.position = Path(result).parent, peer, run, -1
        self.plan, self.timeout = NETWORK_PLAN, 480.
        self.report.update(peer=peer, run_id=run, foreign_cases=[], local_ability_activation_called=False,
            health_properties_written=False, gameplay_state_delivered_by_files=False, native_rpc_bypassed=False,
            packet_loss_tested=False, travel_rejoin_tested=False, physical_input_tested=False)

    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is not None:
            require(gate["native_playing_phase"], "native spawn Playing gate missing")
            NativeSpawn.ready(self)

    def begin(self):
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        self.report["original_health"] = self.health()
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        self.enter("idle")

    def health(self): return float(self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth"))

    def idle(self):
        if token(self.root, "release.json", self.run) is not None:
            self.exit_native(); return
        command = token(self.root, "arm.json", self.run, self.position+1)
        if command is None: return
        self.position, self.index = command["position"], command["index"]
        require(not self.active() and self.effects() == 0 and not self.immune() and not self.ignored(), "owner not clean before native spawn arm")
        self.is_owner = command["target"] == self.peer
        if self.is_owner:
            self.prepare_trial()  # Profile/foreign-lock fixture only; NEVER activate on a client.
            self.action_done = True
            self.enter("await-start")
        else:
            self.foreign_before = policy.instance_snapshot(self.ability)
            self.enter("foreign")
        atomic_write(self.root/(self.peer+"-armed.json"), dict(run_id=self.run, position=self.position))

    def await_start(self):
        if not (self.active() and self.effects() == 1 and self.immune() and self.ignored() and
            self.anim.call_function("Montage_IsPlaying", self.ability.SpawnMontage)): return
        self.trial_started = self.game_time()
        self.record_start()
        self.row["native_montage_playing_observed"] = True
        atomic_write(self.root/(self.peer+"-held.json"), dict(run_id=self.run, position=self.position, actual_native_rpc_activation=True))
        self.enter("running")

    def may_capture_end(self): return self.effects() == 0 and self.tasks() == 0 and not self.immune()

    def complete_trial(self):
        self.row.update(position=self.position, index=self.index, name=self.name, profile=self.profile,
            local_ability_activation_called=False, health_unchanged=self.health() == self.report["original_health"])
        self.report["cases"].append(copy.deepcopy(self.row))
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-ack.json"), dict(run_id=self.run, position=self.position))
        self.enter("idle")

    def foreign(self):
        require(not self.active() and self.effects() == 0 and not self.immune() and not self.ignored() and
            capture(self.controller) == self.original_model and self.health() == self.report["original_health"] and
            policy.instance_snapshot(self.ability) == self.foreign_before, "another owner's native spawn changed local state")
        if token(self.root, "trial-complete.json", self.run, self.position) is None: return
        self.report["foreign_cases"].append(dict(position=self.position, original_state_unchanged=True))
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-foreign-ack.json"), dict(run_id=self.run, position=self.position))
        self.enter("idle")

    def tick(self, seconds):
        if self.phase in ("ready", "running", "settle"): return NativeSpawn.tick(self, seconds)
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < self.timeout, "native spawn client timeout: "+self.phase)
            if self.phase in ("await-start", "foreign"): require(time.monotonic()-self.phase_started < 15., "native spawn client phase timeout: "+self.phase)
            {"idle": self.idle, "await-start": self.await_start, "foreign": self.foreign}[self.phase]()
            return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False

    def exit_native(self, error=None):
        if self.finished: return
        NativeSpawn.finish(self, error)

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_SPAWN_EFFECT_SHUTDOWN_"+self.report["status"].upper())


class Server(NativeSpawn):
    def __init__(self, result, run):
        super().__init__(result)
        self.root, self.run, self.position = Path(result).parent, run, 0
        self.plan, self.timeout, self.phase = NETWORK_PLAN, 480., "setup"
        self.fixture = PlayingFixture(result, run); self.fixture.ability_class = policy.CLASS
        self.initials, self.suspended, self.restored = {}, {}, False
        self.report.update(peer="server", run_id=run, player_ids={}, native_initials={},
            server_waited_for_client_process_exit=False, fixture_authority_native_activation=True,
            native_rpc_bypassed=False, gameplay_state_delivered_by_files=False, packet_loss_tested=False,
            travel_rejoin_tested=False, physical_input_tested=False)

    def health(self): return float(self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth"))

    def setup(self):
        if not self.fixture.playing_gate: self.fixture.wait_playing(); return
        if not self.fixture.owners: self.fixture.setup(); return
        for peer in PEERS:
            owner = self.fixture.owners[peer]; controller = owner["controller"]; count = 0
            # Explicit test isolation, using only balanced native stack APIs.
            # No raw IgnoreMoveInput write or broad reset; restore the exact count.
            while controller.call_function("IsMoveInputIgnored"):
                require(count < 16, "unbounded authority input-lock fixture refused")
                controller.call_function("SetIgnoreMoveInput", False); count += 1
            self.suspended[peer] = count
            self.attach(controller, owner["ability"])
            self.initials[peer] = {key: getattr(self, key) for key in ("world", "bridge", "controller", "pawn", "asc", "cls", "ability", "anim",
                "original_model", "original_specs", "original_fraction", "original_profile")}
            self.initials[peer]["original_health"] = self.health()
            self.report["native_initials"][peer] = dict(default_python_on_spawn=True, native_role=int(self.pawn.call_function("GetLocalRole")),
                original_health=self.health(), player_id=owner["player_id"])
        self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"],
            native_input_locks_suspended=dict(self.suspended))
        self.enter("prepare")

    def bind(self, peer):
        for key, value in self.initials[peer].items():
            if key != "original_health": setattr(self, key, value)

    def prepare(self):
        self.target = PEERS[self.position//(len(self.plan)*2)]
        self.index = self.position % (len(self.plan)*2); self.bind(self.target)
        require(not self.active() and not self.immune() and self.effects() == 0 and not self.ignored(), "authority not clean before spawn arm")
        self.other = PEERS[1] if self.target == PEERS[0] else PEERS[0]
        atomic_write(self.root/"arm.json", dict(run_id=self.run, position=self.position, index=self.index, target=self.target,
            name=self.plan[self.index//2], profile=("BlueprintFallback", "Python")[self.index % 2]))
        self.enter("armed")

    def may_perform_action(self):
        held = token(self.root, self.target+"-held.json", self.run, self.position)
        return held is not None and held["actual_native_rpc_activation"]

    def other_unchanged(self):
        saved = self.initials[self.other]; controller, pawn, ability = saved["controller"], saved["pawn"], saved["ability"]
        return (controller.get_controlled_pawn() == pawn and not ability.get_property("bIsActive") and not controller.call_function("IsMoveInputIgnored") and
            capture(controller) == saved["original_model"] and float(pawn.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth")) == saved["original_health"])

    def complete_trial(self):
        self.row.update(position=self.position, index=self.index, target=self.target, name=self.name, profile=self.profile,
            other_owner_unchanged=self.other_unchanged(), health_unchanged=self.health() == self.initials[self.target]["original_health"],
            actual_owner_rpc_start_observed=self.may_perform_action())
        self.completed = copy.deepcopy(self.row)
        atomic_write(self.root/"trial-complete.json", dict(run_id=self.run, position=self.position))
        self.enter("ack")

    def restore(self):
        if self.restored: return
        if self.foreign_owned:
            self.controller.call_function("SetIgnoreMoveInput", False); self.foreign_owned = False
        for peer in self.initials:
            self.bind(peer)
            if self.active(): self.ability.call_function("K2_EndAbility")
            self.ability.set_property("EnableInputAfterTimeFraction", self.original_fraction)
            ue.set_mixin_profile(self.ability, self.original_profile)
            require(self.specs() == self.original_specs and capture(self.controller) == self.original_model and self.effects() == 0 and
                not self.immune() and not self.ignored() and self.health() == self.initials[peer]["original_health"], "authority native spawn original state not restored")
            for index in range(self.suspended[peer]): self.controller.call_function("SetIgnoreMoveInput", True)
            require(self.ignored() == (self.suspended[peer] > 0), "authority input-lock restore differs")
        self.report.update(original_player_restored=True, original_ability_specs_restored=True, original_fraction_restored=True,
            native_input_locks_restored=dict(self.suspended))
        self.restored = True

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < self.timeout, "native spawn authority timeout: "+self.phase)
            if self.phase == "setup": self.setup()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.phase == "prepare": self.prepare()
                elif self.phase == "armed":
                    require(time.monotonic()-self.phase_started < 20., "native spawn clients did not arm")
                    if all(token(self.root, peer+"-armed.json", self.run, self.position) is not None for peer in PEERS): NativeSpawn.begin(self)
                elif self.phase == "running": self.running()
                elif self.phase == "settle": self.settle()
                elif self.phase == "ack":
                    require(time.monotonic()-self.phase_started < 20., "native spawn clients did not acknowledge native cleanup")
                    if token(self.root, self.target+"-"+str(self.position)+"-ack.json", self.run, self.position) is not None and token(self.root, self.other+"-"+str(self.position)+"-foreign-ack.json", self.run, self.position) is not None:
                        self.report["cases"].append(self.completed)
                        ue.log("UEP_SPAWN_EFFECT_NETWORK_CASE_OBSERVED "+str(self.position)+"/"+self.target+"/"+self.name)
                        self.position += 1
                        if self.position == TOTAL:
                            self.restore(); atomic_write(self.root/"release.json", dict(run_id=self.run)); self.enter("release")
                        else: self.enter("prepare")
                elif self.phase == "release":
                    exited = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                    if all(value is not None and value["exit_code"] == 0 for value in exited):
                        self.report["server_waited_for_client_process_exit"] = True; self.finish()
                if self.phase in ("running", "settle", "ack"):
                    require(self.other_unchanged(), "native spawn changed foreign authority owner")
            atomic_write(self.root/"server-status.json", dict(run_id=self.run, phase=self.phase, position=self.position))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.restore()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_SPAWN_EFFECT_NETWORK_AUTHORITY_"+("FAILED "+error if error else "READY")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_SPAWN_EFFECT_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPSpawnEffectNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPSpawnEffectNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
