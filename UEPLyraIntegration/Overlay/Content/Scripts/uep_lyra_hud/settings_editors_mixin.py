"""Settings presentation policies; native settings values and FText stay native."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASSES={k:'/Game/'+v+'.'+v.rsplit('/',1)[-1]+'_C' for k,v in dict(background='UI/Settings/Editors/W_SettingEntryBackground',action='UI/Settings/Editors/W_SettingsListEntry_Action',discrete='UI/Settings/Editors/W_SettingsListEntry_Discrete',keyboard='UI/Settings/Editors/W_SettingsListEntry_KBMBinding',missing='UI/Settings/Editors/W_SettingsListEntry_Missing',scalar='UI/Settings/Editors/W_SettingsListEntry_Scalar',collection='UI/Settings/Editors/W_SettingsListEntry_SubCollection',rotator='UI/Settings/Editors/W_SettingsRotator',details='UI/Settings/Extensions/Enum/W_EnumOptionDetailsEntry',extension='UI/Settings/Extensions/Enum/W_EnumOptionExtension').items()}
FOCUS=dict(action='Button_Action',discrete='Rotator_SettingValue',keyboard='Button_PrimaryKey',scalar='Slider_SettingValue',collection='Button_Navigate')
METHODS=dict(background=('enter','leave'),action=('enter','leave','focus'),discrete=('enter','leave','focus','sound'),keyboard=('enter','leave','focus'),missing=('enter','leave'),scalar=('enter','leave','focus','value','default'),collection=('enter','leave','focus'),rotator=('style','selected','default'),details=('selected',),extension=('rebuild',))
GATES={k:{m:'UEPSettings'+k.title()+m.title() for m in v} for k,v in METHODS.items()}
BROADCAST={k:'UEPSettingsBackgroundNativeBroadcast'+k.title() for k in ('enter','leave')}
OPTION_COUNT='UEPSettingsNativeOptionCount'
OPTION_CREATE='UEPSettingsNativeOptionCreate'
BRUSH_FIELDS=('TintColor','DrawAs','Tiling','Mirroring','ImageSize','Margin','OutlineSettings')
PIP_MATERIALS=tuple('/Game/UI/Menu/Art/'+n+'.'+n for n in ('MI_UI_SettingsRotator','MI_UI_SettingsRotator_SizeB','MI_UI_SettingsRotator_SizeC','MI_UI_SettingsRotator_SizeD'))

def evidence(w):
    if not hasattr(w,'_uep_settings_editors'):w._uep_settings_editors={p+'_'+k+'_'+m:0 for p in ('python','fallback') for k,v in METHODS.items() for m in v}
    return w._uep_settings_editors
def mark(w,k,m):evidence(w)['python_'+k+'_'+m]+=1
def call(w,f,*a):return w.call_function(f,*a)
def prop(w,n):return w.get_property(n)
def using_touch(w,k):
    if k in ('action','keyboard'):
        sub=lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',call(w,'GetOwningPlayer'),ue.find_class('CommonInputSubsystem'))
        return valid(sub) and int(call(sub,'GetCurrentInputType'))==2
    return bool(lib('CommonUIExtensions').call_function('IsOwningPlayerUsingTouch',w))
def sound(w,family,action,pitch=1.):
    n='sfx_UI_'+family+'_'+action+'_nl_meta_Preset';lib('GameplayStatics').call_function('PlaySound2D',w,ue.load_object(ue.find_class('SoundBase'),'/Game/Audio/Sounds/UI/'+n+'.'+n),1.,pitch,0.,None,None,True)
def hover(w,k,enter):
    mark(w,k,'enter' if enter else 'leave')
    if not using_touch(w,k):
        call(w,'PlayAnimationForward' if enter else 'PlayAnimationReverse',prop(w,'OnHovered' if k=='background' else 'OnHover'),1.,False)
        if k=='background':call(w,BROADCAST['enter' if enter else 'leave'])
        elif k=='scalar' and enter:sound(w,'SubMenu','Highlight')
    return False
def focus(w,k):mark(w,k,'focus');return dict(UseOriginal=False,ReturnValue=prop(w,FOCUS[k]))
def scalar(w,k,value,default):
    mark(w,k,'default' if default else 'value');material=call(prop(w,'ProgressBar'),'GetDynamicMaterial')
    if valid(material):call(material,'SetScalarParameterValue','DefaultValue' if default else 'Progress',value)
    if not default:sound(w,'Lobby','Highlight',.9+min(1.,max(0.,float(value)))*.2)
    return False
def pips_style(w,k,count):
    mark(w,k,'style');count=int(count);index=3 if count>7 else 2 if count>5 else 1 if count>3 else 0;call(prop(w,'OptionsScalingSizeBox'),'SetWidthOverride',(192.,256.,320.,384.)[index]);image=prop(w,'OptionsPips');old=prop(image,'Brush');values={n:getattr(old,n) for n in BRUSH_FIELDS};values['ResourceObject']=ue.load_object(ue.find_class('MaterialInterface'),PIP_MATERIALS[index]);call(image,'SetBrush',ue.find_struct('SlateBrush')(**values));material=call(image,'GetDynamicMaterial')
    if valid(material):call(material,'SetScalarParameterValue','Options',float(count))
    return False
def pips_index(w,k,value,default):
    mark(w,k,'default' if default else 'selected');material=call(prop(w,'OptionsPips'),'GetDynamicMaterial')
    if valid(material):call(material,'SetScalarParameterValue','DefaultOption' if default else 'SelectedOption',float(value))
    return False
def detail(w,k,selected):
    mark(w,k,'selected');materials=(call(prop(w,'EntryText'),'GetDynamicFontMaterial'),call(prop(w,'Diamond'),'GetDynamicMaterial'),call(prop(w,'EntryBorder'),'GetDynamicMaterial'))
    for material in materials:
        if valid(material):call(material,'SetScalarParameterValue','Hover_Animate',1. if selected else 0.)
    return False
def rebuild(w,k,setting):
    mark(w,k,'rebuild');call(prop(w,'EnumOptions'),'Reset',False)
    if valid(setting) and setting.is_a(ue.find_class('GameSettingValueDiscrete')):
        for index in range(int(call(w,OPTION_COUNT,setting))):call(w,OPTION_CREATE,setting,index,index==int(call(setting,'GetDiscreteOptionIndex')))
    return False
def invoke(w,k,m,*args):
    if m in ('enter','leave'):return hover(w,k,m=='enter')
    if m=='focus':return focus(w,k)
    if m=='sound':mark(w,k,m);sound(w,'SubMenu','Select');return False
    if k=='scalar':return scalar(w,k,args[0],m=='default')
    if k=='rotator':return pips_style(w,k,args[0]) if m=='style' else pips_index(w,k,args[0],m=='default')
    if k=='details':return detail(w,k,args[0])
    return rebuild(w,k,args[0])
def method(k,m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+k+'_'+m]+=1;return dict(UseOriginal=True,ReturnValue=None) if m=='focus' else True
        return invoke(self,k,m,*args)
    apply.override=GATES[k][m]
    if m=='focus':apply.uep_named_outputs=True
    return apply
for label,methods in METHODS.items():
    for name,fallback_profile in (('Python',False),('BlueprintFallback',True)):
        clsname='LyraSettingsEditor'+label.title()+name+'Profile';globals()[clsname]=type(clsname,(),{m:method(label,m,fallback_profile) for m in methods})
