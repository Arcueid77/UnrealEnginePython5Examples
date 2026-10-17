"""Reuse closed three-world lifecycle; only factory ownership differs."""
import atexit
import sys
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from .team_observer_network_validation import Client as ObserverClient, Server as ObserverServer
from .team_listener_observation import Context


class Client(ObserverClient):
    context_type = Context
    marker = "UEP_CHARACTER_LISTENER"
    listener_migrated = True


class Server(ObserverServer):
    context_type = Context
    marker = "UEP_CHARACTER_LISTENER"
    listener_migrated = True


if any(value.startswith("-UEPCharacterListenerNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterListenerNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
