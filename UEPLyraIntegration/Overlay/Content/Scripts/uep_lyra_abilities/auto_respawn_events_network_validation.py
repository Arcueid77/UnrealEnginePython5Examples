"""Native reliable completion messages, two actual owners, unchanged foreign state."""
import atexit
import sys
import unreal_engine as ue
from .auto_respawn_events_validation import EventEvidence
from .auto_respawn_listeners_network_validation import Client as ListenerClient, Server as ListenerServer
from .jump_network_validation import arg


class Client(EventEvidence, ListenerClient): pass
class Server(EventEvidence, ListenerServer): pass


if "-UEPAutoRespawnEvents" in sys.argv and "-UEPAutoRespawnActivation" not in sys.argv and any(value.startswith("-UEPAutoRespawnHelpersNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPAutoRespawnHelpersNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
