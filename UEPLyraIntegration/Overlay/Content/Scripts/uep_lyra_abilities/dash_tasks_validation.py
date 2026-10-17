"""Real twelve-case native activation plus independent Cue/typed UI and scope proof."""
import atexit
import sys
import unreal_engine as ue
from .dash_activation_validation import Validation as Activation
from .dash_tasks_observation import Observer
from . import dash_tasks_mixin as policy
from .dash_tasks_contract import standalone


class Validation(Activation):
    marker = "UEP_DASH_TASKS"
    def __init__(self, result):
        super().__init__(result)
        self.report.update(dash_task_business_migrated=True, task_callbacks_replayed=False,
            cue_or_ui_producer_replayed=False, original_kismet_delay_retained=True)
    def trial_begin_evidence(self):
        super().trial_begin_evidence()
        if not hasattr(self, "producer"): self.producer = Observer(self.world)
        self.producer.begin(self.current["pawn"], self.current["ability"])
    def trial_end_evidence(self):
        super().trial_end_evidence(); self.row["task_business"] = self.producer.finish()
    def cleanup(self):
        try:
            if hasattr(self, "producer"): self.producer.close(); self.report["producer_shutdown"] = self.producer.shutdown()
        finally:
            super().cleanup(); self.report["task_shutdown"] = policy.snapshot()
    def validate_report(self): return standalone(self.report)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPDashTasksResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
