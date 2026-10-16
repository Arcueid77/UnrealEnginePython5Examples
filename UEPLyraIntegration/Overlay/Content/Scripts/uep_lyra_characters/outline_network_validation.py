"""Local material software per world; files carry readiness/exit metadata only."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, arg
from uep_lyra_abilities.auto_respawn_helpers_mixin import CLASS as ABILITY
from .quickbar_input_network_validation import token
from .outline_validation import Validation as Native
from .outline_contract import validate as local, require

PEERS = ("A", "B0")


class Peer(Native):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.root, self.peer, self.run, self.complete = Path(result).parent, peer, run, False
        self.require_auto_active = self.require_local_playing_phase = False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, network_software_only=True,
            gameplay_state_delivered_by_files=False)

    def begin(self):
        Native.begin(self)
        self.fixture_actor.call_function("SetReplicates", False)
        self.report["fixture_actor_replication_disabled"] = not bool(self.fixture_actor.get_property("bReplicates"))
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report.update(native_net_mode=str(bridge.call_function("CaptureSnapshot").NetMode),
            player_id=int(self.controller.PlayerState.PlayerId), native_role=int(self.pawn.call_function("GetLocalRole")))

    def finish(self, error=None):
        if self.finished: return
        if error: return self.exit_native(error)
        try:
            self.cleanup(); self.complete = True
            local(dict(self.report, status="passed", error=None))
            self.report["status"] = "awaiting_release"; self.write()
            atomic_write(self.root/(self.peer+"-outline-done.json"), dict(run_id=self.run))
            self.enter("network-wait")
        except Exception: self.exit_native(traceback.format_exc())

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        if not self.complete:
            try: self.cleanup(); self.complete = True
            except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_OUTLINE_"+("FAILED "+error if error else "NETWORK_READY")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"; local(self.report)
                if self.peer == "server": require(self.report["server_waited_for_client_process_exit"], "outline server exited before clients")
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); marker = "UEP_CHARACTER_OUTLINE_"+("NETWORK_" if self.peer == "server" else "SHUTDOWN_")
        (ue.log if self.report["status"] == "passed" else ue.log_error)(marker+self.report["status"].upper())

    def status(self):
        atomic_write(self.root/(self.peer+"-status.json"), dict(run_id=self.run, phase=self.phase, index=self.index,
            complete=self.complete, elapsed_seconds=time.monotonic()-self.started))


class Client(Peer):
    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is None: return
        require(gate["native_playing_phase"], "outline client bypassed actual Playing"); super().ready()

    def begin(self):
        super().begin()
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300, "outline client native timeout")
            if self.complete:
                if token(self.root, "outline-release.json", self.run) is not None: self.exit_native()
            else: Native.tick(self, seconds)
            self.status(); return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


class Server(Peer):
    def __init__(self, result, run):
        super().__init__(result, "server", run)
        self.fixture = PlayingFixture(result, run); self.fixture.ability_class = ABILITY
        self.released = False
        self.report.update(server_waited_for_client_process_exit=False, all_local_checks_complete_before_release=False,
            cleanup_frozen_before_release=False)

    def ready(self):
        if not self.fixture.playing_gate: self.fixture.wait_playing()
        elif not self.fixture.owners: self.fixture.setup()
        else:
            self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"])
            if self.attach(self.fixture.world, self.fixture.owners["A"]["controller"]): self.begin()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300, "outline server native timeout")
            if self.complete:
                if not self.released and all(token(self.root, peer+"-outline-done.json", self.run) is not None for peer in PEERS):
                    self.report.update(all_local_checks_complete_before_release=True, cleanup_frozen_before_release=True)
                    self.released = True; atomic_write(self.root/"outline-release.json", dict(run_id=self.run))
                if self.released:
                    exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                    if all(value is not None and value["exit_code"] == 0 for value in exits):
                        self.report["server_waited_for_client_process_exit"] = True; self.exit_native()
            else: Native.tick(self, seconds)
            self.status(); return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


if any(value.startswith("-UEPCharacterOutlineNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterOutlineNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
