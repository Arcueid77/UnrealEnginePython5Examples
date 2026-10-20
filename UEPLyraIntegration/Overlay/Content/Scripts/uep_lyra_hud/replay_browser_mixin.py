"""Replay list UI policy;native query action and shared DoOnce remain."""
from uep_lyra_weapons.hero_burst_cue_mixin import lib
CLASS='/Game/UI/Menu/Replays/W_ReplayBrowserScreen.W_ReplayBrowserScreen_C'
METHODS=('focus','activate','refresh','search','unlock','results')
GATES={m:'UEPReplayBrowser'+m.title() for m in METHODS}
NATIVE={m:'UEPReplayBrowserNative'+m.title() for m in ('query','reset')}
def evidence(w):
    if not hasattr(w,'_uep_replay_browser'):w._uep_replay_browser={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_replay_browser
def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='focus':return dict(UseOriginal=False,ReturnValue=w.get_property('RefreshButton'))
    if m in ('activate','refresh'):w.call_function('StartSearch')
    elif m=='search':w.get_property('ProgressSpinner').call_function('SetVisibility',0);w.call_function(NATIVE['query'])
    elif m=='unlock':w.call_function(NATIVE['reset']);w.get_property('ProgressSpinner').call_function('SetVisibility',1)
    elif m=='results':w.set_property('ResultList',args[0]);w.get_property('ReplayListWidget').call_function('BP_SetListItems',list(w.get_property('ResultList').get_property('Results')));w.call_function('UnlockAfterSearchFinish')
    return False
def method(m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+m]+=1;return dict(UseOriginal=True,ReturnValue=None) if m=='focus' else True
        return invoke(self,m,*args)
    apply.override=GATES[m]
    if m=='focus':apply.uep_named_outputs=True
    return apply
for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraReplayBrowser'+profile+'Profile']=type('LyraReplayBrowser'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
