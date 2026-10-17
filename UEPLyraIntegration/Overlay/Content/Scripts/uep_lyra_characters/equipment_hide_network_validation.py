"""Freeze inventory restoration first; local native hide/undo then release peers."""
import atexit
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from uep_lyra_network_io import atomic_write
from .initial_inventory_network_validation import token
from .begin_play_network_validation import Client as BeginClient, Server as BeginServer
from .equipment_hide_observation import Caller, network_trial
from .equipment_hide_network_contract import client_gate, server_gate


class Scope:
    marker = "UEP_CHARACTER_EQUIPMENT_HIDE"
    def __init__(self, *args):
        super().__init__(*args); self.hide_caller = None; self.hide_done = False
        self.report.update(inherited_equipment_hide_migrated=True, ragdoll_physics_or_animation_migrated=False,
            equipment_hidden_fields_written_directly=False, equipment_hide_replication_tested=False, network_death_hide_ingress_tested=False, network_equipment_hide_cases=[])
    def close_hide_caller(self):
        if self.hide_caller is not None: self.report["equipment_hide_caller_roots"] = self.hide_caller.close()


class Client(Scope, BeginClient):
    validate_report = staticmethod(client_gate)
    def tick(self, seconds):
        if not self.finished and self.phase == "complete" and not self.hide_done:
            try:
                self.hide_caller = Caller()
                self.report["network_equipment_hide_cases"] = [network_trial(self.pawn, self.controller, self.hide_caller, profile, self.peer) for profile in ("BlueprintFallback", "Python")]
                self.close_hide_caller(); self.hide_done = True
                atomic_write(self.root/(self.peer+"-equipment-hide.json"), dict(run_id=self.run, complete=True))
            except Exception: self.finish(traceback.format_exc()); return False
        return super().tick(seconds)
    def finish(self, error=None):
        if not self.finished: self.close_hide_caller()
        super().finish(error)


class Server(Scope, BeginServer):
    validate_report = staticmethod(server_gate)
    def release_clients(self):
        if not self.hide_done:
            if not all(token(self.root, peer+"-equipment-hide.json", self.run) for peer in ("A", "B0")): return
            self.hide_caller = Caller()
            for peer in ("A", "B0"):
                trial = self.trials[peer]
                self.report["network_equipment_hide_cases"].extend(network_trial(trial.pawn, trial.controller, self.hide_caller, profile, peer) for profile in ("BlueprintFallback", "Python"))
            self.close_hide_caller(); self.hide_done = True
        super().release_clients()
    def finish(self, error=None):
        if not self.finished: self.close_hide_caller()
        super().finish(error)


if any(value.startswith("-UEPCharacterEquipmentHideNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterEquipmentHideNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
