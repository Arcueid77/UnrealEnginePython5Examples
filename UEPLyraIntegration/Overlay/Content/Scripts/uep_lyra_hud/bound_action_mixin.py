"""Bound-action button policy; native action/input delegates and click latent stay."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/Game/UI/Foundation/Widgets/BottomBar/W_BoundActionButton.W_BoundActionButton_C'
KEYS=('style','reset','hover','unhover','click','clicksound','finished','select','deselect','disable','enable')
GATES={k:'UEPBoundAction'+k.title() for k in KEYS}
NATIVE_CLICK='UEPBoundActionStartNativeClick'
BRUSH_FIELDS=('TintColor','Tiling','Mirroring','ImageSize','Margin','ResourceObject','OutlineSettings')
SOUNDS={k:'/Game/Audio/Sounds/UI/sfx_UI_SubMenu_'+n+'_nl_meta_Preset.sfx_UI_SubMenu_'+n+'_nl_meta_Preset' for k,n in (('hover','Highlight'),('select','Select'))}

def evidence(w):
    if not hasattr(w,'_uep_bound_action'):w._uep_bound_action={p+'_'+k:0 for p in ('python','fallback') for k in KEYS}
    return w._uep_bound_action
def mark(w,k):evidence(w)['python_'+k]+=1
def call(w,f,*a):return w.call_function(f,*a)
def prop(w,n):return w.get_property(n)
def materials(w):return (call(prop(w,'ButtonBorder'),'GetDynamicMaterial'),call(prop(w,'Text_ActionName'),'GetDynamicFontMaterial'))
def scalar(values,n,v):
    for material in values:
        if valid(material):call(material,'SetScalarParameterValue',n,v)
def play(w,n,forward):call(w,'PlayAnimationForward' if forward else 'PlayAnimationReverse',prop(w,n),1.,False)
def sound(w,k):lib('GameplayStatics').call_function('PlaySound2D',w,ue.load_object(ue.find_class('SoundBase'),SOUNDS[k]),1.,1.,0.,None,None,True)
def style(w,inputtype):
    mark(w,'style');border=prop(w,'ButtonBorder');old=prop(border,'Background');values={n:getattr(old,n) for n in BRUSH_FIELDS};values['DrawAs']=0 if int(inputtype)==1 else 1
    # Original Break/MakeSlateBrush copies only these pins; omitted fields reset
    # to native defaults instead of retaining the whole previous brush.
    call(border,'SetBrush',ue.find_struct('SlateBrush')(**values));return False
def reset(w):mark(w,'reset');call(w,'StopAnimation',prop(w,'OnPressed'));values=materials(w);scalar(values,'Hover_Animate',0.);scalar(values,'Pressed_Animate',0.);return False
def hover(w):
    mark(w,'hover')
    if not prop(w,'IsDisabled'):play(w,'OnHovered',True);sound(w,'hover')
    return False
def unhover(w):
    mark(w,'unhover')
    if not prop(w,'IsDisabled'):play(w,'OnHovered',False)
    return False
def select(w):
    mark(w,'select')
    if not prop(w,'IsDisabled'):play(w,'OnPressed',True)
    return False
def deselect(w):
    mark(w,'deselect')
    if not prop(w,'IsDisabled'):play(w,'OnPressed',False)
    return False
def disable(w):mark(w,'disable');w.set_property('IsDisabled',True);scalar(materials(w),'bIsDisabled',1.);call(w,'ResetMaterials');return False
def enable(w):mark(w,'enable');w.set_property('IsDisabled',False);scalar(materials(w),'bIsDisabled',0.);return False
def click(w):
    mark(w,'click')
    if not prop(w,'IsDisabled'):call(w,NATIVE_CLICK)
    return False
def clicksound(w):mark(w,'clicksound');sound(w,'select');return False
def finished(w):
    mark(w,'finished')
    if not prop(w,'IsDisabled'):play(w,'OnPressed',False)
    return False
def method(k,fn):
    def invoke(self,*args):return fn(self,*args)
    invoke.override=GATES[k];return invoke
class LyraBoundActionPythonProfile:
    Style=method('style',style);Reset=method('reset',reset);Hover=method('hover',hover);Unhover=method('unhover',unhover);Select=method('select',select);Deselect=method('deselect',deselect);Disable=method('disable',disable);Enable=method('enable',enable);Click=method('click',click);ClickSound=method('clicksound',clicksound);Finished=method('finished',finished)
def fallback(k):
    def invoke(self,*args):evidence(self)['fallback_'+k]+=1;return True
    invoke.override=GATES[k];return invoke
class LyraBoundActionBlueprintFallbackProfile:
    Style=fallback('style');Reset=fallback('reset');Hover=fallback('hover');Unhover=fallback('unhover');Select=fallback('select');Deselect=fallback('deselect');Disable=fallback('disable');Enable=fallback('enable');Click=fallback('click');ClickSound=fallback('clicksound');Finished=fallback('finished')
