"""Accolade presentation; native registry, queue, timers and UMG animation stay."""
from unreal_engine.enums import ESlateVisibility
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib

CLASSES={k:'/ShooterCore/UserInterface/Notifications/Accolades/'+n+'.'+n+'_C' for k,n in (('host','W_AccoladeHostWidget'),('toast','W_AccoladeToast'))}
CONSTRUCT='UEPAccoladeHostConstruct';CREATE='UEPAccoladeHostCreate';DESTROY='UEPAccoladeHostDestroy';PLAY='UEPAccoladeToastPlay'


def evidence(w):
    if not hasattr(w,'_uep_accolade_widgets'):w._uep_accolade_widgets={p+'_'+n:0 for p in ('python','fallback') for n in ('construct','create','destroy','play')};w._uep_accolade_widgets.update(sounds=0,diagnostic_fallbacks=0)
    return w._uep_accolade_widgets


def hide(w,name):
    evidence(w)['python_'+name]+=1;toast=w.get_property('MyToast')
    if not valid(toast):evidence(w)['diagnostic_fallbacks']+=1;return True
    toast.call_function('SetVisibility',ESlateVisibility.Collapsed);return False


def create(w,entry):
    e=evidence(w);e['python_create']+=1;toast=w.get_property('MyToast')
    if not valid(toast) or not all(valid(toast.get_property(n)) for n in ('TextWidget','IconWidget')):e['diagnostic_fallbacks']+=1;return dict(UseOriginal=True,Widget=None)
    toast.call_function('SetVisibility',ESlateVisibility.HitTestInvisible)
    if valid(entry.Sound):lib('GameplayStatics').call_function('PlaySound2D',WorldContextObject=w,Sound=entry.Sound,VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,ConcurrencySettings=None,OwningActor=None,bIsUISound=True);e['sounds']+=1
    toast.get_property('TextWidget').call_function('SetText',entry.Row.DisplayName);toast.get_property('IconWidget').call_function('SetBrushResourceObject',entry.Icon);toast.call_function('PlayIntroOutro')
    return dict(UseOriginal=False,Widget=toast)


def play(w):
    e=evidence(w);e['python_play']+=1;animation=w.get_property('IntroOutro')
    if not valid(animation):e['diagnostic_fallbacks']+=1;return True
    w.call_function('PlayAnimationForward',animation,1.,False);return False


class LyraAccoladeHostPythonProfile:
    def Construct(self):return hide(self,'construct')
    Construct.override=CONSTRUCT
    def Create(self,Entry):return create(self,Entry)
    Create.override=CREATE;Create.uep_named_outputs=True
    def Destroy(self,Widget):return hide(self,'destroy')
    Destroy.override=DESTROY


class LyraAccoladeHostBlueprintFallbackProfile:
    def Construct(self):evidence(self)['fallback_construct']+=1;return True
    Construct.override=CONSTRUCT
    def Create(self,Entry):evidence(self)['fallback_create']+=1;return dict(UseOriginal=True,Widget=None)
    Create.override=CREATE;Create.uep_named_outputs=True
    def Destroy(self,Widget):evidence(self)['fallback_destroy']+=1;return True
    Destroy.override=DESTROY


class LyraAccoladeToastPythonProfile:
    def Play(self):return play(self)
    Play.override=PLAY


class LyraAccoladeToastBlueprintFallbackProfile:
    def Play(self):evidence(self)['fallback_play']+=1;return True
    Play.override=PLAY
