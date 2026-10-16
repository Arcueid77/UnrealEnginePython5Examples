"""Same production listeners, actual authority and two independently observed owners."""
import atexit
import sys
import unreal_engine as ue
from .auto_respawn_listeners_validation import ListenerEvidence
from .auto_respawn_helpers_network_validation import Client as NativeClient, Server as NativeServer
from .jump_network_validation import arg


class Client(ListenerEvidence, NativeClient): pass
class Server(ListenerEvidence, NativeServer): pass


if "-UEPAutoRespawnListeners" in sys.argv and "-UEPAutoRespawnEvents" not in sys.argv and any(value.startswith("-UEPAutoRespawnHelpersNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPAutoRespawnHelpersNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
