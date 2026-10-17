"""Typed BP reference -> Python factory -> native named delegate -> Python result."""
import atexit
import sys
import unreal_engine as ue
from .team_observer_validation import Validation as ObserverValidation
from .team_listener_observation import Context
from .team_listener_contract import validate


class Validation(ObserverValidation):
    context_type = Context
    validate_report = staticmethod(validate)
    marker = "UEP_CHARACTER_LISTENER"

    def __init__(self, result):
        super().__init__(result)
        self.report["listener_factory_orchestration_migrated"] = True


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterListenerResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
