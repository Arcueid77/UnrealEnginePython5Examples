"""Native natural delivery/loadouts and two real missing-controller BP waits."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .initial_inventory_validation import Validation as LoadoutValidation
from .inventory_ready_observation import Trial
from .inventory_ready_contract import validate
from .initial_inventory_contract import require
from .team_observer_observation import proxies
from .outline_validation import gc
from .inventory_clear_mixin import CLASS
from . import inventory_ready_mixin as policy, initial_inventory_mixin as loadout


class Validation(LoadoutValidation):
    trial_type = Trial
    marker = "UEP_CHARACTER_READY"
    validate_report = staticmethod(validate)

    def __init__(self, result):
        super().__init__(result); self.pending_actor = None; self.pending_proxies = []; self.pending_complete = False
        self.report.update(experience_callback_manually_called_by_typed_bp=False, native_experience_factory_signal_tested=True, experience_ready_factory_migrated=False,
            pending_inventory_wait_migrated=False, immediate_inventory_ready_branch_migrated=True, deferred_original_cases=[])

    def begin(self):
        if self.trial is None: self.report["natural_startup_readiness"] = copy.deepcopy(policy.evidence(self.pawn))
        super().begin()

    def start_pending(self):
        profile = ("BlueprintFallback", "Python")[len(self.report["deferred_original_cases"])]
        self.original_proxies = set(proxies())
        self.pending_actor = self.world.actor_spawn(ue.load_class(CLASS), ue.FVector(200000., 200000., 2000.)); self.pending_actor.call_function("SetReplicates", False)
        self.pending_proxies = [value for name, value in proxies().items() if name not in self.original_proxies]
        ue.set_mixin_profile(self.pending_actor, profile)
        self.pending_counts, self.pending_loadout = policy.evidence(self.pending_actor), loadout.evidence(self.pending_actor)
        self.trial.probe.call_function("Grant", self.pending_actor)
        self.pending_row = dict(profile=profile, actor_was_not_rooted=not self.pending_actor.is_rooted())
        self.enter("pending-wait")

    def destroy_pending(self):
        if valid(self.pending_actor): self.pending_actor.call_function("K2_DestroyActor")
        for value in self.pending_proxies:
            if valid(value) and value.call_function("IsActive"): value.call_function("Cancel")
        gc()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300, "native inventory-ready continuation total timeout: "+self.phase)
            if self.phase == "pending-wait":
                if time.monotonic()-self.phase_started >= .2:
                    if not self.trial.probe.capture(self.pending_actor, require_grant=False): return True
                    self.pending_row["readiness_counters"] = copy.deepcopy(self.trial.last_ready_delta)
                    self.pending_row["no_inventory_grant_while_controller_missing"] = self.pending_loadout["python_calls"] == self.pending_loadout["fallback_calls"] == 0
                    self.pending_snapshot = (copy.deepcopy(self.pending_counts), copy.deepcopy(self.pending_loadout))
                    self.destroy_pending(); self.enter("pending-gc")
                return True
            if self.phase == "pending-gc":
                if time.monotonic()-self.phase_started >= .2:
                    self.pending_row.update(owned_actor_destroyed=not valid(self.pending_actor),
                        no_callbacks_or_grants_after_destroy_and_engine_ticks=(self.pending_counts, self.pending_loadout) == self.pending_snapshot,
                        original_live_proxies_preserved=set(proxies()) == self.original_proxies,
                        owned_startup_proxies_collected=all(not valid(value) for value in self.pending_proxies))
                    self.report["deferred_original_cases"].append(self.pending_row)
                    if len(self.report["deferred_original_cases"]) < 2: self.start_pending()
                    else:
                        self.report["owned_experience_proxies_created"] = len(self.trial.probe.owned)
                        self.report["owned_experience_proxies_collected"] = self.trial.probe.collected()
                        self.pending_complete = True; self.finish()
                return not self.finished
            if self.phase == "observe" and not self.trial.capture(): return True
            return super().tick(seconds)
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        if error is None and not self.pending_complete and self.trial is not None:
            self.start_pending(); return
        try:
            if not self.pending_complete: self.destroy_pending()
            if self.trial is not None: self.report["caller_roots"] = self.trial.close_probe()
        except Exception: error = (error or "")+traceback.format_exc()
        super().finish(error)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterReadyResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
