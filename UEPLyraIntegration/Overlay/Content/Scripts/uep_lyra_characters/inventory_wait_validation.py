"""Native latent resumption, late readiness and repeated BP/Python requests."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from .inventory_ready_validation import Validation as ReadyValidation
from .inventory_wait_contract import validate
from . import inventory_wait_mixin as policy
from .inventory_wait_transitions import Transition, SCENARIOS
from .initial_inventory_contract import require
from .outline_validation import gc


class Validation(ReadyValidation):
    marker = "UEP_CHARACTER_WAIT"
    validate_report = staticmethod(validate)

    def __init__(self, result):
        super().__init__(result)
        self.report.update(pending_inventory_wait_migrated=True, native_wait_backend="DelayUntilNextTick", python_wait_ticker_registered=False,
            native_deferred_transitions_tested=False, readiness_transition_cases=[])
        self.transition = None; self.transitions_complete = False

    def start_pending(self):
        super().start_pending()
        self.pending_wait = policy.evidence(self.pending_actor)

    def tick(self, seconds):
        if not self.finished and self.phase == "transition":
            try:
                if self.transition.step():
                    self.report["readiness_transition_cases"].append(copy.deepcopy(self.transition.row))
                    ue.log(self.marker+"_TRANSITION_PASSED "+self.transition.scenario[0]+"/"+self.transition.scenario[3])
                    self.transition = None
                    if len(self.report["readiness_transition_cases"]) == len(SCENARIOS):
                        self.transitions_complete = True; self.report["native_deferred_transitions_tested"] = True
                        gc(); self.enter("transition-final-gc")
                    else: self.start_transition()
                return True
            except Exception:
                self.report["readiness_transition_failed_case"] = copy.deepcopy(getattr(self.transition, "row", {}))
                self.finish(traceback.format_exc()); return False
        if not self.finished and self.phase == "transition-final-gc":
            if time.monotonic()-self.phase_started >= .2: self.finish()
            return not self.finished
        if not self.finished and self.phase == "pending-wait" and time.monotonic()-self.phase_started >= .2:
            self.pending_row["wait_counters"] = copy.deepcopy(self.pending_wait)
            self.pending_wait_snapshot = copy.deepcopy(self.pending_wait)
        if not self.finished and self.phase == "pending-gc" and time.monotonic()-self.phase_started >= .2:
            self.pending_row["script_wait_quiet_after_destroy"] = self.pending_wait == self.pending_wait_snapshot
        return super().tick(seconds)

    def start_transition(self):
        self.transition = Transition(self.world, self.trial.probe, SCENARIOS[len(self.report["readiness_transition_cases"])])
        self.enter("transition")

    def finish(self, error=None):
        if self.finished: return
        try:
            if error is None and self.pending_complete and not self.transitions_complete:
                self.start_transition(); return
            if self.transition is not None: self.transition.close()
            if self.transitions_complete:
                self.report["owned_experience_proxies_created"] = len(self.trial.probe.owned)
                self.report["owned_experience_proxies_collected"] = self.trial.probe.collected()
        except Exception: error = (error or "")+traceback.format_exc()
        super().finish(error)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterWaitResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
