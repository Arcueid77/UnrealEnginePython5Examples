"""Menu/root-layer policy with original native async prompts and terminal calls."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASSES={k:'/Game/'+v+'.'+v.rsplit('/',1)[-1]+'_C' for k,v in dict(layout='UI/W_OverallUILayout',menu='UI/Hud/W_LyraGameMenu',close='UI/Menu/W_TouchCloseButton',spinner='UI/Menu/Experiences/W_NonInteractiveSpinner').items()}
METHODS=dict(layout=('initialize',),menu=('focus','activate','quit','settings','exit','result'),close=('click',),spinner=('focus',))
GATES={k:{m:'UEPMenuLayer'+k.title()+m.title() for m in methods} for k,methods in METHODS.items()}
LAYERS=(('UI.Layer.Game','GameLayer_Stack'),('UI.Layer.GameMenu','GameMenu_Stack'),('UI.Layer.Menu','Menu_Stack'),('UI.Layer.Modal','Modal_Stack'))
PUSH='UEPMenuNativePushSettings'
CONFIRM='UEPMenuNativeShowConfirmation'
TRAVEL='UEPMenuNativeOpenFrontEnd'

def evidence(w):
    if not hasattr(w,'_uep_menu_layers'):w._uep_menu_layers={p+'_'+k+'_'+m:0 for p in ('python','fallback') for k,methods in METHODS.items() for m in methods};w._uep_menu_layers.update(layer_names=[],last_confirmation_result=None)
    return w._uep_menu_layers
def invoke(w,k,m,*a):
    evidence(w)['python_'+k+'_'+m]+=1
    if k=='layout':
        for name,field in LAYERS:w.call_function('RegisterLayer',ue.find_struct('GameplayTag')(TagName=name),w.get_property(field));evidence(w)['layer_names'].append(name)
        return False
    if k=='spinner':return dict(UseOriginal=False,ReturnValue=w)
    if k=='close':
        cls=ue.find_class('CommonActivatableWidget');parent=lib('CommonUILibrary').call_function('FindParentWidgetOfType',w,cls)
        if valid(parent) and parent.is_a(cls):parent.call_function('DeactivateWidget')
        return False
    if m=='focus':return dict(UseOriginal=False,ReturnValue=w.get_property('OptionsButtons'))
    if m=='activate':w.call_function('PlayAnimationForward',w.get_property('OnActivated'),1.,False);return False
    if m=='settings':w.call_function(PUSH);return False
    if m=='exit':w.call_function(CONFIRM);return False
    if m=='result':
        value=int(a[0]);evidence(w)['last_confirmation_result']=value
        if value==0:w.call_function(TRAVEL)
        return False
    subsystem=lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',w.call_function('GetOwningPlayer'),ue.find_class('CommonInputSubsystem'));subsystem.call_function('SetCurrentInputType',0);lib('KismetSystemLibrary').call_function('QuitGame',w,None,0,False);return False
def method(k,m,fallback):
    def apply(self,*a):
        if fallback:evidence(self)['fallback_'+k+'_'+m]+=1;return dict(UseOriginal=True,ReturnValue=None) if m=='focus' else True
        return invoke(self,k,m,*a)
    apply.override=GATES[k][m]
    if m=='focus':apply.uep_named_outputs=True
    return apply
for label,methods in METHODS.items():
    for name,fallback_profile in (('Python',False),('BlueprintFallback',True)):
        clsname='LyraMenuLayer'+label.title()+name+'Profile';globals()[clsname]=type(clsname,(),{m:method(label,m,fallback_profile) for m in methods})
