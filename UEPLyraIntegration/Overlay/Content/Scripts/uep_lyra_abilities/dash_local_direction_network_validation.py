"""Existing real native RPC protocol plus actual local preparation witnesses."""
import atexit
import copy
import sys
import unreal_engine as ue
from .dash_rpc_input_network_validation import Client as RPCClient, Server as RPCServer, delta, payload
from .jump_network_validation import arg
from . import dash_local_direction_mixin as local


class Client(RPCClient):
    def trial_begin_evidence(self):
        self.local_before = copy.deepcopy(local.evidence(self.dash)); self.local_fields_before = payload(self.dash)
    def trial_end_evidence(self):
        after = copy.deepcopy(local.evidence(self.dash))
        self.row["local_direction"] = dict(counters=delta(after, self.local_before), before=self.local_fields_before,
            stored=payload(self.dash), last=after["last"] if self.profile == "Python" else None)
    def finalize(self):
        super().finalize()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_LOCAL_DIRECTION_SHUTDOWN_"+self.report["status"].upper())


class Server(RPCServer):
    def trial_begin_evidence(self):
        self.local_before = copy.deepcopy(local.evidence(self.owners[self.current["target"]]["ability"]))
    def trial_end_evidence(self):
        self.current["local_direction_counters"] = delta(local.evidence(self.owners[self.current["target"]]["ability"]), self.local_before)
    def finalize(self):
        super().finalize()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_LOCAL_DIRECTION_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPDashLocalDirectionNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPDashLocalDirectionNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
