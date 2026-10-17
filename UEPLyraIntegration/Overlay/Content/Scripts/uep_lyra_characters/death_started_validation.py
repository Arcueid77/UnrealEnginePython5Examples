"""Full prior regressions plus actual native Health-death configuration/lifetime."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from .ragdoll_validation import Validation as RagdollValidation
from .death_started_observation import NaturalTrial, Trial, SCENARIOS
from .death_started_contract import validate


class Validation(RagdollValidation):
    marker = "UEP_CHARACTER_DEATH_STARTED"
    validate_report = staticmethod(validate)
    hide_trial_type = NaturalTrial
    def __init__(self, result):
        super().__init__(result); self.death_trial = None; self.death_complete = False
        self.report.update(death_started_business_migrated=True, death_receiver_called_by_fixture=False, death_native_delay_backend="Delay",
            death_python_ticker_or_rooting=False, empty_death_endpoint_retained=True, death_started_cases=[])
    def start_death(self):
        self.death_trial = Trial(self.world, SCENARIOS[len(self.report["death_started_cases"])]); self.enter("death-started")
    def tick(self, seconds):
        if not self.finished and self.phase == "death-started":
            try:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.death_trial.step():
                    self.report["death_started_cases"].append(copy.deepcopy(self.death_trial.row))
                    ue.log(self.marker+"_OBSERVED "+self.death_trial.case+"/"+self.death_trial.scenario[3]); self.death_trial = None
                    if len(self.report["death_started_cases"]) == len(SCENARIOS): self.death_complete = True; self.finish()
                    else: self.start_death()
                return not self.finished
            except Exception:
                self.report["death_started_failed_case"] = copy.deepcopy(getattr(self.death_trial, "row", {})); self.finish(traceback.format_exc()); return False
        return super().tick(seconds)
    def finish(self, error=None):
        if self.finished: return
        try:
            if error is None and self.ragdoll_complete and not self.death_complete: self.start_death(); return
            if self.death_trial is not None: self.death_trial.close()
        except Exception: error = (error or "")+traceback.format_exc()
        super().finish(error)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterDeathStartedResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
