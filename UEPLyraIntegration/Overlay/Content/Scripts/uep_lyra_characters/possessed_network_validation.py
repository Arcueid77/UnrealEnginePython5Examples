"""Same real inventory/replica protocol, record actual native possession."""
import atexit
import copy
import sys
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from .inventory_wait_network_validation import Client as WaitClient, Server as WaitServer
from .possessed_network_contract import client_gate, server_gate
from . import possessed_mixin as policy


class Scope:
    marker = "UEP_CHARACTER_POSSESSED"
    def __init__(self, *args):
        super().__init__(*args)
        self.report.update(experience_ready_factory_migrated=True, native_possession_ingress_tested=True,
            possession_event_manually_called_by_fixture=False, begin_play_business_migrated=False)


class Client(Scope, WaitClient):
    validate_report = staticmethod(client_gate)
    def begin(self):
        super().begin()
        if self.trial is not None: self.report["natural_startup_possession"] = copy.deepcopy(policy.evidence(self.pawn))


class Server(Scope, WaitServer):
    validate_report = staticmethod(server_gate)
    def setup(self):
        super().setup()
        self.report.update(natural_startup_possession={peer: copy.deepcopy(policy.evidence(value.pawn)) for peer, value in self.trials.items()},
            natural_startup_controllers={peer: value.controller.get_path_name() for peer, value in self.trials.items()})


if any(value.startswith("-UEPCharacterPossessedNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterPossessedNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
