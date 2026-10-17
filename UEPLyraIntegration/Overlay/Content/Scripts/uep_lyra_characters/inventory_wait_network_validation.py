"""Keep native replication/identity protocol; report wait scope explicitly."""
import atexit
import sys
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from .inventory_ready_network_validation import Client as ReadyClient, Server as ReadyServer
from .inventory_wait_network_contract import client_gate, server_gate


class WaitScope:
    marker = "UEP_CHARACTER_WAIT"

    def __init__(self, *args):
        super().__init__(*args)
        self.report.update(pending_inventory_wait_migrated=True, native_wait_backend="DelayUntilNextTick", python_wait_ticker_registered=False,
            network_deferred_transitions_tested=False)


class Client(WaitScope, ReadyClient): validate_report = staticmethod(client_gate)
class Server(WaitScope, ReadyServer): validate_report = staticmethod(server_gate)


if any(value.startswith("-UEPCharacterWaitNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterWaitNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
