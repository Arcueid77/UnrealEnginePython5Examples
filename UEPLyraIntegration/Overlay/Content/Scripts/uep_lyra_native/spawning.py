"""Spawn policy on native candidates; physics, weak caches and claims stay native."""
import unreal_engine as ue
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .message_processors import lib
from .bot_creation import random_index

CLASS='/ShooterCore/Game/B_TeamSpawningRules.B_TeamSpawningRules_C'
CHOOSE='UEPChooseFromStarts';TDM='UEPChooseTDMStart'


def metrics(component):
    if not hasattr(component,'_uep_native_spawning_metrics'):
        component._uep_native_spawning_metrics=dict(python_choose=0,native_choose=0,python_tdm=0,native_tdm=0,
            spectator_choices=0,fallback_queries=0,native_occupancy_queries=0,native_claim_requests=0)
    return component._uep_native_spawning_metrics


def occupancy(component,start,player):
    metrics(component)['native_occupancy_queries']+=1
    return int(component.call_function('UEPGetStartOccupancy',start,player))


def random_unoccupied(component,player,starts):
    metrics(component)['fallback_queries']+=1
    if player is None:return None
    empty=[];partial=[]
    for start in starts:
        state=occupancy(component,start,player)
        if state==0:empty.append(start)
        elif state==1:partial.append(start)
    candidates=empty or partial
    return candidates[random_index(0,len(candidates)-1)] if candidates else None


def team_id(subsystem,actor):
    result=native_outputs('LyraTeamSubsystem','FindTeamFromActor',subsystem.call_function('FindTeamFromActor',actor))
    return int(result['TeamId'])


class SpawningPythonProfile:
    def UEPChooseFromStarts(self,Player,StarterPoints):
        metrics(self)['python_choose']+=1
        state=Player.PlayerState
        if state is not None and state.get_property('bOnlySpectator'):
            metrics(self)['spectator_choices']+=1
            return StarterPoints[random_index(0,len(StarterPoints)-1)] if StarterPoints else None
        chosen=native_outputs('LyraPlayerSpawningManagerComponent','UEPChooseSpecificStart',self.call_function('UEPChooseSpecificStart',Player,StarterPoints))['ReturnValue']
        if chosen is None:chosen=random_unoccupied(self,Player,StarterPoints)
        if chosen is not None and chosen.is_a(ue.find_class('LyraPlayerStart')):
            metrics(self)['native_claim_requests']+=1;self.call_function('UEPTryClaimStart',chosen,Player)
        return chosen
    def UEPChooseTDMStart(self,Player,PlayerStarts):
        metrics(self)['python_tdm']+=1
        subsystem=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self,ue.find_class('LyraTeamSubsystem'))
        if subsystem is None:ue.log_error('Native spawning requires LyraTeamSubsystem');return None
        player_team=team_id(subsystem,Player)
        if player_team==-1:ue.log_error('Native spawning requires an assigned player team');return None
        state=lib('GameplayStatics').call_function('GetGameState',self)
        best=None;maximum=0.;fallback=None;fallback_maximum=0.
        for other in state.get_property('PlayerArray'):
            other_team=team_id(subsystem,other)
            if other.get_property('bOnlySpectator'):continue
            if other_team==-1:ue.log_error('Native spawning encountered an unassigned player team');continue
            if other_team==player_team:continue
            for start in PlayerStarts:
                pawn=other.call_function('GetPawn')
                if pawn is None:continue
                distance=float(start.call_function('GetDistanceTo',pawn))
                if self.call_function('UEPIsStartClaimed',start):
                    if fallback is None or distance>fallback_maximum:fallback=start;fallback_maximum=distance
                elif occupancy(self,start,Player)<2:
                    if best is None or distance>maximum:best=start;maximum=distance
        return best if best is not None else fallback


class SpawningNativeFallbackProfile:
    def UEPChooseFromStarts(self,Player,StarterPoints):
        metrics(self)['native_choose']+=1;return native_outputs('LyraPlayerSpawningManagerComponent',CHOOSE,self.call_mixin_original(CHOOSE,Player,StarterPoints))['ReturnValue']
    def UEPChooseTDMStart(self,Player,PlayerStarts):
        metrics(self)['native_tdm']+=1;return native_outputs('TDM_PlayerSpawningManagmentComponent',TDM,self.call_mixin_original(TDM,Player,PlayerStarts))['ReturnValue']
