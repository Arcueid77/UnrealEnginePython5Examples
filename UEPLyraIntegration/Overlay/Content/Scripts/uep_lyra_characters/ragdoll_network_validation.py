"""Owned local Actors only; do not alter/undo physics on a real player's Pawn."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from uep_lyra_network_io import atomic_write
from .initial_inventory_network_validation import token
from .team_observer_observation import proxies
from .equipment_hide_network_validation import Client as HideClient, Server as HideServer
from .ragdoll_observation import Caller, LocalTrial
from .ragdoll_network_contract import client_gate, server_gate


class Scope:
    marker = "UEP_CHARACTER_RAGDOLL"
    def __init__(self, *args):
        super().__init__(*args); self.ragdoll_trial = self.ragdoll_caller = None; self.ragdoll_done = False; self.ragdoll_start = False
        self.report.update(ragdoll_orchestration_migrated=True, native_physics_or_animation_implementation_changed=False,
            physics_properties_written_directly=False, ragdoll_physics_replication_tested=False,
            network_owner_death_ragdoll_ingress_tested=False, local_ragdoll_cases=[])
    def advance_ragdoll(self, world):
        if self.ragdoll_caller is None: self.ragdoll_caller = Caller()
        if self.ragdoll_trial is None:
            self.ragdoll_trial = LocalTrial(world, self.ragdoll_caller, ("BlueprintFallback", "Python")[len(self.report["local_ragdoll_cases"])])
        if self.ragdoll_trial.step():
            self.ragdoll_trial.row.update(original_active_observer_paths=sorted(self.ragdoll_trial.original), final_active_observer_paths=sorted(proxies()))
            self.report["local_ragdoll_cases"].append(copy.deepcopy(self.ragdoll_trial.row)); self.ragdoll_trial = None
            if len(self.report["local_ragdoll_cases"]) == 2:
                self.close_ragdoll(); self.ragdoll_done = True
        return self.ragdoll_done
    def close_ragdoll(self):
        if self.ragdoll_trial is not None: self.ragdoll_trial.close()
        if self.ragdoll_caller is not None: self.report["ragdoll_caller_roots"] = self.ragdoll_caller.close()


class Client(Scope, HideClient):
    validate_report = staticmethod(client_gate)
    def tick(self, seconds):
        if not self.finished and self.phase == "complete" and self.hide_done and not self.ragdoll_done:
            try:
                if not token(self.root, "ragdoll-start.json", self.run): return super().tick(seconds)
                if self.advance_ragdoll(self.pawn.get_world()): atomic_write(self.root/(self.peer+"-ragdoll.json"), dict(run_id=self.run, complete=True))
                return True
            except Exception: self.finish(traceback.format_exc()); return False
        return super().tick(seconds)
    def finish(self, error=None):
        if not self.finished: self.close_ragdoll()
        super().finish(error)


class Server(Scope, HideServer):
    validate_report = staticmethod(server_gate)
    def release_clients(self):
        if not self.ragdoll_done:
            if not self.ragdoll_start:
                if not all(token(self.root, peer+"-equipment-hide.json", self.run) for peer in ("A", "B0")): return
                # This method is reached only AFTER all24 grants/restores/ACKs.
                # A's own complete phase alone does not imply B0 is finished.
                atomic_write(self.root/"ragdoll-start.json", dict(run_id=self.run, all_inventory_and_hide_peers_ready=True))
                self.ragdoll_start = True
            if not all(token(self.root, peer+"-ragdoll.json", self.run) for peer in ("A", "B0")): return
            if not self.advance_ragdoll(self.trials["A"].pawn.get_world()): return
        super().release_clients()
    def finish(self, error=None):
        if not self.finished: self.close_ragdoll()
        super().finish(error)


if any(value.startswith("-UEPCharacterRagdollNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterRagdollNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
