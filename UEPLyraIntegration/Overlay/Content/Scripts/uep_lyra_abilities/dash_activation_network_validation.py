"""Existing real two-owner ASC/RPC protocol with actual activation witnesses."""
import atexit
import copy
import sys
import unreal_engine as ue
from .dash_local_direction_network_validation import Client as LocalClient, Server as LocalServer, delta
from .dash_activation_mixin import evidence
from .jump_network_validation import arg


class Client(LocalClient):
    def trial_begin_evidence(self):
        super().trial_begin_evidence(); self.activation_before = copy.deepcopy(evidence(self.dash))
    def trial_end_evidence(self):
        super().trial_end_evidence(); after = copy.deepcopy(evidence(self.dash))
        self.row["activation_entry"] = dict(counters=delta(after, self.activation_before), last=after["last"] if self.profile == "Python" else None)
    def finalize(self):
        super().finalize()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_ACTIVATION_SHUTDOWN_"+self.report["status"].upper())


class Server(LocalServer):
    def trial_begin_evidence(self):
        super().trial_begin_evidence(); self.activation_before = copy.deepcopy(evidence(self.owners[self.current["target"]]["ability"]))
    def trial_end_evidence(self):
        super().trial_end_evidence(); after = copy.deepcopy(evidence(self.owners[self.current["target"]]["ability"]))
        self.current["activation_entry"] = dict(counters=delta(after, self.activation_before), last=after["last"] if self.current["profile"] == "Python" else None)
    def finalize(self):
        super().finalize()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_ACTIVATION_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPDashActivationNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPDashActivationNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
