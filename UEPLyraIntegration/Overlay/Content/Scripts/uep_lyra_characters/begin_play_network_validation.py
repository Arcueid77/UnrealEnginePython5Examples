"""Natural native startup, not BeginPlay replay or CDO fixture on network."""
import atexit
import copy
import sys
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from .visibility_network_validation import Client as VisibilityClient, Server as VisibilityServer
from .begin_play_network_contract import client_gate, server_gate
from . import begin_play_mixin as policy


class Scope:
    marker = "UEP_CHARACTER_BEGIN_PLAY"
    def __init__(self, *args):
        super().__init__(*args)
        self.report.update(begin_play_business_migrated=True, begin_play_manually_replayed=False, ancestor_construction_death_business_migrated=False,
            fixture_cdo_profile_modified_on_network=False)


class Client(Scope, VisibilityClient):
    validate_report = staticmethod(client_gate)
    def begin(self):
        super().begin()
        if self.trial is not None: self.report["natural_startup_begin_play"] = copy.deepcopy(policy.evidence(self.pawn))


class Server(Scope, VisibilityServer):
    validate_report = staticmethod(server_gate)
    def setup(self):
        super().setup(); self.report["natural_startup_begin_play"] = {peer: copy.deepcopy(policy.evidence(value.pawn)) for peer, value in self.trials.items()}


if any(value.startswith("-UEPCharacterBeginPlayNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterBeginPlayNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
