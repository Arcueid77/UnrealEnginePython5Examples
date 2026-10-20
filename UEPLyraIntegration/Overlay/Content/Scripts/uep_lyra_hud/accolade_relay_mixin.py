"""Accolade authority/client forwarding and independent cosmetic notification."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,LyraNotificationMessage
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib

CLASS='/ShooterCore/Accolades/B_AccoladeRelay.B_AccoladeRelay_C'
RECEIVE='UEPAccoladeReceived'
BROADCAST='UEPAccoladeBroadcast'
ROOT='Lyra.ShooterGame.Accolade'
CHANNEL='Lyra.AddNotification.Message'


def evidence(a):
    if not hasattr(a,'_uep_accolade_relay'):a._uep_accolade_relay=dict(python_received=0,fallback_received=0,client_requests=0,cosmetic_broadcasts=0,player_helper_calls=0,diagnostic_fallbacks=0)
    return a._uep_accolade_relay


def player(a,source):
    evidence(a)['player_helper_calls']+=1
    return lib('LyraVerbMessageHelpers').call_function('GetPlayerStateFromObject',source)


def received(a,payload):
    e=evidence(a);e['python_received']+=1;owner=a.call_function('GetOwner')
    if not valid(owner):e['diagnostic_fallbacks']+=1;return True
    if owner.call_function('HasAuthority'):
        target=player(a,payload.Instigator)
        if valid(target) and target.is_a(ue.find_class('LyraPlayerState')):target.call_function('ClientBroadcastMessage',payload);e['client_requests']+=1
    # This is the second Sequence output, even when the first cast failed.
    if not lib('KismetSystemLibrary').call_function('IsDedicatedServer',a):
        target=player(a,payload.Instigator)
        notification=LyraNotificationMessage(TargetChannel=GameplayTag(TagName=ROOT),TargetPlayer=target,PayloadTag=payload.Verb)
        a.call_function(BROADCAST,notification);e['cosmetic_broadcasts']+=1
    return False


class LyraAccoladeRelayPythonProfile:
    def Received(self,Payload):return received(self,Payload)
    Received.override=RECEIVE


class LyraAccoladeRelayBlueprintFallbackProfile:
    def Received(self,Payload):evidence(self)['fallback_received']+=1;return True
    Received.override=RECEIVE
