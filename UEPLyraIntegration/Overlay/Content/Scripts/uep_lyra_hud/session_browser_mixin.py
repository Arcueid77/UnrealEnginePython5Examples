"""Browser UI policy after native DoOnce and opaque native search completion."""
from uep_lyra_weapons.hero_burst_cue_mixin import lib
CLASS='/Game/UI/Menu/Experiences/W_SessionBrowserScreen.W_SessionBrowserScreen_C'
METHODS=('focus','activate','refresh','search','unlock','results')
GATES={m:'UEPSessionBrowser'+m.title() for m in METHODS}
NATIVE={m:'UEPSessionBrowserNative'+m.title() for m in ('submit','reset')}

def evidence(w):
    if not hasattr(w,'_uep_session_browser'):w._uep_session_browser={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_session_browser
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def play(w,name):w.call_function('PlayAnimationForward',w.get_property(name),1.,False)
def stop(w,name):
    animation=w.get_property(name);w.call_function('IsAnimationPlayingForward',animation);w.call_function('StopAnimation',animation)
def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='focus':return dict(UseOriginal=False,ReturnValue=w.get_property('LyraListView'))
    if m=='activate':play(w,'OnActivated_0');w.call_function('StartSearch')
    elif m=='refresh':w.call_function('StartSearch')
    elif m=='search':
        w.get_property('LyraListView').call_function('ClearListItems');w.get_property('NoGamesBorder').call_function('SetVisibility',1);stop(w,'ProgressSpinnerOutro');play(w,'ProgressSpinnerIntro');w.call_function(NATIVE['submit'])
    elif m=='unlock':w.call_function(NATIVE['reset']);stop(w,'ProgressSpinnerIntro');play(w,'ProgressSpinnerOutro')
    elif m=='results':
        results=list(w.get_property('SearchRequest').get_property('Results'));w.get_property('NoGamesBorder').call_function('SetVisibility',3 if not results else 1);w.get_property('LyraListView').call_function('BP_SetListItems',results);controller=one(w.call_function('GetOwningPlayer'));w.call_function('SetUserFocus',controller);w.get_property('LyraListView').call_function('SetUserFocus',controller);w.call_function('UnlockAfterSearchFinish')
    return False
def method(m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+m]+=1;return dict(UseOriginal=True,ReturnValue=None) if m=='focus' else True
        return invoke(self,m,*args)
    apply.override=GATES[m]
    if m=='focus':apply.uep_named_outputs=True
    return apply
for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraSessionBrowser'+profile+'Profile']=type('LyraSessionBrowser'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
