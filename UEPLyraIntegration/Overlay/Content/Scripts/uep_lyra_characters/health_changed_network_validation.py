"""One real server + two clients; files only coordinate test phases/identities."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, arg
from uep_lyra_abilities.auto_respawn_helpers_mixin import CLASS as ABILITY
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from .quickbar_input_network_validation import token
from .health_changed_observation import Context, OwnedAI, health
from .health_changed_contract import CLASS, require
from .health_changed_network_contract import PLAN, PEERS


def native_actors(world, player_ids):
    actors, = ue.find_class("GameplayStatics").get_cdo().call_function("GetAllActorsOfClass", world, ue.load_class(CLASS))
    result = {}
    for actor in actors:
        state = actor.get_property("PlayerState")
        if not valid(state): continue
        if state.call_function("GetPlayerName") == "UEPHealthSenseFixture": result["AI"] = actor
        else:
            for peer, player_id in player_ids.items():
                if int(state.PlayerId) == player_id: result[peer] = actor
    return result


class Peer(Ready):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.root, self.peer, self.run, self.position = Path(result).parent, peer, run, 0
        self.context = self.owned = None; self.complete = False
        self.require_auto_active = self.require_local_playing_phase = False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, callback_replayed=False, health_properties_written=False,
            sense_report_called_by_fixture=False, component_delegate_broadcast_by_fixture=False, gameplay_state_delivered_by_files=False,
            pixels_verified=False, whole_character_migrated=False, full_acceptance=False, retained_character_class=CLASS)

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
        if self.owned is not None:
            try: self.report["owned_fixture_cleanup"] = self.owned.close()
            except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_HEALTH_"+("FAILED "+error if error else "NETWORK_READY")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        self.write()
        marker = "UEP_CHARACTER_HEALTH_NETWORK_" if self.peer == "server" else "UEP_CHARACTER_HEALTH_SHUTDOWN_"
        (ue.log if self.report["status"] == "passed" else ue.log_error)(marker+self.report["status"].upper())


class Client(Peer):
    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is not None:
            require(gate["native_playing_phase"], "health client bypassed native Playing"); Ready.ready(self)

    def begin(self):
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"])); self.enter("context")

    def setup_context(self):
        plan = token(self.root, "health-plan.json", self.run)
        if plan is None: return
        actors = native_actors(self.world, plan["player_ids"])
        if set(actors) != {"A", "B0", "AI"} or not all(health(actor) > 20 for actor in actors.values()): return
        self.context = Context(actors, {self.peer: self.controller})
        self.report.update(player_ids=plan["player_ids"], native_net_mode=self.context.net_mode, natural_startup_python_dispatch=self.context.startup)
        atomic_write(self.root/(self.peer+"-context-ready.json"), dict(run_id=self.run)); self.enter("idle")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360, "native health client timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "context": self.setup_context()
            elif self.phase == "idle":
                command = token(self.root, "health-command.json", self.run)
                if command is not None and command["position"] == self.position and self.context.prepared(command["name"]):
                    self.command = command; self.context.arm(command["name"], command["profile"])
                    atomic_write(self.root/(self.peer+"-"+str(self.position)+"-armed.json"), dict(run_id=self.run)); self.enter("observe")
                elif self.position == len(PLAN) and token(self.root, "health-clean.json", self.run) is not None:
                    self.clean(); self.write(); atomic_write(self.root/(self.peer+"-health-done.json"), dict(run_id=self.run)); self.enter("release")
            elif self.phase == "observe":
                require(time.monotonic()-self.phase_started < 12, "native replicated health delegate timeout")
                issued = token(self.root, "health-issued-"+str(self.position)+".json", self.run)
                if issued is not None and self.context.seen() and time.monotonic()-self.phase_started >= .2:
                    self.report["cases"].append(copy.deepcopy(self.context.row()))
                    atomic_write(self.root/(self.peer+"-"+str(self.position)+"-ack.json"), dict(run_id=self.run)); self.enter("restore")
            elif self.phase == "restore":
                if self.context.restored() and token(self.root, "health-restored-"+str(self.position)+".json", self.run) is not None:
                    atomic_write(self.root/(self.peer+"-"+str(self.position)+"-restored.json"), dict(run_id=self.run))
                    self.position += 1; self.enter("idle")
            elif self.phase == "release" and token(self.root, "health-release.json", self.run) is not None: self.exit_native()
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
            require(time.monotonic()-self.started < 360, "native health authority timeout: "+self.phase)
            if self.phase == "setup":
                if not self.fixture.playing_gate: self.fixture.wait_playing()
                elif not self.fixture.owners: self.fixture.setup()
                elif self.owned is None: self.owned = OwnedAI(self.fixture.world)
                elif self.owned.ready() and self.context is None:
                    actors = {peer: value["controller"].get_controlled_pawn() for peer, value in self.fixture.owners.items()}; actors["AI"] = self.owned.pawn
                    self.context = Context(actors, {peer: value["controller"] for peer, value in self.fixture.owners.items()}, self.owned)
                    self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"], native_net_mode=self.context.net_mode,
                        natural_startup_python_dispatch=self.context.startup)
                    atomic_write(self.root/"health-plan.json", dict(run_id=self.run, player_ids=self.report["player_ids"]))
                elif self.context is not None and all(token(self.root, peer+"-context-ready.json", self.run) is not None for peer in PEERS): self.enter("next")
            elif self.phase == "next":
                if self.position == len(PLAN):
                    self.clean(); atomic_write(self.root/"health-clean.json", dict(run_id=self.run)); self.enter("cleanup")
                else:
                    name, profile = PLAN[self.position]; self.context.prepare(name)
                    self.command = dict(run_id=self.run, position=self.position, name=name, profile=profile)
                    atomic_write(self.root/"health-command.json", self.command); self.enter("armed")
            elif self.phase == "armed":
                require(time.monotonic()-self.phase_started < 15, "native health prepared/profile-arm timeout")
                if all(token(self.root, peer+"-"+str(self.position)+"-armed.json", self.run) is not None for peer in PEERS):
                    require(self.context.prepared(self.command["name"]), "authority native health preparation failed")
                    self.context.arm(self.command["name"], self.command["profile"]); self.context.produce()
                    atomic_write(self.root/("health-issued-"+str(self.position)+".json"), dict(run_id=self.run)); self.enter("ack")
            elif self.phase == "ack":
                require(time.monotonic()-self.phase_started < 15, "native health replica/stimulus ack timeout")
                if self.context.seen() and time.monotonic()-self.phase_started >= .35 and all(token(self.root, peer+"-"+str(self.position)+"-ack.json", self.run) is not None for peer in PEERS):
                    self.report["cases"].append(copy.deepcopy(self.context.row())); self.context.restore()
                    require(self.context.restored(), "native GAS authority health restoration failed")
                    atomic_write(self.root/("health-restored-"+str(self.position)+".json"), dict(run_id=self.run)); self.enter("restore")
            elif self.phase == "restore":
                require(time.monotonic()-self.phase_started < 15, "native health replica restoration timeout")
                if all(token(self.root, peer+"-"+str(self.position)+"-restored.json", self.run) is not None for peer in PEERS):
                    self.position += 1; ue.log("UEP_CHARACTER_HEALTH_NETWORK_CASE_PASSED "+str(self.position)); self.enter("next")
            elif self.phase == "cleanup":
                if all(token(self.root, peer+"-health-done.json", self.run) is not None for peer in PEERS):
                    self.report["all_cleanup_frozen_before_release"] = True
                    atomic_write(self.root/"health-release.json", dict(run_id=self.run)); self.enter("exits")
            elif self.phase == "exits":
                exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                if all(value is not None and value["exit_code"] == 0 for value in exits):
                    self.report["server_waited_for_client_process_exit"] = True; self.exit_native()
            self.status(); return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


if any(value.startswith("-UEPCharacterHealthNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterHealthNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
