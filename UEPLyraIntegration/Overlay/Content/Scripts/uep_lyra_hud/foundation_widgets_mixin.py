"""Foundation dialog/loading/image/size policies with native localized rendering."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASSES={k:'/Game/'+v+'.'+v.rsplit('/',1)[-1]+'_C' for k,v in dict(dialog='UI/Foundation/Dialogs/W_ConfirmationDialog',reason='UI/Foundation/LoadingScreen/W_LoadingScreenReasonDebugText',loading='UI/Foundation/LoadingScreen/W_LoadingScreen_Host',aspect='UI/Foundation/Widgets/W_AspectImageWithBlur',spinner='UI/Foundation/Widgets/W_ProgressSpinner').items()}
GATES={k:'UEPFoundationWidget'+k.title() for k in CLASSES}
NATIVE_REASON='UEPFoundationReasonApply'
DEFAULT_CONTENT='/Game/UI/Foundation/LoadingScreen/W_LoadingScreen_DefaultContent.W_LoadingScreen_DefaultContent_C'

def evidence(w):
    if not hasattr(w,'_uep_foundation_widgets'):w._uep_foundation_widgets={p+'_'+k:0 for p in ('python','fallback') for k in CLASSES}
    return w._uep_foundation_widgets
def mark(w,k):evidence(w)['python_'+k]+=1
def subsystem(w,name):return lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',w,ue.find_class(name))
def dialog(w):mark(w,'dialog');w.call_function('PlayAnimationForward',w.get_property('OnActivated'),1.,False);return False
def reason(w):mark(w,'reason');value=subsystem(w,'LoadingScreenManager').call_function('GetDebugReasonForShowingOrHidingLoadingScreen');w.call_function(NATIVE_REASON,value);return False
def loading(w,cls):
    mark(w,'loading');w.set_property('ContentWidgetClass',cls)
    if not valid(cls):cls=ue.load_class(DEFAULT_CONTENT);w.set_property('ContentWidgetClass',cls)
    child=lib('WidgetBlueprintLibrary').call_function('Create',w,cls,w.call_function('GetOwningPlayer'));w.get_property('ExperienceSpecificWidgetSlot').call_function('SetContent',child);return False
def aspect(w):mark(w,'aspect');brush=w.get_property('DisplayBrush');w.get_property('Background').call_function('SetBrush',brush);w.get_property('BlurredBackground').call_function('SetBrush',brush);return False
def spinner(w):mark(w,'spinner');w.get_property('Spinner').call_function('SetDesiredSizeOverride',w.get_property('Size'));return False
def method(k,fn):
    def invoke(self,*args):return fn(self,*args)
    invoke.override=GATES[k];return invoke
def ignore_design(fn):
    def invoke(w,IsDesignTime):return fn(w)
    return invoke
def fallback(k):
    def invoke(self,*args):evidence(self)['fallback_'+k]+=1;return True
    invoke.override=GATES[k];return invoke

class LyraFoundationWidgetDialogPythonProfile:Apply=method('dialog',dialog)
class LyraFoundationWidgetReasonPythonProfile:Apply=method('reason',reason)
class LyraFoundationWidgetLoadingPythonProfile:Apply=method('loading',loading)
class LyraFoundationWidgetAspectPythonProfile:Apply=method('aspect',aspect)
class LyraFoundationWidgetSpinnerPythonProfile:Apply=method('spinner',ignore_design(spinner))
class LyraFoundationWidgetDialogBlueprintFallbackProfile:Apply=fallback('dialog')
class LyraFoundationWidgetReasonBlueprintFallbackProfile:Apply=fallback('reason')
class LyraFoundationWidgetLoadingBlueprintFallbackProfile:Apply=fallback('loading')
class LyraFoundationWidgetAspectBlueprintFallbackProfile:Apply=fallback('aspect')
class LyraFoundationWidgetSpinnerBlueprintFallbackProfile:Apply=fallback('spinner')
