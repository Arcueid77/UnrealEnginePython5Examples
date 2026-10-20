"""Player membership/order/pooling and ping; original native timers stay."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .scoreboard_rows_mixin import color,slate,text,one,INTERFACE

CLASSES={k:'/ShooterCore/UserInterface/ScoreBoard/'+n+'.'+n+'_C' for k,n in (('list','W_SB_PlayerList'),('connection','W_UserConnectionStatus'))}
GATES={k:'UEPSBList'+v for k,v in dict(construct='Construct',poll='Poll',sort='Sort',filter='Filter',set='PingPlayer',update='PingUpdate').items()}
LIST_TIMER='UEPSBListStartNativeTimer';PING_TIMER='UEPSBPingStartNativeTimer';FORMAT='UEPSBPingFormat'


def evidence(w):
    if not hasattr(w,'_uep_scoreboard_list'):w._uep_scoreboard_list={p+'_'+n:0 for p in ('python','fallback') for n in GATES};w._uep_scoreboard_list['diagnostic_fallbacks']=0
    return w._uep_scoreboard_list
def mark(w,n):evidence(w)['python_'+n]+=1
def diagnostic(w):evidence(w)['diagnostic_fallbacks']+=1;return True
def passes(w,ps):
    mark(w,'filter');team=int(w.get_property('TeamIdFilter'))
    if team==-1:return dict(UseOriginal=False,Passes=True)
    subsystem=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',w,ue.find_class('LyraTeamSubsystem'))
    if not valid(subsystem):diagnostic(w);return dict(UseOriginal=True,Passes=False)
    result=native_outputs('LyraTeamSubsystem','FindTeamFromActor',subsystem.call_function('FindTeamFromActor',ps));return dict(UseOriginal=False,Passes=bool(result['bIsPartOfTeam']) and int(result['TeamId'])==team)
def construct(w):
    mark(w,'construct');w.call_function('PollPlayerStates');w.call_function('SortPlayerList')
    if int(w.get_property('TeamIdFilter'))!=-1:w.call_function(LIST_TIMER)
    return False
def poll(w):
    mark(w,'poll');box=w.get_property('PlayerList')
    if not valid(box):return diagnostic(w)
    states=list(w.get_property('PlayerStates'));entries=list(one(box.call_function('GetAllEntries')))
    for i in range(len(entries)-1,-1,-1):
        if i>=len(states):box.call_function('RemoveEntry',entries[i]);continue
        if not valid(states[i]) or not one(w.call_function('PassesFilter',states[i])):
            states.pop(i);w.set_property('PlayerStates',states);box.call_function('RemoveEntry',entries[i])
    pc=w.call_function('GetOwningPlayer');gs=lib('GameplayStatics').call_function('GetGameState',w)
    if not valid(pc) or not valid(pc.get_property('PlayerState')) or not valid(gs):return False
    fresh=list(gs.get_property('PlayerArray'));w.set_property('NewPlayerStates',fresh)
    for ps in fresh:
        if valid(ps) and ps.is_a(ue.find_class('LyraPlayerState')) and ps not in states and one(w.call_function('PassesFilter',ps)):states.append(ps);w.set_property('PlayerStates',states)
    return False
def sort(w):
    mark(w,'sort');box=w.get_property('PlayerList');cls=w.get_property('PlayerRowClass');states=list(w.get_property('PlayerStates'))
    if not valid(box) or not valid(cls) or any(not valid(ps) for ps in states):return diagnostic(w)
    sorted_states=[];score_tag=ue.find_struct('GameplayTag')(TagName='ShooterGame.Score.Eliminations')
    for ps in states:
        value=int(ps.call_function('GetStatTagStackCount',score_tag));index=len(sorted_states)
        for i in range(len(sorted_states)-1,-1,-1):
            if value>int(sorted_states[i].call_function('GetStatTagStackCount',score_tag)):index=i
        sorted_states.insert(index,ps)
    box.call_function('Reset',False)
    for i,ps in enumerate(sorted_states):
        entry=box.call_function('BP_CreateEntryOfClass',cls)
        if lib('KismetSystemLibrary').call_function('DoesImplementInterface',entry,ue.load_class(INTERFACE)):entry.call_function('SetPlayerState',ps)
        entry.call_function('SetRowColor',bool(i%2>0))
    return False
def set_player(w,ps):
    mark(w,'set')
    if not valid(ps) or int(ps.call_function('GetTeamId')) not in (0,1,2):return diagnostic(w)
    w.set_property('AssociatedPlayerState',ps);w.get_property('ConnectionStatus').call_function('SetDefaultColorAndOpacity',slate(color(int(ps.call_function('GetTeamId')),.4)));w.call_function(PING_TIMER);return False
def ping(w):
    mark(w,'update');ps=w.get_property('AssociatedPlayerState')
    if not valid(ps):return False
    rounded=lib('KismetMathLibrary').call_function('Round',ps.call_function('GetPingInMilliseconds'));value=one(w.call_function(FORMAT,text(rounded)));w.get_property('ConnectionStatus').call_function('SetText',value);return False


class LyraScoreboardListPythonProfile:
    def Construct(self):return construct(self)
    Construct.override=GATES['construct']
    def Poll(self):return poll(self)
    Poll.override=GATES['poll']
    def Sort(self):return sort(self)
    Sort.override=GATES['sort']
    def Filter(self,TestPS):return passes(self,TestPS)
    Filter.override=GATES['filter'];Filter.uep_named_outputs=True
class LyraScoreboardConnectionPythonProfile:
    def Player(self,PlayerState):return set_player(self,PlayerState)
    Player.override=GATES['set']
    def Update(self):return ping(self)
    Update.override=GATES['update']
def fallback(key,named=False):
    def invoke(self,*args):evidence(self)['fallback_'+key]+=1;return dict(UseOriginal=True,Passes=False) if named else True
    invoke.override=GATES[key];invoke.uep_named_outputs=named;return invoke
class LyraScoreboardListBlueprintFallbackProfile:Construct=fallback('construct');Poll=fallback('poll');Sort=fallback('sort');Filter=fallback('filter',True)
class LyraScoreboardConnectionBlueprintFallbackProfile:Player=fallback('set');Update=fallback('update')
