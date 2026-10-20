"""Default-map portal local-overlap/widget/default-color/offline-host policy."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
CLASS='/Game/System/DefaultEditorMap/B_TeleportToUserFacingExperience.B_TeleportToUserFacingExperience_C'
METHODS=('widget','color','overlap','load','pushed')
GATES={m:'UEPEditorExperiencePortal'+m.title() for m in METHODS}
NATIVE={m:'UEPEditorExperiencePortalNative'+m.title() for m in ('delay','color','push','request')}
def evidence(actor):
    if not hasattr(actor,'_uep_editor_portal'):actor._uep_editor_portal={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return actor._uep_editor_portal
def invoke(actor,m,*args):
    evidence(actor)['python_'+m]+=1
    if m=='widget':args[0].call_function('Set User Facing Experience',actor.get_property('UserFacingExperienceToLoad'));actor.call_function(NATIVE['delay'])
    elif m=='color':
        if bool(args[0]):actor.call_function(NATIVE['color'])
    elif m=='overlap':
        other=args[0]
        if valid(other) and other.is_a(ue.find_class('Pawn')):
            controller=other.call_function('GetController')
            if valid(controller) and controller.call_function('IsLocalPlayerController') and controller.is_a(ue.find_class('PlayerController')):actor.call_function('LoadIntoExperience',controller)
    elif m=='load':
        if valid(actor.get_property('UserFacingExperienceToLoad')):actor.call_function(NATIVE['push'])
    elif m=='pushed':
        request=actor.call_function(NATIVE['request'],actor.get_property('UserFacingExperienceToLoad'));sub=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',actor,ue.find_class('CommonSessionSubsystem'));sub.call_function('HostSession',args[0],request)
    return False
def method(m,fallback):
    def apply(self,*args):
        if m in ('widget','color'):evidence(self)['begin_experience']=self.get_property('UserFacingExperienceToLoad')
        if m=='color':evidence(self)['native_default_flag']=bool(args[0])
        if m=='pushed':evidence(self)['pushed_experience']=self.get_property('UserFacingExperienceToLoad')
        if fallback:evidence(self)['fallback_'+m]+=1;return True
        return invoke(self,m,*args)
    apply.override=GATES[m];return apply
for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraEditorExperiencePortal'+profile+'Profile']=type('LyraEditorExperiencePortal'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
