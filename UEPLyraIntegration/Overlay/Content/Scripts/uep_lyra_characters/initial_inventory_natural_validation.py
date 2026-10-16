"""Existing real death/Avatar fixture; only observe natural new-Pawn loadouts."""
import atexit
import copy
import sys
import unreal_engine as ue
from .inventory_clear_validation import Validation as Native
from . import initial_inventory_mixin as policy
from .initial_inventory_natural_contract import validate


class Validation(Native):
    def __init__(self, result):
        super().__init__(result)
        self.report.update(additional_character_helper_under_test="AddInitialInventory", add_initial_called_by_fixture=False,
            whole_character_migrated=False)

    def attach(self, world, controller):
        attached = super().attach(world, controller)
        if attached and "natural_startup_python_grant" not in self.report:
            self.report["natural_startup_python_grant"] = copy.deepcopy(policy.evidence(self.pawn))
        return attached

    def end_inventory_evidence(self, row):
        row["new_pawn_initial_inventory"] = copy.deepcopy(policy.evidence(self.controller.get_controlled_pawn()))
        return super().end_inventory_evidence(row)

    def validate_report(self): return validate(self.report)

    def finish(self, error=None):
        finished = self.finished; super().finish(error)
        if not finished and self.finished:
            passed = self.report["status"] == "awaiting_shutdown"
            (ue.log if passed else ue.log_error)("UEP_CHARACTER_LOADOUT_DIFFERENTIAL_"+("PASSED" if passed else "FAILED"))

    def finalize(self):
        super().finalize()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_LOADOUT_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterLoadoutResult=")), None)
if result and "-UEPCharacterLoadoutNatural" in sys.argv:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
