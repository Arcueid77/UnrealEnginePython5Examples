"""Actual two-owner native requests/RPC with task, Cue and local-message witnesses."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from .dash_activation_network_validation import Client as ActivationClient, Server as ActivationServer
from .dash_tasks_observation import Observer
from .jump_network_validation import arg
from . import dash_tasks_mixin as policy
from .dash_tasks_contract import client


class Client(ActivationClient):
    def __init__(self, result, peer, run):
        super().__init__(result, peer, run)
        self.report.update(dash_task_business_migrated=True, task_callbacks_replayed=False,
            cue_or_ui_producer_replayed=False, original_kismet_delay_retained=True)
    def trial_begin_evidence(self):
        super().trial_begin_evidence()
        if not hasattr(self, "producer"): self.producer = Observer(self.world)
        self.producer.begin(self.pawn, self.dash)
    def trial_end_evidence(self):
        super().trial_end_evidence(); self.row["task_business"] = self.producer.finish()
    def cleanup(self):
        try:
            if hasattr(self, "producer"): self.producer.close(); self.report["producer_shutdown"] = self.producer.shutdown()
        finally: super().cleanup(); self.report["task_shutdown"] = policy.snapshot()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; client(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_TASKS_SHUTDOWN_"+self.report["status"].upper())


class Server(ActivationServer):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.report.update(dash_task_business_migrated=True, task_callbacks_replayed=False,
            cue_or_ui_producer_replayed=False, original_kismet_delay_retained=True)
    def trial_begin_evidence(self):
        super().trial_begin_evidence()
        if not hasattr(self, "producer"): self.producer = Observer(self.world)
        actor = self.owners[self.current["target"]]; self.producer.begin(actor["pawn"], actor["ability"])
    def trial_end_evidence(self):
        super().trial_end_evidence(); self.current["task_business"] = self.producer.finish()
    def restore(self):
        try:
            if hasattr(self, "producer"): self.producer.close(); self.report["producer_shutdown"] = self.producer.shutdown()
        finally: super().restore(); self.report["task_shutdown"] = policy.snapshot()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        from uep_lyra_network_io import atomic_write
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_TASKS_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPDashTasksNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPDashTasksNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
