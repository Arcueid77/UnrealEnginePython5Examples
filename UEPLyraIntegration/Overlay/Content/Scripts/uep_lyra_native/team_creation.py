"""Team policy only; native experience callbacks, creation, and team setters remain."""
import unreal_engine as ue
from .message_processors import lib

CLASSES=('/ShooterCore/Game/B_TeamSetup_TwoTeams.B_TeamSetup_TwoTeams_C',
         '/TopDownArena/Game/B_TeamSetup_FourTeams.B_TeamSetup_FourTeams_C')
CHOOSE='UEPChooseTeamForPlayer';LEAST='UEPGetLeastPopulatedTeamID'


def metrics(component):
    if not hasattr(component,'_uep_native_team_metrics'):
        component._uep_native_team_metrics=dict(python_choose=0,python_least=0,native_choose=0,native_least=0)
    return component._uep_native_team_metrics


def least_team(configured,players):
    counts={int(team):0 for team in configured}
    if not counts:return -1
    for team,inactive in players:
        if team!=-1 and not inactive:
            if team not in counts:raise AssertionError('Active native player belongs to an unconfigured team')
            counts[team]=(counts[team]+1)&0xffffffff
    return min(counts,key=lambda team:(counts[team],team))


def least(component):
    metrics(component)['python_least']+=1
    configured=component.get_property('TeamsToCreate')
    if not configured:return -1
    state=lib('GameplayStatics').call_function('GetGameState',component)
    players=[(int(p.call_function('GetTeamId')),bool(p.get_property('bIsInactive')))
             for p in state.get_property('PlayerArray') if p is not None and p.is_a(ue.find_class('LyraPlayerState'))]
    return least_team(configured,players)


class TeamPythonProfile:
    def UEPChooseTeamForPlayer(self,PS):
        metrics(self)['python_choose']+=1
        team=-1 if PS.get_property('bOnlySpectator') else int(self.call_function(LEAST))
        self.call_function('UEPSetPlayerTeam',PS,team)
    def UEPGetLeastPopulatedTeamID(self):return least(self)


class TeamNativeFallbackProfile:
    def UEPChooseTeamForPlayer(self,PS):
        metrics(self)['native_choose']+=1
        return self.call_mixin_original(CHOOSE,PS)
    def UEPGetLeastPopulatedTeamID(self):
        metrics(self)['native_least']+=1
        return self.call_mixin_original(LEAST)
