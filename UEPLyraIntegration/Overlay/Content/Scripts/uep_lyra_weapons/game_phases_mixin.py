"""Phase decisions; original GAS parent, latent nodes and typed message VM remain."""
import unreal_engine as ue
from .hero_burst_cue_mixin import lib

CLASSES={k:'/ShooterCore/Experiences/Phases/'+n+'.'+n+'_C' for k,n in (('warmup','Phase_Warmup'),('playing','Phase_Playing'),('postgame','Phase_PostGame'))}
GATES={k:'UEPPhase'+v for k,v in dict(sanitize='Sanitize',warmup='Warmup',warmupend='WarmupEnd',ready='CountdownReady',step='CountdownStep',playing='Playing',playingend='PlayingEnd',postgame='PostGame',block='BlockInput',restart='Restart').items()}
BACKENDS={k:'UEPPhaseNative'+v for k,v in dict(wait='WarmupWait',emit='WarmupEmit',playing='StartPlaying',postwait='PostGameWait',nexttick='NextTick').items()}
LOBBY='/ShooterCore/Experiences/Phases/GE_PregameLobby.GE_PregameLobby_C'
IMMUNITY='/ShooterCore/Experiences/Phases/GE_DamageImmunity_FromGameMode.GE_DamageImmunity_FromGameMode_C'
BLOCK='/Game/GameplayEffects/GE_BlockAbilityInput.GE_BlockAbilityInput_C'
CHANNEL='ShooterGame.GamePhase.MatchBeginCountdown'


def evidence(a):
    if not hasattr(a,'_uep_game_phases'):a._uep_game_phases={p+'_'+k:0 for p in ('python','fallback') for k in GATES}
    return a._uep_game_phases
def mark(a,k):evidence(a)['python_'+k]+=1
def display(a,value):lib('KismetSystemLibrary').call_function('PrintString',a,value,True,True,ue.FLinearColor(0.,.66,1.,1.),2.,'None')
def global_system(a):return lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',a,ue.find_class('LyraGlobalAbilitySystem'))
def effect(a,action,path):global_system(a).call_function(action,ue.load_class(path))


def sanitize(a):
    mark(a,'sanitize');math=lib('KismetMathLibrary');original_count=int(a.get_property('CountdownDuration'));original_wait=float(a.get_property('WaitForPlayersDuration'));wait=math.call_function('FMax',original_wait,0.);a.set_property('WaitForPlayersDuration',wait);maximum=math.call_function('Conv_Int64ToInt',math.call_function('Conv_DoubleToInt64',a.get_property('WaitForPlayersDuration')));count=min(max(original_count,0),int(maximum));a.set_property('CountdownDuration',count)
    if float(a.get_property('WaitForPlayersDuration'))!=original_wait or int(a.get_property('CountdownDuration'))!=original_count:display(a,'Altered durations settings for warm-up phase to be in valid ranges')
    return False
def warmup(a):
    mark(a,'warmup')
    if lib('LyraDevelopmentStatics').call_function('ShouldSkipDirectlyToGameplay'):a.call_function(BACKENDS['playing']);return False
    a.call_function('SanitizeDurations');effect(a,'ApplyEffectToAll',LOBBY);a.call_function(BACKENDS['wait']);return False
def finish_warmup(a):effect(a,'RemoveEffectFromAll',LOBBY);a.call_function(BACKENDS['playing'])
def countdown(a):
    if int(a.get_property('CountdownSecsRemaining'))>=0:a.call_function(BACKENDS['emit'])
    else:finish_warmup(a)
def ready(a):mark(a,'ready');a.set_property('CountdownSecsRemaining',int(a.get_property('CountdownDuration')));countdown(a);return False
def step(a):mark(a,'step');a.set_property('CountdownSecsRemaining',lib('KismetMathLibrary').call_function('Subtract_IntInt',int(a.get_property('CountdownSecsRemaining')),1));countdown(a);return False
def warmupend(a,cancelled):mark(a,'warmupend');display(a,'Warmup Phase Ended');return False
def playing(a):mark(a,'playing');display(a,'Playing Phase');return False
def playingend(a,cancelled):mark(a,'playingend');display(a,'Playing Phase Ended');return False
def postgame(a):mark(a,'postgame');effect(a,'ApplyEffectToAll',IMMUNITY);a.call_function(BACKENDS['postwait']);return False
def block(a):mark(a,'block');effect(a,'ApplyEffectToAll',BLOCK);a.call_function(BACKENDS['nexttick']);return False
def restart(a):mark(a,'restart');lib('LyraSystemStatics').call_function('PlayNextGame',a);return False


class LyraWarmupPhasePythonProfile:
    def Sanitize(self):return sanitize(self)
    Sanitize.override=GATES['sanitize']
    def Activate(self):return warmup(self)
    Activate.override=GATES['warmup']
    def End(self,bWasCancelled):return warmupend(self,bWasCancelled)
    End.override=GATES['warmupend']
    def Ready(self):return ready(self)
    Ready.override=GATES['ready']
    def Step(self):return step(self)
    Step.override=GATES['step']
class LyraPlayingPhasePythonProfile:
    def Activate(self):return playing(self)
    Activate.override=GATES['playing']
    def End(self,bWasCancelled):return playingend(self,bWasCancelled)
    End.override=GATES['playingend']
class LyraPostgamePhasePythonProfile:
    def Activate(self):return postgame(self)
    Activate.override=GATES['postgame']
    def Block(self):return block(self)
    Block.override=GATES['block']
    def Restart(self):return restart(self)
    Restart.override=GATES['restart']


def fallback(k):
    def invoke(self,*args):evidence(self)['fallback_'+k]+=1;return True
    invoke.override=GATES[k];return invoke
class LyraWarmupPhaseBlueprintFallbackProfile:
    Sanitize=fallback('sanitize');Activate=fallback('warmup');End=fallback('warmupend');Ready=fallback('ready');Step=fallback('step')
class LyraPlayingPhaseBlueprintFallbackProfile:
    Activate=fallback('playing');End=fallback('playingend')
class LyraPostgamePhaseBlueprintFallbackProfile:
    Activate=fallback('postgame');Block=fallback('block');Restart=fallback('restart')
