"""Actual inactive-client AvatarSet startup plus two-owner full-policy regression."""
import atexit
import sys
import unreal_engine as ue
from .auto_respawn_activation_validation import ActivationEvidence
from .auto_respawn_events_network_validation import Client as EventClient, Server as EventServer
from .jump_network_validation import arg


class Client(ActivationEvidence, EventClient): pass
class Server(ActivationEvidence, EventServer): pass


if "-UEPAutoRespawnActivation" in sys.argv and "-UEPCharacterInventory" not in sys.argv and any(value.startswith("-UEPAutoRespawnHelpersNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPAutoRespawnHelpersNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
