"""Production native startup visibility; preserve the inventory/possession lane."""
import atexit
import copy
import sys
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from .possessed_network_validation import Client as PossessionClient, Server as PossessionServer
from .visibility_network_contract import client_gate, server_gate
from . import visibility_mixin as policy


def snapshot(actor):
    return dict(counters=copy.deepcopy(policy.evidence(actor)), actor=actor.get_path_name(), hidden=bool(actor.get_property("bHidden")))


class Scope:
    marker = "UEP_CHARACTER_VISIBILITY"
    def __init__(self, *args):
        super().__init__(*args)
        self.report.update(visibility_callback_business_migrated=True, visibility_native_backend="DelayUntilNextTick",
            visibility_python_ticker_registered=False, visibility_physical_pixels_tested=False, network_visibility_repeat_destroy_matrix_tested=False)


class Client(Scope, PossessionClient):
    validate_report = staticmethod(client_gate)
    def begin(self):
        super().begin()
        if self.trial is not None: self.report["natural_startup_visibility"] = snapshot(self.pawn)


class Server(Scope, PossessionServer):
    validate_report = staticmethod(server_gate)
    def setup(self):
        super().setup(); self.report["natural_startup_visibility"] = {peer: snapshot(value.pawn) for peer, value in self.trials.items()}


if any(value.startswith("-UEPCharacterVisibilityNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterVisibilityNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
