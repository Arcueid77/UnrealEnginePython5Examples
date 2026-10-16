"""Independent local Interface probes on actual server/owner/foreign replicas."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.auto_respawn_helpers_network_validation import token
from uep_lyra_abilities.auto_respawn_helpers_mixin import CLASS as ROOT_ABILITY
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, PEERS, arg
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from .emote_audio_validation import Validation as Software
from .emote_audio_contract import validate


class Peer(Software):
    def __init__(self, path, peer, run):
        super().__init__(path)
        self.root, self.peer, self.run = Path(path).parent, peer, run
        self.require_auto_active = self.require_local_playing_phase = False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, network_software_only=True,
            audio_property_replication_claimed=False, gameplay_state_delivered_by_files=False)

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write(); (ue.log_error if error else ue.log)("UEP_CHARACTER_AUDIO_NETWORK_"+("FAILED "+error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write()
        marker = "UEP_CHARACTER_AUDIO_NETWORK_" if self.peer == "server" else "UEP_CHARACTER_AUDIO_SHUTDOWN_"
        (ue.log if self.report["status"] == "passed" else ue.log_error)(marker+self.report["status"].upper())

    def status(self):
        if time.monotonic()-getattr(self, "last_status", 0.) > 1.:
            self.last_status = time.monotonic()
            atomic_write(self.root/(self.peer+"-status.json"), dict(phase=self.phase, elapsed_seconds=time.monotonic()-self.started))


class Client(Peer):
    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is not None:
            require(gate["native_playing_phase"], "native Character Interface Playing gate missing")
            self.report["authority_phase_gate_observed"] = True; Ready.ready(self)

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        mode = str(bridge.call_function("CaptureSnapshot").NetMode)
        require(mode == "Client", "Character Interface peer is not a real client")
        self.report["native_net_mode"] = mode
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, peer=self.peer, player_id=int(self.controller.PlayerState.PlayerId)))
        self.enter("start")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 280, "Character Interface client timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "start":
                command = token(self.root, "audio-start.json", self.run)
                if command is not None:
                    other = "B0" if self.peer == "A" else "A"
                    self.secondary_player_id = command["player_ids"][other]
                    actors, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("Pawn"))
                    if any(valid(actor.get_property("PlayerState")) and int(actor.get_property("PlayerState").PlayerId) == self.secondary_player_id for actor in actors):
                        self.exercise(); self.cleanup(); self.report["status"] = "awaiting_release"; self.write()
                        atomic_write(self.root/(self.peer+"-audio-done.json"), dict(run_id=self.run, peer=self.peer))
                        self.enter("release")
            elif token(self.root, "audio-release.json", self.run) is not None: self.finish()
            self.status(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False


class Server(Peer):
    def __init__(self, path, run):
        super().__init__(path, "server", run)
        self.fixture = PlayingFixture(path, run); self.fixture.ability_class = ROOT_ABILITY
        self.report.update(server_waited_for_client_process_exit=False, all_local_checks_complete_before_release=False)
        self.enter("setup")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 280, "Character Interface server timeout: "+self.phase)
            if self.phase == "setup":
                if not self.fixture.playing_gate: self.fixture.wait_playing()
                elif not self.fixture.owners: self.fixture.setup()
                else:
                    self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"])
                    self.secondary_player_id = self.report["player_ids"]["B0"]
                    if self.attach(self.fixture.world, self.fixture.owners["A"]["controller"]):
                        self.exercise(); self.cleanup(); self.report["status"] = "awaiting_clients"; self.write()
                        atomic_write(self.root/"audio-start.json", dict(run_id=self.run, player_ids=self.report["player_ids"]))
                        self.enter("clients")
            elif self.phase == "clients":
                if all(token(self.root, peer+"-audio-done.json", self.run) is not None for peer in PEERS):
                    self.report["all_local_checks_complete_before_release"] = True
                    atomic_write(self.root/"audio-release.json", dict(run_id=self.run)); self.enter("exits")
            else:
                exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                if all(row is not None and row["exit_code"] == 0 for row in exits):
                    self.report["server_waited_for_client_process_exit"] = True; self.finish()
            self.status(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False


if any(value.startswith("-UEPCharacterAudioNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterAudioNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
