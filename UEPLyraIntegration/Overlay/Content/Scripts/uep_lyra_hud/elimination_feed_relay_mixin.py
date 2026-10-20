"""Relay policy; original exact subscription and reliable native RPC remain."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_abilities.melee_trace_mixin import native_outputs

CLASS='/ShooterCore/Accolades/B_EliminationFeedRelay.B_EliminationFeedRelay_C'
RECEIVE='UEPElimFeedReceived'
BROADCAST='UEPElimFeedBroadcast'
CHANNEL='Lyra.AddNotification.KillFeed'
SLOT='HUD.Slot.EliminationFeed'
STRUCT='/ShooterCore/UserInterface/Notifications/EliminationFeed/EliminationFeedMessage.EliminationFeedMessage'


def evidence(a):
    if not hasattr(a,'_uep_elim_feed_relay'):a._uep_elim_feed_relay=dict(python_received=0,fallback_received=0,multicast_requests=0,cosmetic_broadcasts=0,diagnostic_fallbacks=0)
    return a._uep_elim_feed_relay


def received(a,payload):
    e=evidence(a);e['python_received']+=1;owner=a.call_function('GetOwner')
    if not valid(owner):e['diagnostic_fallbacks']+=1;return True
    authority=bool(owner.call_function('HasAuthority'));state=None
    if authority:
        state=lib('GameplayStatics').call_function('GetGameState',a)
        if not valid(state) or not state.is_a(ue.find_class('LyraGameState')):return False
    cosmetic=not authority or not lib('KismetSystemLibrary').call_function('IsDedicatedServer',a)
    if cosmetic:
        attacker=payload.Instigator;attackee=payload.Target;ps=ue.find_class('PlayerState')
        teams=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',a,ue.find_class('LyraTeamSubsystem'))
        # No side effects before returning to the original diagnostic path.
        if not all(valid(p) and p.is_a(ps) for p in (attacker,attackee)) or not valid(teams):e['diagnostic_fallbacks']+=1;return True
    if authority:state.call_function('MulticastReliableMessageToClients',payload);e['multicast_requests']+=1
    if not cosmetic:return False
    ids=[]
    for player in (attacker,attackee):
        result=native_outputs('LyraTeamSubsystem','FindTeamFromActor',teams.call_function('FindTeamFromActor',player.call_function('GetPawn')));ids.append(int(result['TeamId']))
    names=[lib('KismetTextLibrary').call_function('Conv_StringToText',p.call_function('GetPlayerName')) for p in (attacker,attackee)]
    a.call_function(BROADCAST,names[0],names[1],ids[0],ids[1],payload.InstigatorTags);e['cosmetic_broadcasts']+=1
    return False


class LyraEliminationFeedRelayPythonProfile:
    def Received(self,Payload):return received(self,Payload)
    Received.override=RECEIVE


class LyraEliminationFeedRelayBlueprintFallbackProfile:
    def Received(self,Payload):evidence(self)['fallback_received']+=1;return True
    Received.override=RECEIVE
