"""Player-tile ordering and color decisions; native team/UMG backends remain."""
import unreal_engine as ue
from unreal_engine.structs import SlateColor
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/TopDownArena/UserInterface/Player/W_PlayerTile.W_PlayerTile_C'
MONITOR='Monitor Team Change'
BOUND='OnTeamChanged_651EFD6A4A656440ED3534BB77B849B5'
BIND='UEPBindArenaTileTeamObserver'
STATS=('Bomb','Range','Speed')
COLORS={0:(0.,0.,0.,0.),1:(1.,.1,.1,1.),2:(.1,.1,1.,1.),3:(.1,1.,.1,1.),4:(1.,1.,.1,1.)}
def lib(name):return ue.find_class(name).get_cdo()
def evidence(widget):
    value=getattr(widget,'_uep_arena_player_tile',None)
    if value is None:
        value=dict(python_configure=0,python_monitor=0,python_team=0,fallback_configure=0,fallback_monitor=0,fallback_team=0,cancels=0,factories=0,activations=0,updates=0,unset_noops=0,stat_calls=[],payloads=[])
        widget._uep_arena_player_tile=value
    return value

class LyraArenaPlayerTilePythonProfile:
    def Configure(self,PlayerState):
        value=evidence(self);value['python_configure']+=1
        text=lib('KismetTextLibrary').call_function('Conv_StringToText',PlayerState.call_function('GetPlayerName'));self.get_property('PlayerName').call_function('SetText',text)
        self.call_function(MONITOR,PlayerState)
        for stat in STATS:
            # Typed native calls carry the original FGameplayAttribute and soft
            # display-asset literals; they have no branches or UI policy.
            self.call_function('UEPArenaTileConfigure'+stat,PlayerState);value['stat_calls'].append(stat)
    def MonitorTeamChange(self,PlayerState):
        value=evidence(self);value['python_monitor']+=1;old=self.get_property('MonitorTeamChangeAsync')
        if valid(old):old.call_function('Cancel');value['cancels']+=1
        proxy=lib('AsyncAction_ObserveTeam').call_function('ObserveTeam',PlayerState)
        if not valid(proxy):return
        value['factories']+=1;self.call_function(BIND,proxy);proxy.call_function('Activate');value['activations']+=1;self.set_property('MonitorTeamChangeAsync',proxy)
    MonitorTeamChange.override=MONITOR
    def ObservedTeam(self,bTeamSet:bool,TeamId:int):
        value=evidence(self);value['python_team']+=1;value['payloads'].append([bool(bTeamSet),int(TeamId)])
        if not bTeamSet:value['unset_noops']+=1;return
        self.get_property('Image_82').call_function('SetBrushTintColor',SlateColor(SpecifiedColor=ue.FLinearColor(*COLORS.get(int(TeamId),COLORS[0])),ColorUseRule=0));value['updates']+=1
    ObservedTeam.override=BOUND

class LyraArenaPlayerTileBlueprintFallbackProfile:
    def Configure(self,PlayerState):
        evidence(self)['fallback_configure']+=1;self.call_mixin_original('Configure',PlayerState)
    def MonitorTeamChange(self,PlayerState):
        evidence(self)['fallback_monitor']+=1;self.call_mixin_original(MONITOR,PlayerState)
    MonitorTeamChange.override=MONITOR
    def ObservedTeam(self,bTeamSet:bool,TeamId:int):
        value=evidence(self);value['fallback_team']+=1;value['payloads'].append([bool(bTeamSet),int(TeamId)]);self.call_mixin_original(BOUND,bTeamSet,TeamId)
    ObservedTeam.override=BOUND
