"""Experience-selection policy with original native login/push/preparation waits."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_hud import experience_preparation_policy as preparation

CLASS='/Game/UI/Menu/Experiences/W_ExperienceSelectionScreen.W_ExperienceSelectionScreen_C'
METHODS=('focus','activate','selected','spinner','host','browse','quick','browse_result','quick_result','prepared','preparation_loaded')
GATES={m:'UEPExperienceScreen'+''.join(v.title() for v in m.split('_')) for m in METHODS}
NATIVE={m:'UEPExperienceScreenNative'+m.title() for m in ('host','browse','quick','browser','prepare','request')}
NATIVE['request']='UEPExperienceScreenNativeOnlineRequest'

def evidence(w):
    if not hasattr(w,'_uep_experience_screen'):w._uep_experience_screen={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_experience_screen

def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='focus':return dict(UseOriginal=False,ReturnValue=w.get_property('QuickplayButton'))
    if m=='activate':w.call_function('PlayAnimationForward',w.get_property('OnActivated'),1.,False);w.call_function('ShowProgressSpinner',False)
    elif m=='selected':w.set_property('SelectedExperience',args[0])
    elif m=='spinner':w.get_property('ProgressSpinner').call_function('SetVisibility',0 if bool(args[0]) else 2)
    elif m in ('host','browse','quick'):w.call_function(NATIVE[m])
    elif m=='browse_result':w.call_function(NATIVE['browser'])
    elif m=='quick_result':
        if bool(args[0]):
            w.get_property('W_ExperienceList').call_function('SelectRandomExperience')
            if valid(w.get_property('SelectedExperience')):w.call_function(NATIVE['prepare'])
    elif m=='prepared':
        request=w.call_function(NATIVE['request'],w.get_property('SelectedExperience'));sub=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',w,ue.find_class('CommonSessionSubsystem'));sub.call_function('QuickPlaySession',w.call_function('GetOwningPlayer'),request);w.call_function('ShowProgressSpinner',True)
    elif m=='preparation_loaded':preparation.finish(w,args[0])
    return False

def method(m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+m]+=1;return dict(UseOriginal=True,ReturnValue=None) if m=='focus' else True
        return invoke(self,m,*args)
    apply.override=GATES[m]
    if m=='focus':apply.uep_named_outputs=True
    return apply

for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraExperienceScreen'+profile+'Profile']=type('LyraExperienceScreen'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
