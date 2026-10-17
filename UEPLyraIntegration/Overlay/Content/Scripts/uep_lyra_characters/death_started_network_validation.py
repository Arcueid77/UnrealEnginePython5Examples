"""Keep the accepted two-owner inventory/local-body lane under the new profile."""
import atexit
import sys
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from .ragdoll_network_validation import Client as RagdollClient, Server as RagdollServer
from .death_started_network_contract import client_gate, server_gate


class Scope:
    marker = "UEP_CHARACTER_DEATH_STARTED"
    def __init__(self, *args):
        super().__init__(*args)
        self.report.update(death_started_business_migrated=True, death_receiver_called_by_fixture=False, death_native_delay_backend="Delay",
            death_python_ticker_or_rooting=False, empty_death_endpoint_retained=True, network_death_receiver_ingress_tested=False)


class Client(Scope, RagdollClient): validate_report = staticmethod(client_gate)
class Server(Scope, RagdollServer): validate_report = staticmethod(server_gate)


if any(value.startswith("-UEPCharacterDeathStartedNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterDeathStartedNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
