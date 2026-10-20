"""Host screen choices and request policy; original text/latent/delegate IO retained."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_hud import experience_preparation_policy as preparation

CLASS='/Game/UI/Menu/Experiences/W_HostSessionScreen.W_HostSessionScreen_C'
METHODS=('focus','activate','mode_text','bots_text','request','mode_cycle','bots_toggle','selected','online_result','spinner_pushed','prepared','completed','preparation_loaded')
GATES={m:'UEPHostSession'+''.join(v.title() for v in m.split('_')) for m in METHODS}
NATIVE={m:'UEPHostSessionNative'+''.join(v.title() for v in m.split('_')) for m in ('mode_text','bots_on','bots_off','login','spinner','prepare','submit','failure')}

def evidence(w):
    if not hasattr(w,'_uep_host_session'):w._uep_host_session={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_host_session

def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v

def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='focus':return dict(UseOriginal=False,ReturnValue=w.get_property('BotsToggleButton'))
    if m=='request':
        selected=w.get_property('SelectedExperience');request=None
        if valid(selected):
            request=selected.call_function('CreateHostingRequest',w);request.set_property('OnlineMode',int(w.get_property('Online Mode')))
            if not w.get_property('BotsEnabled'):values=dict(request.get_property('ExtraArgs'));values['NumBots']='0';request.set_property('ExtraArgs',values)
        return dict(UseOriginal=False,ReturnValue=request)
    if m=='activate':w.call_function('UpdateOnlineModeText');w.call_function('UpdateBotsEnabledText');w.call_function('PlayAnimationForward',w.get_property('OnActivated'),1.,False)
    elif m=='mode_text':w.call_function(NATIVE['mode_text'])
    elif m=='bots_text':w.call_function(NATIVE['bots_on' if w.get_property('BotsEnabled') else 'bots_off'])
    elif m=='mode_cycle':w.set_property('Online Mode',{0:2,1:0,2:1}[int(w.get_property('Online Mode'))]);w.call_function('UpdateOnlineModeText')
    elif m=='bots_toggle':w.set_property('BotsEnabled',not bool(w.get_property('BotsEnabled')));w.call_function('UpdateBotsEnabledText')
    elif m=='selected':
        w.set_property('SelectedExperience',args[0])
        if valid(w.get_property('SelectedExperience')):w.call_function(NATIVE['login' if int(w.get_property('Online Mode'))==2 else 'spinner'])
    elif m=='online_result':
        if bool(args[0]):w.call_function(NATIVE['spinner'])
    elif m=='spinner_pushed':w.set_property('SpinnerWidget',args[0]);w.call_function(NATIVE['prepare'])
    elif m=='prepared':w.call_function(NATIVE['submit'],one(w.call_function('CreateHostingRequest')))
    elif m=='completed':
        if not bool(args[0]):w.call_function(NATIVE['failure'])
    elif m=='preparation_loaded':preparation.finish(w,args[0])
    return False

def method(m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+m]+=1;return dict(UseOriginal=True,ReturnValue=None) if m in ('focus','request') else True
        return invoke(self,m,*args)
    apply.override=GATES[m]
    if m in ('focus','request'):apply.uep_named_outputs=True
    return apply

for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraHostSession'+profile+'Profile']=type('LyraHostSession'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
