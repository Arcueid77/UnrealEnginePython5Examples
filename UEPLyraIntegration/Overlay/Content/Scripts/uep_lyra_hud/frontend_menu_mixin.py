"""Frontend policy; original native async/UI/session adapters retain payloads."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib

CLASS='/Game/UI/Menu/W_LyraFrontEnd.W_LyraFrontEnd_C'
METHODS=('focus','activate','start','options','credits','replays','quit','logout','quit_result','logout_result','logout_success')
GATES={m:'UEPFrontend'+''.join(v.title() for v in m.split('_')) for m in METHODS}
ALIASES={m:'UEPFrontendNative'+''.join(v.title() for v in m.split('_')) for m in ('start','options','credits','replays','quit','logout','destroy_session','startup')}

def evidence(w):
    if not hasattr(w,'_uep_frontend'):w._uep_frontend={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_frontend

def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='focus':return dict(UseOriginal=False,ReturnValue=w.get_property('StartGameButton'))
    if m=='activate':
        w.call_function('PlayAnimationForward',w.get_property('OnActivated'),1.,False)
        w.call_function('GetDesiredFocusTarget').call_function('SetFocus')
    elif m in ('start','options','credits','replays','quit','logout'):w.call_function(ALIASES[m])
    elif m=='quit_result':
        if int(args[0])==0:lib('KismetSystemLibrary').call_function('QuitGame',w,None,0,False)
    elif m=='logout_result':
        if int(args[0])==0:w.call_function(ALIASES['destroy_session'])
    elif m=='logout_success':
        subsystem=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',w,ue.find_class('CommonUserSubsystem'))
        subsystem.call_function('TryToLogOutUser',0,False)
        subsystem.call_function('ResetUserState')
        w.call_function(ALIASES['startup'])
    return False

def method(m,fallback):
    def apply(self,*args):
        if fallback:
            evidence(self)['fallback_'+m]+=1
            return dict(UseOriginal=True,ReturnValue=None) if m=='focus' else True
        return invoke(self,m,*args)
    apply.override=GATES[m]
    if m=='focus':apply.uep_named_outputs=True
    return apply

for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraFrontendMenu'+profile+'Profile']=type('LyraFrontendMenu'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
