"""Settings screen presentation/routing with native localization and async UI."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASSES={k:'/Game/'+v+'.'+v.rsplit('/',1)[-1]+'_C' for k,v in dict(gamma='UI/Settings/Screens/Gamma/W_GammaEditor',hdr='UI/Settings/Screens/HDRCalibration/W_HDRCalibrationEditor',screen='UI/Settings/W_LyraSettingScreen',panel='UI/Settings/W_SettingsPanel').items()}
METHODS=dict(gamma=('focus',),hdr=('construct','luminance'),screen=('register','construct','activate','navigate','action'),panel=('animate',))
GATES={k:{m:'UEPSettingsScreen'+k.title()+m.title() for m in methods} for k,methods in METHODS.items()}
REGISTER_NATIVE='UEPSettingsScreenRegisterNativeTab'
TABS=('GameplayCollection','VideoCollection','AudioCollection','MouseAndKeyboardCollection','GamepadCollection')
ACTIONS={n.casefold():'UEPSettingsScreenPush'+kind for n,kind in (('GameSettings.Action.EditSafeZone','SafeZone'),('GameSettings.Action.EditBrightness','Gamma'),('GameSettings.Action.CalibrateHDR','HDR'))}

def evidence(w):
    if not hasattr(w,'_uep_settings_screens'):w._uep_settings_screens={p+'_'+k+'_'+m:0 for p in ('python','fallback') for k,methods in METHODS.items() for m in methods};w._uep_settings_screens.update(last_route=None,registered_names=[])
    return w._uep_settings_screens
def mark(w,k,m):evidence(w)['python_'+k+'_'+m]+=1
def play(w,n):w.call_function('PlayAnimationForward',w.get_property(n),1.,False)
def register(w,name):
    mark(w,'screen','register');collection,has=w.call_function('GetSettingCollection',name);evidence(w)['registered_names'].append(str(name));w.call_function(REGISTER_NATIVE,name,collection,not bool(has));return False
def construct(w):
    mark(w,'screen','construct')
    for name in TABS:w.call_function('RegisterTopLevelTab',name)
    return False
def activate(w):
    mark(w,'screen','activate');play(w,'OnActivated');panel=w.get_property('Settings_Panel')
    if valid(panel) and panel.is_a(ue.load_class(CLASSES['panel'])):panel.call_function('OnSettingScreenAnim')
    return False
def action(w,setting,tag):
    mark(w,'screen','action');route=ACTIONS.get(str(tag.TagName).casefold());evidence(w)['last_route']=route
    # Original async nodes and interface messages read the original event's
    # native persistent Setting/Action pins; do not manufacture a new payload.
    if route:w.call_function(route)
    return False
def invoke(w,k,m,*a):
    mark(w,k,m) if k!='screen' else None
    if k=='gamma':return dict(UseOriginal=False,ReturnValue=w)
    if k=='hdr':
        if m=='construct':w.set_property('MID_Checkerboard',w.get_property('Checkerboard').call_function('GetDynamicMaterial'))
        else:
            material=w.get_property('MID_Checkerboard')
            if valid(material):material.call_function('SetScalarParameterValue','MaxLuminance',a[0])
        return False
    if k=='panel':play(w,'OnParentScreenActivated');return False
    if m=='register':return register(w,a[0])
    if m=='construct':return construct(w)
    if m=='activate':return activate(w)
    if m=='navigate':mark(w,k,m);w.call_function('NavigateToSetting',a[0]);return False
    return action(w,*a)
def method(k,m,fallback):
    def apply(self,*a):
        if fallback:evidence(self)['fallback_'+k+'_'+m]+=1;return dict(UseOriginal=True,ReturnValue=None) if m=='focus' else True
        return invoke(self,k,m,*a)
    apply.override=GATES[k][m]
    if m=='focus':apply.uep_named_outputs=True
    return apply
for label,methods in METHODS.items():
    for name,fallback_profile in (('Python',False),('BlueprintFallback',True)):
        clsname='LyraSettingsScreen'+label.title()+name+'Profile';globals()[clsname]=type(clsname,(),{m:method(label,m,fallback_profile) for m in methods})
