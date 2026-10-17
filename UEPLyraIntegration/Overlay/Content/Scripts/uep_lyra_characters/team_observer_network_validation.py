"""Native BP listener calls and task lifetimes, not replicated team mutations."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, arg
from uep_lyra_abilities.auto_respawn_helpers_mixin import CLASS as ABILITY
from .quickbar_input_network_validation import token
from .parts_changed_network_validation import native_actors
from .team_observer_observation import Context, query
from .team_observer_network_contract import PLAN
from .team_observer_contract import require

PEERS = ("A", "B0")


class Peer(Ready):
    context_type = Context
    marker = "UEP_CHARACTER_OBSERVER"
    listener_migrated = False
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.root, self.peer, self.run, self.position = Path(result).parent, peer, run, 0
        self.context = None; self.complete = False
        self.require_auto_active = self.require_local_playing_phase = False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, callback_replayed=False, team_properties_written=False,
            observer_delegate_broadcast_by_fixture=False, all_native_observers_cancelled=False, replicated_team_changes_tested=False,
            listener_factory_orchestration_migrated=self.listener_migrated, hardware_output_tested=False, pixels_verified=False, whole_character_migrated=False, full_acceptance=False)

    def status(self): atomic_write(self.root/(self.peer+"-status.json"), dict(run_id=self.run, phase=self.phase, position=self.position, complete=self.complete, elapsed_seconds=time.monotonic()-self.started))

    def clean(self):
        if self.context is not None: self.report["cleanup"] = self.context.cleanup()
        self.complete = True

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        if not self.complete:
            try: self.clean()
            except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)(self.marker+"_"+("FAILED "+error if error else "NETWORK_READY")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        self.write(); marker = self.marker+("_NETWORK_" if self.peer == "server" else "_SHUTDOWN_")
        (ue.log if self.report["status"] == "passed" else ue.log_error)(marker+self.report["status"].upper())


class Client(Peer):
    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is not None:
            require(gate["native_playing_phase"], "team observer client bypassed native Playing"); Ready.ready(self)

    def begin(self):
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"])); self.enter("context")

    def setup_context(self):
        plan = token(self.root, "observer-plan.json", self.run)
        if plan is None: return
        actors = native_actors(self.world, plan["player_ids"])
        if set(actors) != set(PEERS) or not all(query(actor)["team_set"] for actor in actors.values()): return
        self.context = self.context_type(actors, {self.peer: self.controller})
        self.report.update(player_ids=plan["player_ids"], native_net_mode=self.context.net_mode, natural_startup_python_dispatch=self.context.startup)
        atomic_write(self.root/(self.peer+"-context-ready.json"), dict(run_id=self.run)); self.enter("idle")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360, "native team observer client timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "context": self.setup_context()
            elif self.phase == "idle":
                command = token(self.root, "observer-command.json", self.run)
                if command is not None and command["position"] == self.position:
                    self.command = command; self.context.produce(command["target"], command["profile"], command["calls"]); self.enter("device")
                elif self.position == len(PLAN) and token(self.root, "observer-clean.json", self.run) is not None:
                    self.clean(); self.enter("cleanup-gc")
            elif self.phase == "device" and self.context.devices_done():
                self.row = self.context.complete(); self.row.update(name=self.command["name"], target=self.command["target"], calls=self.command["calls"]); self.enter("gc")
            elif self.phase == "gc" and time.monotonic()-self.phase_started >= .15:
                self.report["cases"].append(self.context.settle_collection(self.row)); atomic_write(self.root/(self.peer+"-"+str(self.position)+"-ack.json"), dict(run_id=self.run)); self.position += 1; self.enter("idle")
            elif self.phase == "cleanup-gc" and time.monotonic()-self.phase_started >= .15:
                self.report["cleanup"] = self.context.finalize_collection(); self.write(); atomic_write(self.root/(self.peer+"-done.json"), dict(run_id=self.run)); self.enter("release")
            elif self.phase == "release" and token(self.root, "observer-release.json", self.run) is not None: self.exit_native()
            self.status(); return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


class Server(Peer):
    def __init__(self, result, run):
        super().__init__(result, "server", run)
        self.fixture = PlayingFixture(result, run); self.fixture.ability_class = ABILITY
        self.report.update(server_waited_for_client_process_exit=False, all_cleanup_frozen_before_release=False); self.enter("setup")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360, "native team observer authority timeout: "+self.phase)
            if self.phase == "setup":
                if not self.fixture.playing_gate: self.fixture.wait_playing()
                elif not self.fixture.owners: self.fixture.setup()
                elif self.context is None:
                    self.context = self.context_type({peer: value["controller"].get_controlled_pawn() for peer, value in self.fixture.owners.items()}, {peer: value["controller"] for peer, value in self.fixture.owners.items()})
                    self.report.update(player_ids=self.fixture.report["player_ids"], native_net_mode=self.context.net_mode,
                        native_playing_gate=self.fixture.report["native_playing_gate"], natural_startup_python_dispatch=self.context.startup)
                    atomic_write(self.root/"observer-plan.json", dict(run_id=self.run, player_ids=self.report["player_ids"]))
                elif all(token(self.root, peer+"-context-ready.json", self.run) is not None for peer in PEERS): self.enter("next")
            elif self.phase == "next":
                if self.position == len(PLAN):
                    self.clean(); self.enter("cleanup-gc")
                else:
                    name, target, calls, profile = PLAN[self.position]
                    self.command = dict(run_id=self.run, position=self.position, name=name, target=target, calls=calls, profile=profile)
                    self.context.produce(target, profile, calls); atomic_write(self.root/"observer-command.json", self.command); self.enter("device")
            elif self.phase == "device" and self.context.devices_done():
                self.row = self.context.complete(); self.row.update(name=self.command["name"], target=self.command["target"], calls=self.command["calls"]); self.enter("gc")
            elif self.phase == "gc" and time.monotonic()-self.phase_started >= .15:
                self.report["cases"].append(self.context.settle_collection(self.row)); self.enter("ack")
            elif self.phase == "cleanup-gc" and time.monotonic()-self.phase_started >= .15:
                self.report["cleanup"] = self.context.finalize_collection(); atomic_write(self.root/"observer-clean.json", dict(run_id=self.run)); self.enter("cleanup")
            elif self.phase == "ack":
                require(time.monotonic()-self.phase_started < 15, "native team observer peer ack timeout")
                if all(token(self.root, peer+"-"+str(self.position)+"-ack.json", self.run) is not None for peer in PEERS): self.position += 1; self.enter("next")
            elif self.phase == "cleanup":
                if all(token(self.root, peer+"-done.json", self.run) is not None for peer in PEERS):
                    self.report["all_cleanup_frozen_before_release"] = True; atomic_write(self.root/"observer-release.json", dict(run_id=self.run)); self.enter("exits")
            elif self.phase == "exits":
                exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                if all(value is not None and value["exit_code"] == 0 for value in exits): self.report["server_waited_for_client_process_exit"] = True; self.exit_native()
            self.status(); return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


if any(value.startswith("-UEPCharacterObserverNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterObserverNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
