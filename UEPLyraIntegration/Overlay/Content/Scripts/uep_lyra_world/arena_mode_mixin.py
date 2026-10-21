"""Arena scoring/round/local-user decisions on the original mode component family."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from unreal_engine.enums import ELyraTeamComparison
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .effect_pad_mixin import valid
BASE='/TopDownArena/Game/Modes/B_TopDownArena_GameComponent_Base.B_TopDownArena_GameComponent_Base_C'
LIVES='/TopDownArena/Game/Modes/B_TopDownArena_GameComponent_Lives.B_TopDownArena_GameComponent_Lives_C'
LOCAL='/TopDownArena/Game/Modes/B_TopDownArena_GameComponent_SpawnLocalPlayers.B_TopDownArena_GameComponent_SpawnLocalPlayers_C'
START='UEPArenaModeNativeListeners'
ELIM_LISTEN='UEPArenaModeNativeEliminationListener'
ASSIST_LISTEN='UEPArenaModeNativeAssistListener'
WARMUP='UEPArenaModeNativeStartWarmup'
POSTGAME='UEPArenaModeNativeStartPostGame'
GATES={k:'UEPArenaMode'+v for k,v in dict(begin='Begin',elimination='Elimination',assist='Assist',ready='Ready',warmup='WarmupEnded',tick='Tick',localbegin='LocalAfterParent',localspawn='SpawnLocalUsers').items()}
def lib(n):return ue.find_class(n).get_cdo()
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def tag(n):return GameplayTag(TagName=n)
def state(c):return lib('GameplayStatics').call_function('GetGameState',c)
def teams(c):return lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',c,ue.find_class('LyraTeamSubsystem'))
def evidence(c):
    value=getattr(c,'_uep_arena_mode',None)
    if value is None:
        value={p+k:0 for p in ('python_','fallback_') for k in list(GATES)+['remaining']};value.update(team_adds=0,kills=0,deaths=0,assists=0,hooks=0,local_users=0,players_created=0,postgames=0);c._uep_arena_mode=value
    return value
class LyraArenaModePythonProfile:
    def Begin(self):evidence(self)['python_begin']+=1;self.call_function(START);return False
    Begin.override=GATES['begin']
    def Elimination(self,Payload):
        value=evidence(self);value['python_elimination']+=1;system=teams(self);result=native_outputs('LyraTeamSubsystem','CompareTeams',system.call_function('CompareTeams',Payload.Instigator,Payload.Target))
        if int(result['ReturnValue'])!=int(ELyraTeamComparison.DifferentTeams):return False
        system.call_function('AddTeamTagStack',result['TeamIdA'],tag('ShooterGame.Score.Eliminations'),1);value['team_adds']+=1;source,target=Payload.Instigator,Payload.Target;cls=ue.find_class('LyraPlayerState')
        if not valid(source) or not source.is_a(cls):return False
        source.call_function('AddStatTagStack',tag('ShooterGame.Score.Eliminations'),1);value['kills']+=1
        if not valid(target) or not target.is_a(cls):return False
        target.call_function('AddStatTagStack',tag('ShooterGame.Score.Deaths'),1);value['deaths']+=1;self.call_function('OnEliminationScored');value['hooks']+=1;return False
    Elimination.override=GATES['elimination']
    def Assist(self,Payload):
        value=evidence(self);value['python_assist']+=1;source=Payload.Instigator
        if valid(source) and source.is_a(ue.find_class('LyraPlayerState')):source.call_function('AddStatTagStack',tag('ShooterGame.Score.Assists'),1);value['assists']+=1
        return False
    Assist.override=GATES['assist']
    def Ready(self):evidence(self)['python_ready']+=1;self.call_function(WARMUP);return False
    Ready.override=GATES['ready']
    def WarmupEnded(self):
        evidence(self)['python_warmup']+=1;self.set_property('IsPlaying',True);seconds=state(self).call_function('GetServerWorldTimeSeconds');self.set_property('ServerWorld_GameEndTime',lib('KismetMathLibrary').call_function('Add_DoubleDouble',seconds,120.));return False
    WarmupEnded.override=GATES['warmup']
    def GetRoundTimeRemaining(self):
        evidence(self)['python_remaining']+=1
        if not self.get_property('IsPlaying'):return {'SecondsRemaining':0.}
        delta=lib('KismetMathLibrary').call_function('Subtract_DoubleDouble',self.get_property('ServerWorld_GameEndTime'),state(self).call_function('GetServerWorldTimeSeconds'));return {'SecondsRemaining':lib('KismetMathLibrary').call_function('FMax',delta,0.)}
    GetRoundTimeRemaining.uep_named_outputs=True
    def Tick(self):
        value=evidence(self);value['python_tick']+=1
        if self.get_property('IsPlaying') and lib('KismetMathLibrary').call_function('EqualEqual_DoubleDouble',float(one(self.call_function('GetRoundTimeRemaining'))),0.):self.set_property('IsPlaying',False);value['postgames']+=1;self.call_function(POSTGAME)
        return False
    Tick.override=GATES['tick']
    def LocalAfterParent(self):
        evidence(self)['python_localbegin']+=1;lib('KismetSystemLibrary').call_function('PrintString',self,'ADD LOCAL PLAYERS',True,True,ue.FLinearColor(0.,.66,1.,1.),2.,'None')
        if self.call_function('GetOwner').call_function('HasAuthority'):self.call_function('Spawn Local Players')
        return False
    LocalAfterParent.override=GATES['localbegin']
    def SpawnLocalUsers(self):
        value=evidence(self);value['python_localspawn']+=1;result=native_outputs('InputDeviceLibrary','GetAllActiveUsers',lib('InputDeviceLibrary').call_function('GetAllActiveUsers'))
        if int(result['ReturnValue'])>0:
            for index,user in enumerate(result['OutUsers']):
                value['local_users']+=1
                if index>0:lib('GameplayStatics').call_function('CreatePlayerFromPlatformUser',self,user,True);value['players_created']+=1
        return False
    SpawnLocalUsers.override=GATES['localspawn']
def fallback(key):
    def call(c,*args):evidence(c)['fallback_'+key]+=1;return True
    call.override=GATES[key];return call
class LyraArenaModeBlueprintFallbackProfile:
    Begin=fallback('begin');Elimination=fallback('elimination');Assist=fallback('assist');Ready=fallback('ready');WarmupEnded=fallback('warmup');Tick=fallback('tick');LocalAfterParent=fallback('localbegin');SpawnLocalUsers=fallback('localspawn')
    def GetRoundTimeRemaining(self):evidence(self)['fallback_remaining']+=1;return {'SecondsRemaining':one(self.call_mixin_original('GetRoundTimeRemaining'))}
    GetRoundTimeRemaining.uep_named_outputs=True
