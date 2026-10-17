"""Reuse native role/cleanup coordination; never claim real RepNotify delivery."""
import atexit
import sys
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from .team_observer_network_validation import Client as ObserverClient, Server as ObserverServer
from .legacy_player_info_observation import Context


class Scope:
    context_type = Context
    marker = "UEP_CHARACTER_LEGACY"
    listener_migrated = True

    def __init__(self, *args):
        super().__init__(*args)
        self.report.update(callback_replayed=True, legacy_repnotify_manually_called_by_typed_bp=True, real_legacy_repnotify_ingress_tested=False)


class Client(Scope, ObserverClient): pass
class Server(Scope, ObserverServer): pass


if any(value.startswith("-UEPCharacterLegacyNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterLegacyNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
