"""Real existing C++ Reset -> original Character OnReset -> selected helper."""
import atexit
import sys
import unreal_engine as ue
from .inventory_clear_validation import CharacterEvidence
from .inventory_clear_contract import validate_reset
from uep_lyra_abilities.auto_respawn_reset_validation import ResetTrials


class Validation(CharacterEvidence, ResetTrials):
    def prepare_reset(self):
        super().prepare_reset(); self.start_inventory_evidence()

    def complete_reset(self):
        self.end_inventory_evidence(self.row); super().complete_reset()

    def validate_reset_report(self): return validate_reset(self.report)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoRespawnResetResult=")), None)
if result and "-UEPCharacterInventory" in sys.argv:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
