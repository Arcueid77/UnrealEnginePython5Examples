"""Retain the closed comparison lifecycle, but explicitly replay a legacy helper."""
import atexit
import sys
import unreal_engine as ue
from .team_observer_validation import Validation as ObserverValidation
from .legacy_player_info_observation import Context
from .legacy_player_info_contract import validate


class Validation(ObserverValidation):
    context_type = Context
    validate_report = staticmethod(validate)
    marker = "UEP_CHARACTER_LEGACY"

    def __init__(self, result):
        super().__init__(result)
        self.report.update(listener_factory_orchestration_migrated=True, callback_replayed=True,
            legacy_repnotify_manually_called_by_typed_bp=True, real_legacy_repnotify_ingress_tested=False)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterLegacyResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
