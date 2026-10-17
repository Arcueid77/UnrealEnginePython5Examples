"""Reuse accepted late-readiness scenes with actual Python possession factories."""
import atexit
import copy
import sys
import unreal_engine as ue
from .inventory_wait_validation import Validation as WaitValidation
from .possessed_observation import Transition
from .possessed_contract import validate
from . import possessed_mixin as policy


class Validation(WaitValidation):
    marker = "UEP_CHARACTER_POSSESSED"
    transition_type = Transition
    validate_report = staticmethod(validate)

    def __init__(self, result):
        super().__init__(result)
        self.report.update(experience_ready_factory_migrated=True, native_possession_ingress_tested=True,
            possession_event_manually_called_by_fixture=False, begin_play_business_migrated=False)

    def begin(self):
        if self.trial is None:
            self.report.update(natural_startup_possession=copy.deepcopy(policy.evidence(self.pawn)), natural_startup_controller=self.controller.get_path_name())
        super().begin()


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterPossessedResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
