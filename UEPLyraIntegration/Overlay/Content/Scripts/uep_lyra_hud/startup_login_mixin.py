"""Startup/login state policy; native key arrays, delegates and text stay opaque."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASSES=dict(startup='/Game/UI/Menu/W_LyraStartup.W_LyraStartup_C',login='/Game/UI/Menu/W_UserLoginButton.W_UserLoginButton_C')
METHODS=dict(startup=('focus','listen','press_start','full_menu','initialized','construct','click'),login=('logged_in','listen','refresh','initialized','construct','destruct','click'))
GATES={kind:{m:'UEPStartupLogin'+kind.title()+''.join(v.title() for v in m.split('_')) for m in methods} for kind,methods in METHODS.items()}
ALIASES={kind:{m:'UEPStartupLoginNative'+kind.title()+''.join(v.title() for v in m.split('_')) for m in ('listen_on','listen_off','bind','initialize','text_in','text_out')} for kind in CLASSES}

def evidence(w):
    if not hasattr(w,'_uep_startup_login'):w._uep_startup_login={p+'_'+k+'_'+m:0 for p in ('python','fallback') for k,ms in METHODS.items() for m in ms}
    return w._uep_startup_login

def subsystem(w):return lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',w,ue.find_class('CommonUserSubsystem'))
def controller(w,index):return lib('GameplayStatics').call_function('GetPlayerController',w,int(index))
def one(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value

def invoke(w,k,m,*args):
    evidence(w)['python_'+k+'_'+m]+=1
    if k=='startup':
        if m=='focus':return dict(UseOriginal=False,ReturnValue=w.get_property('PressStartButton'))
        if m=='listen':
            enabled=bool(args[0]);w.set_property('bWaitingForLoginInput',enabled);w.call_function(ALIASES[k]['listen_on' if enabled else 'listen_off'])
        elif m=='press_start':w.call_function('SetListenForLoginInput',True);w.set_property('bWaitingForPlayerInitialize',True)
        elif m=='full_menu':w.call_function('DeactivateWidget');w.call_function('SetListenForLoginInput',False)
        elif m=='initialized':
            if bool(args[0]) and bool(w.get_property('bWaitingForPlayerInitialize')):w.set_property('bWaitingForPlayerInitialize',False);w.call_function('SwitchToFullMenu')
        elif m=='construct':w.call_function(ALIASES[k]['bind'])
        elif m=='click':w.call_function('SetListenForLoginInput',False);w.call_function(ALIASES[k]['initialize'])
        return False
    if m=='logged_in':return dict(UseOriginal=False,ReturnValue=valid(controller(w,w.get_property('PlayerNumber'))))
    if m=='listen':
        enabled=bool(args[0]);w.set_property('WaitingForLoginInput',enabled);w.call_function(ALIASES[k]['listen_on' if enabled else 'listen_off'])
    elif m=='refresh':
        logged=bool(one(w.call_function('IsPlayerLoggedIn')));button=w.get_property('LoginButton');button.call_function('SetOwningPlayer',controller(w,w.get_property('PlayerNumber')) if logged else controller(w,0));w.call_function(ALIASES[k]['text_in' if logged else 'text_out']);w.call_function('SetListenForLoginInput',not logged)
    elif m=='initialized':w.call_function('RefreshLoginState')
    elif m=='construct':w.call_function(ALIASES[k]['bind'])
    elif m=='destruct':
        if valid(subsystem(w)):w.call_function('SetListenForLoginInput',False)
    elif m=='click':
        if bool(one(w.call_function('IsPlayerLoggedIn'))):subsystem(w).call_function('TryToLogOutUser',int(w.get_property('PlayerNumber')),True);w.call_function('RefreshLoginState')
        else:w.call_function(ALIASES[k]['initialize'])
    return False

def method(k,m,fallback):
    def apply(self,*args):
        if fallback:
            evidence(self)['fallback_'+k+'_'+m]+=1
            return dict(UseOriginal=True,ReturnValue=None if m=='focus' else False) if m in ('focus','logged_in') else True
        return invoke(self,k,m,*args)
    apply.override=GATES[k][m]
    if m in ('focus','logged_in'):apply.uep_named_outputs=True
    return apply

for k,methods in METHODS.items():
    for profile,fallback in (('Python',False),('BlueprintFallback',True)):
        name='LyraStartupLogin'+k.title()+profile+'Profile';globals()[name]=type(name,(),{m:method(k,m,fallback) for m in methods})
