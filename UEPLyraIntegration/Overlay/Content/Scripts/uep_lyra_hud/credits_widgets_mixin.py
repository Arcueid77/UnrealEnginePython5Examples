"""Credits scroll/visibility policy with original native Delay and TimerManager."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib

CLASSES={k:'/Game/UI/Credits/'+n+'.'+n+'_C' for k,n in (('credits','W_Credits'),('bar','W_TapToggleActionBar'))}
METHODS=dict(credits=('focus','scroll','toggle','reset','capture','construct','activate'),bar=('visible','reset','click'))
GATES={k:{m:'UEPCredits'+k.title()+m.title() for m in methods} for k,methods in METHODS.items()}
START='UEPCreditsNativeStartTimer'
STOP='UEPCreditsNativeStopTimer'
WRITE='UEPCreditsNativeWritePeople'
DELAY='UEPCreditsNativeBeginDelay'
PREFIX='<text case="upper">Credit Title : </><text fontface="OrbitronMedium" color="D6E3FFCC">Credit Person Name '
SUFFIX='</>\r\n'

def evidence(w):
    if not hasattr(w,'_uep_credits_widgets'):w._uep_credits_widgets={p+'_'+k+'_'+m:0 for p in ('python','fallback') for k,methods in METHODS.items() for m in methods}
    return w._uep_credits_widgets
def invoke(w,k,m,*a):
    evidence(w)['python_'+k+'_'+m]+=1
    if k=='bar':
        bar=w.get_property('BottomActionBar')
        if m=='visible':return dict(UseOriginal=False,IsVisible=int(bar.call_function('GetVisibility'))!=1)
        if m=='reset':bar.call_function('SetVisibility',1)
        else:
            visible=w.call_function('GetCurrentVisibility');visible=visible[0] if isinstance(visible,tuple) else visible;bar.call_function('SetVisibility',1 if visible else 0)
        return False
    if m=='focus':return dict(UseOriginal=False,ReturnValue=None)
    if m=='toggle':w.call_function(START if a[0] else STOP);return False
    if m=='reset':w.get_property('CreditsScroller').call_function('SetScrollOffset',0.);w.get_property('TapToggleActionBar').call_function('ResetVisibility');return False
    if m=='capture':w.set_property('EndPointOffset',float(w.get_property('CreditsScroller').call_function('GetDesiredSize').y));return False
    if m=='scroll':
        scroller=w.get_property('CreditsScroller');old=float(scroller.call_function('GetScrollOffset'));w.set_property('CurrentPosition',old);scroller.call_function('SetScrollOffset',old+float(w.get_property('ScrollSpeed')))
        # The source pure GetScrollOffset is gathered again for the later branch.
        if float(scroller.call_function('GetScrollOffset'))>=float(w.get_property('EndPointOffset')):w.call_function('ToggleScrollTimer',False);w.call_function('Reset')
        return False
    if m=='construct':
        text=w.get_property('StudioPeopleString')
        for index in range(1,101):text+=PREFIX+str(index)+SUFFIX;w.set_property('StudioPeopleString',text)
        w.call_function(WRITE);return False
    w.call_function('Reset');w.call_function(DELAY);return False
def method(k,m,fallback):
    def apply(self,*a):
        if fallback:evidence(self)['fallback_'+k+'_'+m]+=1;return dict(UseOriginal=True,IsVisible=False) if m=='visible' else dict(UseOriginal=True,ReturnValue=None) if m=='focus' else True
        return invoke(self,k,m,*a)
    apply.override=GATES[k][m]
    if m in ('visible','focus'):apply.uep_named_outputs=True
    return apply
for label,methods in METHODS.items():
    for name,fallback_profile in (('Python',False),('BlueprintFallback',True)):
        clsname='LyraCredits'+label.title()+name+'Profile';globals()[clsname]=type(clsname,(),{m:method(label,m,fallback_profile) for m in methods})
