"""Real native death events, owner replication and passive foreign isolation."""
import atexit
import sys
import unreal_engine as ue
from .lifecycle_validation import LifecycleEvidence
from uep_lyra_abilities.auto_respawn_activation_network_validation import Client as ParentClient, Server as ParentServer
from uep_lyra_abilities.jump_network_validation import arg


class Client(LifecycleEvidence, ParentClient): pass
class Server(LifecycleEvidence, ParentServer): pass


if any(value.startswith("-UEPCharacterLifecycleNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterLifecycleNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
