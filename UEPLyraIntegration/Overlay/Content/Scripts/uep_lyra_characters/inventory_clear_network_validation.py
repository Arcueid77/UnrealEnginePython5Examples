"""Same original Character BP helper, native authority clear and two real owners."""
import atexit
import sys
import unreal_engine as ue
from .inventory_clear_validation import CharacterEvidence
from uep_lyra_abilities.auto_respawn_activation_network_validation import Client as ParentClient, Server as ParentServer
from uep_lyra_abilities.jump_network_validation import arg


class Client(CharacterEvidence, ParentClient): pass
class Server(CharacterEvidence, ParentServer): pass


if "-UEPCharacterInventory" in sys.argv and any(value.startswith("-UEPAutoRespawnHelpersNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPAutoRespawnHelpersNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
