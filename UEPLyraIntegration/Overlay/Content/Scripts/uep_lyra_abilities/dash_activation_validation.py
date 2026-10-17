"""Real ASC entry, original/Python plus native crouch; no activation replay."""
import atexit
import copy
import sys
import unreal_engine as ue
from .dash_local_direction_validation import Validation as Local, delta
from .dash_activation_mixin import evidence
from .dash_activation_contract import STANDALONE_TRIALS, standalone


class Validation(Local):
    marker = "UEP_DASH_ACTIVATION"
    def __init__(self, result):
        super().__init__(result); self.plan = STANDALONE_TRIALS
        self.report.update(actual_activation_event_business_migrated=True, native_commit_failure_tested=False,
            crouch_fixture_entry="Character.Crouch")
    def context(self, pawn, controller):
        value = super().context(pawn, controller)
        if value is not None: value["initial_crouched"] = bool(pawn.get_property("bIsCrouched"))
        return value
    def start(self):
        super().start()
        if self.phase == "settle" and self.row["name"] == "crouched-forward": self.current["pawn"].call_function("Crouch", False)
    def intent_name(self): return "forward" if self.row["name"] == "crouched-forward" else super().intent_name()
    def input_snapshot(self):
        value = super().input_snapshot(); value["native_crouched_before"] = bool(self.current["pawn"].get_property("bIsCrouched")); return value
    def trial_begin_evidence(self): self.activation_before = copy.deepcopy(evidence(self.current["ability"]))
    def trial_end_evidence(self):
        after = copy.deepcopy(evidence(self.current["ability"]))
        self.row.update(activation_entry=dict(counters=delta(after, self.activation_before), last=after["last"] if self.row["profile"] == "Python" else None),
            native_crouched_after=bool(self.current["pawn"].get_property("bIsCrouched")))
    def cleanup(self):
        super().cleanup()
        self.report["native_crouch_restored"] = all(bool(value["pawn"].get_property("bIsCrouched")) == value["initial_crouched"]
            for value in getattr(self, "actors", {}).values())
    def validate_report(self): return standalone(self.report)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPDashActivationResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
