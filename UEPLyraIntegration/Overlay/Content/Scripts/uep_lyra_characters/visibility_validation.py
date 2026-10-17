"""Natural readiness regression plus actual native InitState repeat/cancel trials."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from .possessed_validation import Validation as PossessionValidation
from .visibility_observation import Transition, Trial, SCENARIOS
from .visibility_contract import validate
from . import visibility_mixin as policy


class Validation(PossessionValidation):
    marker = "UEP_CHARACTER_VISIBILITY"
    transition_type = Transition
    validate_report = staticmethod(validate)

    def __init__(self, result):
        super().__init__(result); self.visibility_trial = None; self.visibility_complete = False
        self.report.update(visibility_callback_business_migrated=True, visibility_native_backend="DelayUntilNextTick",
            visibility_python_ticker_registered=False, visibility_physical_pixels_tested=False, visibility_cases=[])

    def begin(self):
        if self.trial is None:
            self.report.update(natural_startup_visibility=copy.deepcopy(policy.evidence(self.pawn)),
                natural_startup_visibility_actor=self.pawn.get_path_name(), natural_startup_hidden=bool(self.pawn.get_property("bHidden")))
        super().begin()

    def start_visibility(self):
        self.visibility_trial = Trial(self.world, SCENARIOS[len(self.report["visibility_cases"])]); self.enter("visibility")

    def tick(self, seconds):
        if not self.finished and self.phase == "visibility":
            try:
                if self.visibility_trial.step():
                    self.report["visibility_cases"].append(copy.deepcopy(self.visibility_trial.row))
                    ue.log(self.marker+"_VISIBILITY_PASSED "+self.visibility_trial.scenario[0]+"/"+self.visibility_trial.scenario[3]); self.visibility_trial = None
                    if len(self.report["visibility_cases"]) == len(SCENARIOS): self.visibility_complete = True; self.finish()
                    else: self.start_visibility()
                return not self.finished
            except Exception:
                self.report["visibility_failed_case"] = copy.deepcopy(getattr(self.visibility_trial, "row", {})); self.finish(traceback.format_exc()); return False
        return super().tick(seconds)

    def finish(self, error=None):
        if self.finished: return
        try:
            if error is None and self.transitions_complete and not self.visibility_complete: self.start_visibility(); return
            if self.visibility_trial is not None: self.visibility_trial.close()
        except Exception: error = (error or "")+traceback.format_exc()
        super().finish(error)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterVisibilityResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
