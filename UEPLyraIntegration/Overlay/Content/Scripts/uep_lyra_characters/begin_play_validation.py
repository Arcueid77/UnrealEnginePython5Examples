"""Fresh native BeginPlay baseline/candidate, plus complete preceding regressions."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from .visibility_validation import Validation as VisibilityValidation
from .begin_play_observation import Trial, SCENARIOS
from .begin_play_contract import validate
from . import begin_play_mixin as policy


class Validation(VisibilityValidation):
    marker = "UEP_CHARACTER_BEGIN_PLAY"
    validate_report = staticmethod(validate)

    def __init__(self, result):
        super().__init__(result); self.begin_trial = None; self.begin_complete = False
        self.report.update(begin_play_business_migrated=True, begin_play_manually_replayed=False, ancestor_construction_death_business_migrated=False, begin_play_cases=[])

    def begin(self):
        if self.trial is None: self.report["natural_startup_begin_play"] = copy.deepcopy(policy.evidence(self.pawn))
        super().begin()

    def start_begin(self): self.begin_trial = Trial(self.world, SCENARIOS[len(self.report["begin_play_cases"])]); self.enter("begin-play")

    def tick(self, seconds):
        if not self.finished and self.phase == "begin-play":
            try:
                if self.begin_trial.step():
                    self.report["begin_play_cases"].append(copy.deepcopy(self.begin_trial.row))
                    ue.log(self.marker+"_STARTUP_PASSED "+self.begin_trial.scenario[0]+"/"+self.begin_trial.scenario[3]); self.begin_trial = None
                    if len(self.report["begin_play_cases"]) == len(SCENARIOS): self.begin_complete = True; self.finish()
                    else: self.start_begin()
                return not self.finished
            except Exception:
                self.report["begin_play_failed_case"] = copy.deepcopy(getattr(self.begin_trial, "row", {})); self.finish(traceback.format_exc()); return False
        return super().tick(seconds)

    def finish(self, error=None):
        if self.finished: return
        try:
            if error is None and self.visibility_complete and not self.begin_complete: self.start_begin(); return
            if self.begin_trial is not None: self.begin_trial.close()
        except Exception: error = (error or "")+traceback.format_exc()
        super().finish(error)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterBeginPlayResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
