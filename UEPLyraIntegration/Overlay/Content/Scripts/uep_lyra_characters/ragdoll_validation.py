"""Prior acceptance plus real native death and typed BP Ragdoll/impulse matrix."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from .equipment_hide_validation import Validation as HideValidation
from .ragdoll_observation import Caller, Trial, NaturalHideTrial, SCENARIOS
from .ragdoll_contract import validate


class Validation(HideValidation):
    marker = "UEP_CHARACTER_RAGDOLL"
    validate_report = staticmethod(validate)
    hide_trial_type = NaturalHideTrial
    def __init__(self, result):
        super().__init__(result); self.ragdoll_trial = self.ragdoll_caller = None; self.ragdoll_complete = False
        self.report.update(ragdoll_orchestration_migrated=True, native_physics_or_animation_implementation_changed=False,
            physics_properties_written_directly=False, ragdoll_cases=[])
    def start_ragdoll(self):
        if self.ragdoll_caller is None: self.ragdoll_caller = Caller()
        self.ragdoll_trial = Trial(self.world, self.ragdoll_caller, SCENARIOS[len(self.report["ragdoll_cases"])]); self.enter("ragdoll")
    def tick(self, seconds):
        if not self.finished and self.phase == "ragdoll":
            try:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.ragdoll_trial.step():
                    self.report["ragdoll_cases"].append(copy.deepcopy(self.ragdoll_trial.row)); self.ragdoll_trial = None
                    if len(self.report["ragdoll_cases"]) == len(SCENARIOS): self.ragdoll_complete = True; self.finish()
                    else: self.start_ragdoll()
                return not self.finished
            except Exception:
                self.report["ragdoll_failed_case"] = copy.deepcopy(getattr(self.ragdoll_trial, "row", {})); self.finish(traceback.format_exc()); return False
        return super().tick(seconds)
    def finish(self, error=None):
        if self.finished: return
        try:
            if error is None and self.hide_complete and not self.ragdoll_complete: self.start_ragdoll(); return
            if self.ragdoll_trial is not None: self.ragdoll_trial.close()
            if self.ragdoll_caller is not None: self.report["ragdoll_caller_roots"] = self.ragdoll_caller.close()
        except Exception: error = (error or "")+traceback.format_exc()
        super().finish(error)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterRagdollResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
