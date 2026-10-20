"""Replay owner/activation/progress/seek policy;native lifecycle and input IO."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
CLASSES={'handler':'/ShooterCore/Game/B_HandleShooterReplays.B_HandleShooterReplays_C','hud':'/ShooterCore/UserInterface/Replays/W_ShooterReplayHUD.W_ShooterReplayHUD_C','scrub':'/ShooterCore/UserInterface/Replays/W_Replay_ScrubBar.W_Replay_ScrubBar_C'}
METHODS={'handler':('begin',),'hud':('construct',),'scrub':('tick','seek')}
GATES={'handler':{'begin':'UEPReplayHandlerBegin'},'hud':{'construct':'UEPReplayHUDConstruct'},'scrub':{'tick':'UEPReplayScrubTick','seek':'UEPReplayScrubSeek'}}
NATIVE_CREATE='UEPReplayHandlerNativeCreate'
def evidence(obj,kind):
    if not hasattr(obj,'_uep_replay_runtime'):obj._uep_replay_runtime={p+'_'+m:0 for p in ('python','fallback') for m in METHODS[kind]}
    return obj._uep_replay_runtime
def subsystem(obj,name):return lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',obj,ue.find_class(name))
def divide(a,b):
    # Native Kismet returns zero and emits its original warning for zero width
    # or replay length. Keep that diagnostic instead of adding a silent clamp.
    return float(lib('KismetMathLibrary').call_function('Divide_DoubleDouble',a,b)) if b==0. else a/b
def invoke(obj,kind,m,*args):
    evidence(obj,kind)['python_'+m]+=1
    if kind=='handler':
        owner=obj.call_function('GetOwner')
        if valid(owner) and owner.is_a(ue.find_class('LyraPlayerController')):
            if owner.is_a(ue.find_class('LyraReplayPlayerController')):
                if subsystem(obj,'ReplaySubsystem').call_function('IsPlaying'):obj.set_property('As Lyra Replay Player Controller',owner);obj.call_function(NATIVE_CREATE)
            else:owner.call_function('TryToRecordClientReplay')
    elif kind=='hud':obj.call_function('ActivateWidget')
    elif m=='tick':obj.get_property('TimeScrubberWidget').call_function('SetPercent',divide(float(args[0]),float(args[1])))
    elif m=='seek':subsystem(obj,'LyraReplaySubsystem').call_function('SeekInActiveReplay',float(args[0])*divide(float(args[1]),float(args[2])))
    return False
def method(kind,m,fallback):
    def apply(self,*args):
        if kind=='scrub':evidence(self,kind)['last_'+m+'_inputs']=list(args)
        if fallback:evidence(self,kind)['fallback_'+m]+=1;return True
        return invoke(self,kind,m,*args)
    apply.override=GATES[kind][m];return apply
for kind,prefix in (('handler','Handler'),('hud','HUD'),('scrub','Scrub')):
    for profile,fallback in (('Python',False),('BlueprintFallback',True)):
        globals()['LyraReplay'+prefix+profile+'Profile']=type('LyraReplay'+prefix+profile+'Profile',(),{m:method(kind,m,fallback) for m in METHODS[kind]})
