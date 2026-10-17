"""Three native worlds/two owners; helper invocation, not Melee damage/RPC proof."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from .jump_network_validation import Server as PlayingFixture, arg
from .auto_respawn_helpers_mixin import CLASS as RESPAWN
from .auto_respawn_helpers_validation import Validation as Ready, native_state, specs
from .auto_respawn_helpers_network_validation import token
from .melee_hit_montage_validation import Validation
from .melee_hit_montage_contract import require


def net_mode(world):
    return str(ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world).call_function("CaptureSnapshot").NetMode)


class Client(Validation):
    def __init__(self, result, peer, run):
        super().__init__(result); self.peer, self.run, self.root = peer, run, self.path.parent
        self.require_local_playing_phase = False; self.report.update(peer=peer, run_id=run, helper_two_owner_network_tested=True)
    def ready(self):
        if token(self.root, "playing-ready.json", self.run) is not None: Ready.ready(self)
    def begin(self):
        super().begin(); self.report.update(player_id=int(self.controller.PlayerState.PlayerId), native_net_mode=net_mode(self.world))
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
    def complete(self):
        self.cleanup(); atomic_write(self.root/(self.peer+"-melee-complete.json"), dict(run_id=self.run)); self.enter("release")
    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "native Melee helper owner timeout")
            if self.phase == "release":
                if token(self.root, "release.json", self.run) is not None: self.finish()
                return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
        return super().tick(delta)


class Server(Validation):
    def __init__(self, result, run):
        super().__init__(result); self.run, self.root = run, self.path.parent; self.release_issued = False
        self.fixture = PlayingFixture(result, run); self.fixture.ability_class = RESPAWN
        self.report.update(peer="server", run_id=run, helper_two_owner_network_tested=True, server_waited_for_client_process_exit=False,
            all_helper_owners_restored_before_release=False, other_authority_owner_unchanged=False); self.enter("setup")
    def other_state(self):
        from uep_lyra_world.effect_pad_mixin import ability_system
        controller = self.fixture.owners["B0"]["controller"]
        return dict(native=native_state(controller), specs=specs(ability_system(controller.get_controlled_pawn())))
    def complete(self): self.cleanup(); self.enter("release")
    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "native Melee helper authority timeout")
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "setup":
                if not self.fixture.playing_gate: self.fixture.wait_playing()
                elif not self.fixture.owners: self.fixture.setup()
                elif self.attach(self.fixture.world, self.fixture.owners["A"]["controller"]):
                    self.other_before = self.other_state(); self.begin()
                    self.report.update(player_id=int(self.controller.PlayerState.PlayerId), native_net_mode=net_mode(self.world),
                        authority_player_ids={peer: value["player_id"] for peer, value in self.fixture.owners.items()})
                return True
            if self.phase == "release":
                if not self.release_issued:
                    require(self.other_state() == self.other_before, "helper changed other real authority owner")
                    if not all(token(self.root, peer+"-melee-complete.json", self.run) is not None for peer in ("A", "B0")): return True
                    self.report.update(all_helper_owners_restored_before_release=True, other_authority_owner_unchanged=True)
                    atomic_write(self.root/"release.json", dict(run_id=self.run)); self.release_issued = True
                exits = [token(self.root, peer+"-exited.json", self.run) for peer in ("A", "B0")]
                if all(value is not None and value["exit_code"] == 0 for value in exits):
                    self.report["server_waited_for_client_process_exit"] = True; self.finish()
                return not self.finished
            return super().tick(delta)
        except Exception: self.finish(traceback.format_exc()); return False
    def finalize(self):
        super().finalize()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_MELEE_HIT_MONTAGE_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPMeleeHitMontageNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPMeleeHitMontageNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
