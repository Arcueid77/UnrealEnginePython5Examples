"""Replay item validity and confirmed-only play;localized text remains native."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
CLASS='/Game/UI/Menu/Replays/W_ReplayListEntry.W_ReplayListEntry_C'
METHODS=('item','click','result')
GATES={m:'UEPReplayEntry'+m.title() for m in METHODS}
NATIVE={m:'UEPReplayEntryNative'+m.title() for m in ('item','dialog')}
def evidence(w):
    if not hasattr(w,'_uep_replay_entry'):w._uep_replay_entry={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_replay_entry
def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='item':
        if valid(args[0]) and args[0].is_a(ue.find_class('LyraReplayListEntry')):w.call_function(NATIVE['item'],args[0])
    elif m=='click':w.call_function(NATIVE['dialog'])
    elif m=='result':
        if int(args[0])==0:lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',w,ue.find_class('LyraReplaySubsystem')).call_function('PlayReplay',w.get_property('As Lyra Replay List Entry'))
    return False
def method(m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+m]+=1;return True
        return invoke(self,m,*args)
    apply.override=GATES[m];return apply
for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraReplayEntry'+profile+'Profile']=type('LyraReplayEntry'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
