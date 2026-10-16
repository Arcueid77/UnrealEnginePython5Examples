"""Existing native Reset request, not manual invocation of the Character event."""
import atexit
import sys
import unreal_engine as ue
from .lifecycle_validation import LifecycleEvidence
from .lifecycle_contract import validate
from uep_lyra_abilities.auto_respawn_reset_validation import ResetTrials


class Validation(LifecycleEvidence, ResetTrials):
    def prepare_reset(self):
        super().prepare_reset(); self.start_inventory_evidence()

    def complete_reset(self):
        self.end_inventory_evidence(self.row); super().complete_reset()

    def validate_reset_report(self): return validate(self.report, reset=True)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterLifecycleResetResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
