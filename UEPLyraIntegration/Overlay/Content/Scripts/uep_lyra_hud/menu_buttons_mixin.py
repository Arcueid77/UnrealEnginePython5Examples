"""Menu/tile policies with native latent animation and opaque text transport."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASSES={k:'/Game/UI/Menu/'+n+'.'+n+'_C' for k,n in dict(menu='W_LyraMenuButton',tile='W_LyraTileButton').items()}
CHILDREN={k:'/Game/UI/Menu/'+n+'.'+n+'_C' for k,n in dict(modal='W_LyraMenuButton_Modal',arrow='W_LyraArrowButton').items()}
KEYS=('textstyle','layout','art','reset','progress','pre','construct','hover','unhover','click','clicksound','finished','select','deselect','disable','enable','text')
GATES={k:'UEPMenu'+k.title() for k in KEYS}
NATIVE_CLICK='UEPMenuStartNativeClick'

def evidence(w):
    if not hasattr(w,'_uep_menu_buttons'):w._uep_menu_buttons={p+'_'+k:0 for p in ('python','fallback') for k in KEYS}
    return w._uep_menu_buttons
def mark(w,k):evidence(w)['python_'+k]+=1
def call(w,f,*a):return w.call_function(f,*a)
def prop(w,n):return w.get_property(n)
def is_tile(w):return w.is_a(ue.load_class(CLASSES['tile']))
def play(w,n,forward):return call(w,'PlayAnimationForward' if forward else 'PlayAnimationReverse',prop(w,n),1.,False)
def materials(w):return (call(prop(w,'ButtonBorder'),'GetDynamicMaterial'),call(prop(w,'ButtonTextBlock'),'GetDynamicFontMaterial'))
def scalar(values,name,value):
    for material in values:
        if valid(material):call(material,'SetScalarParameterValue',name,value)
def sound(w,selected):
    family='Lobby' if is_tile(w) else ('SubMenu' if prop(w,'UseIconOverride') else 'MainMenu')
    path='/Game/Audio/Sounds/UI/sfx_UI_'+family+'_'+('Select' if selected else 'Highlight')+'_nl_meta_Preset'
    lib('GameplayStatics').call_function('PlaySound2D',w,ue.load_object(ue.find_class('SoundBase'),path+'.'+path.rsplit('/',1)[-1]),1.,1.,0.,None,None,True)
def textstyle(w):
    mark(w,'textstyle')
    if is_tile(w):return True  # Both original FText setters stay inside BlueprintVM.
    label=prop(w,'ButtonTextBlock');call(label,'SetFont',prop(w,'Font'));call(label,'SetTextTransformPolicy',prop(w,'TextCase'));return False
def text(w):mark(w,'text');return True
def reset(w):
    mark(w,'reset');call(w,'StopAnimation',prop(w,'OnPressed'));values=materials(w);scalar(values,'Hover_Animate',0.);scalar(values,'Pressed_Animate',0.);return False
def progress(w):mark(w,'progress');return dict(UseOriginal=False,Progress=float(prop(w,'PressProgress')))
def layout(w):
    mark(w,'layout')
    for n in ('Ring','Glow','TextShadow'):call(prop(w,n),'SetVisibility',3 if prop(w,'UseImageOverlays') else 1)
    call(prop(w,'ButtonBorder'),'SetBrush',prop(w,'ButtonBorderBrush'))
    for n in ('AnimBoundSpacer_Left','AnimBoundSpacer_Right'):call(prop(w,n),'SetVisibility',3 if prop(w,'UseScaleChangeSpacers') else 1)
    margin=ue.find_struct('Margin');slot=lib('WidgetLayoutLibrary').call_function('SlotAsHorizontalBoxSlot',prop(w,'ButtonBorder'));call(slot,'SetPadding',margin(Left=prop(w,'HitTestPadding_X'),Top=prop(w,'HitTestPadding_Y'),Right=prop(w,'HitTestPadding_X'),Bottom=prop(w,'HitTestPadding_Y')))
    slot=lib('WidgetLayoutLibrary').call_function('SlotAsOverlaySlot',prop(w,'InputActionWidget'));call(slot,'SetPadding',prop(w,'InputPadding'));call(slot,'SetHorizontalAlignment',prop(w,'InputHorzAlignment'));call(slot,'SetVerticalAlignment',prop(w,'InputVertAlignment'))
    if prop(w,'UseIconOverride'):
        call(prop(w,'TextIconSwitch'),'SetActiveWidget',prop(w,'IconOvr'));icon=prop(w,'Icon');call(icon,'SetBrush',prop(w,'IconBrush'));call(icon,'SetRenderTransform',ue.find_struct('WidgetTransform')(Scale=ue.find_struct('Vector2D')(X=-1. if prop(w,'FlipIconXDimension') else 1.,Y=1.)))
    else:
        call(prop(w,'TextIconSwitch'),'SetActiveWidget',prop(w,'TextOvr'));slot=lib('WidgetLayoutLibrary').call_function('SlotAsWidgetSwitcherSlot',prop(w,'TextOvr'));call(slot,'SetPadding',margin(Left=prop(w,'TextLeftRightPadding'),Right=prop(w,'TextLeftRightPadding')))
    return False
def art(w):
    mark(w,'art');material=call(prop(w,'KeyArt'),'GetDynamicMaterial')
    if valid(material):call(material,'SetTextureParameterValue','TileArt',prop(w,'KeyArtTexture'))
    return False
def prepare(w,k):
    mark(w,k);call(w,'UpdateTextStyle');call(w,'UpdateTileArt' if is_tile(w) else 'UpdateButtonStyles');call(w,'ResetMaterials');return False
def hover(w):
    mark(w,'hover')
    if not prop(w,'IsDisabled'):play(w,'OnHovered',True);sound(w,False)
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
def clicksound(w):mark(w,'clicksound');sound(w,True);return False
def finished(w):
    mark(w,'finished')
    if not prop(w,'IsDisabled'):play(w,'OnPressed',False)
    return False
def method(k,fn):
    def invoke(self,*args):return fn(self,*args)
    invoke.override=GATES[k];return invoke
def pre(w,design):return prepare(w,'pre')
def construct(w):return prepare(w,'construct')

class MenuSharedPythonProfile:
    TextStyle=method('textstyle',textstyle);Reset=method('reset',reset);Hover=method('hover',hover);Unhover=method('unhover',unhover);Select=method('select',select);Deselect=method('deselect',deselect);Disable=method('disable',disable);Enable=method('enable',enable);Click=method('click',click);ClickSound=method('clicksound',clicksound);Finished=method('finished',finished);Pre=method('pre',pre)
    def Progress(self):return progress(self)
    Progress.override=GATES['progress'];Progress.uep_named_outputs=True
class LyraMenuMenuPythonProfile:
    Layout=method('layout',layout);Text=method('text',text)
class LyraMenuTilePythonProfile:
    Art=method('art',art);Construct=method('construct',construct)
def fallback(k):
    def invoke(self,*args):evidence(self)['fallback_'+k]+=1;return dict(UseOriginal=True,Progress=0.) if k=='progress' else True
    invoke.override=GATES[k]
    if k=='progress':invoke.uep_named_outputs=True
    return invoke
class MenuSharedBlueprintFallbackProfile:
    TextStyle=fallback('textstyle');Reset=fallback('reset');Hover=fallback('hover');Unhover=fallback('unhover');Select=fallback('select');Deselect=fallback('deselect');Disable=fallback('disable');Enable=fallback('enable');Click=fallback('click');ClickSound=fallback('clicksound');Finished=fallback('finished');Pre=fallback('pre');Progress=fallback('progress')
class LyraMenuMenuBlueprintFallbackProfile:
    Layout=fallback('layout');Text=fallback('text')
class LyraMenuTileBlueprintFallbackProfile:
    Art=fallback('art');Construct=fallback('construct')

# The native registry reads each class __dict__, not its Python MRO.
for shared,targets in ((MenuSharedPythonProfile,(LyraMenuMenuPythonProfile,LyraMenuTilePythonProfile)),(MenuSharedBlueprintFallbackProfile,(LyraMenuMenuBlueprintFallbackProfile,LyraMenuTileBlueprintFallbackProfile))):
    for name,value in vars(shared).items():
        if callable(value) and hasattr(value,'override'):
            for target in targets:setattr(target,name,value)
