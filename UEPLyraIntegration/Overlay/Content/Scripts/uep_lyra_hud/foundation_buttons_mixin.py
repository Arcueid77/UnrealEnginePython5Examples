"""Foundation button/tab policies; native CommonUI routing, FText and UMG remain."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASSES={k:'/Game/'+p+'.'+p.rsplit('/',1)[-1]+'_C' for k,p in (('base','UI/Foundation/Buttons/W_LyraButton'),('tab','UI/Foundation/Buttons/W_LyraButtonTab'),('tabs','UI/Foundation/TabbedView/W_HorizontalTabList'))}
GATES={k:'UEPFoundation'+v for k,v in dict(combined='TextAndStyle',controller='ControllerStyle',style='Style',mouse='MouseStyle',alignupdate='AlignUpdate',align='Alignment',textstyle='TextStyle',progress='Progress',pre='PreConstruct',held='Held',text='Text',tabtext='TabText',hover='Hover',unhover='Unhover',select='Select',deselect='Deselect',tabstyle='TabStyle',debug='DebugTabs',tabpre='TabsPre',refresh='TabsVisibility').items()}
BIND='UEPFoundationBindNativeTabDelegates'
HOVER_SOUND='/Game/Audio/Sounds/UI/sfx_UI_SubMenu_Highlight_nl_meta_Preset.sfx_UI_SubMenu_Highlight_nl_meta_Preset'
SELECT_SOUND='/Game/Audio/Sounds/UI/sfx_UI_SubMenu_Select_nl_meta_Preset.sfx_UI_SubMenu_Select_nl_meta_Preset'


def evidence(w):
    if not hasattr(w,'_uep_foundation_buttons'):w._uep_foundation_buttons={p+'_'+k:0 for p in ('python','fallback') for k in GATES};w._uep_foundation_buttons.update(hover_sounds=0,select_sounds=0,selected_stops=0)
    return w._uep_foundation_buttons
def mark(w,k):evidence(w)['python_'+k]+=1
def gamepad(w):return bool(lib('CommonUIExtensions').call_function('IsOwningPlayerUsingGamepad',w))
def combined(w,inputtype):mark(w,'combined');w.call_function('UpdateStyle',int(inputtype)==1);w.call_function('UpdateTextStyle');return False
def controller(w,value):mark(w,'controller');w.set_property('ControllerInputStyle',value);w.call_function('UpdateStyle',gamepad(w));return False
def mouse(w,value):mark(w,'mouse');w.set_property('DefaultStyle',value);w.call_function('UpdateStyle',gamepad(w));return False
def style(w,using):
    mark(w,'style');controller=w.get_property('ControllerInputStyle');w.call_function('SetStyle',controller if using and valid(controller) else w.get_property('DefaultStyle'));return False
def alignupdate(w):
    mark(w,'alignupdate');slot=w.get_property('ContentBorder').call_function('GetContentSlot')
    if valid(slot) and slot.is_a(ue.find_class('BorderSlot')):slot.call_function('SetHorizontalAlignment',w.get_property('ContentAlignment'))
    return False
def align(w,value):mark(w,'align');w.set_property('ContentAlignment',value);w.call_function('UpdateContentAlignment');return False
def textstyle(w):mark(w,'textstyle');w.get_property('Text').call_function('SetStyle',w.call_function('GetCurrentTextStyleClass'));return False
def progress(w):mark(w,'progress');return dict(UseOriginal=False,Progress=float(w.get_property('PressProgress')))
def pre(w):
    mark(w,'pre');w.call_function('UpdateContentAlignment');label=w.get_property('Text');label.call_function('SetText',lib('KismetTextLibrary').call_function('GetEmptyText'));w.call_function('UpdateTextStyle');label.call_function('SetTextTransformPolicy',w.get_property('TextTransformPolicy'));label.call_function('SetJustification',w.get_property('TextJustification'));return False
def held(w,value):mark(w,'held');w.set_property('PressProgress',value);return False
def text(w):mark(w,'text');return True
def tabtext(w):mark(w,'tabtext');return True
def play(w,animation,forward):w.call_function('PlayAnimationForward' if forward else 'PlayAnimationReverse',w.get_property(animation),1.,False)
def sound(w,path):lib('GameplayStatics').call_function('PlaySound2D',w,ue.load_object(ue.find_class('SoundBase'),path),1.,1.,0.,None,None,True)
def hover(w):
    mark(w,'hover')
    if not w.call_function('GetSelected'):play(w,'Hovered',True);sound(w,HOVER_SOUND);evidence(w)['hover_sounds']+=1
    return False
def unhover(w):
    mark(w,'unhover')
    if not w.call_function('GetSelected'):play(w,'Hovered',False)
    return False
def select(w):mark(w,'select');play(w,'Selected',True);sound(w,SELECT_SOUND);evidence(w)['select_sounds']+=1;return False
def deselect(w):
    mark(w,'deselect');play(w,'Hovered',False);animation=w.get_property('Selected')
    if w.call_function('IsAnimationPlaying',animation):w.call_function('StopAnimation',animation);evidence(w)['selected_stops']+=1
    play(w,'Selected',False);return False
def tabstyle(w,button):
    mark(w,'tabstyle');slot=w.get_property('TabButtonBox').call_function('AddChildToHorizontalBox',button);slot.call_function('SetPadding',w.get_property('TabButtonPadding'));button.call_function('SetMinDimensions',w.get_property('MinTabWidth'),0)
    if w.get_property('UseButtonStyle'):button.call_function('SetStyle',w.get_property('ButtonStyle'))
    w.call_function('Refresh Next/Previous Visibility');return False
def debug(w):
    mark(w,'debug');w.get_property('TabButtonBox').call_function('ClearChildren')
    for _ in range(1,int(w.get_property('DebugTabCount'))+1):
        button=lib('WidgetBlueprintLibrary').call_function('Create',w,w.get_property('DebugButtonTypeDisplay'),w.call_function('GetOwningPlayer'));button.set_property('bSelectable',False);w.call_function('UpdateTabStyles',button)
    return False
def tabpre(w,design):
    mark(w,'tabpre');w.get_property('PreviousTabAction').call_function('SetInputAction',w.get_property('PreviousTabInputActionData'));w.get_property('NextTabAction').call_function('SetInputAction',w.get_property('NextTabInputActionData'));w.call_function(BIND)
    if design and valid(w.get_property('DebugButtonTypeDisplay')):w.call_function('DebugCreateTabsForDesigner')
    return False
def refresh(w):
    mark(w,'refresh');visibility=2 if int(w.call_function('GetTabCount'))<=1 else 0
    # ESlateVisibility.Hidden is 2;Collapsed is 1. Preserve layout space.
    w.get_property('PreviousTabActionWrapper').call_function('SetVisibility',visibility);w.get_property('NextTabActionWrapper').call_function('SetVisibility',visibility);return False


def method(k,fn):
    def invoke(self,*args):return fn(self,*args)
    invoke.override=GATES[k];return invoke
class LyraFoundationBasePythonProfile:
    Combined=method('combined',combined);Controller=method('controller',controller);Style=method('style',style);Mouse=method('mouse',mouse);AlignUpdate=method('alignupdate',alignupdate);Align=method('align',align);TextStyle=method('textstyle',textstyle);Held=method('held',held);Text=method('text',text)
    def Pre(self,IsDesignTime):return pre(self)
    Pre.override=GATES['pre']
    def Progress(self):return progress(self)
    Progress.override=GATES['progress'];Progress.uep_named_outputs=True
class LyraFoundationTabPythonProfile:
    Text=method('tabtext',tabtext);Hover=method('hover',hover);Unhover=method('unhover',unhover);Select=method('select',select);Deselect=method('deselect',deselect)
class LyraFoundationTabsPythonProfile:
    Style=method('tabstyle',tabstyle);Debug=method('debug',debug);Pre=method('tabpre',tabpre);Refresh=method('refresh',refresh)


def fallback(k):
    def invoke(self,*args):evidence(self)['fallback_'+k]+=1;return dict(UseOriginal=True,Progress=0.) if k=='progress' else True
    invoke.override=GATES[k]
    if k=='progress':invoke.uep_named_outputs=True
    return invoke
class LyraFoundationBaseBlueprintFallbackProfile:
    Combined=fallback('combined');Controller=fallback('controller');Style=fallback('style');Mouse=fallback('mouse');AlignUpdate=fallback('alignupdate');Align=fallback('align');TextStyle=fallback('textstyle');Progress=fallback('progress');Pre=fallback('pre');Held=fallback('held');Text=fallback('text')
class LyraFoundationTabBlueprintFallbackProfile:
    Text=fallback('tabtext');Hover=fallback('hover');Unhover=fallback('unhover');Select=fallback('select');Deselect=fallback('deselect')
class LyraFoundationTabsBlueprintFallbackProfile:
    Style=fallback('tabstyle');Debug=fallback('debug');Pre=fallback('tabpre');Refresh=fallback('refresh')
