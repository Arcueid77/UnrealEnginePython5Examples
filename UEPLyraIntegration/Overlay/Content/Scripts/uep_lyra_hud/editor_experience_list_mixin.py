"""Default-map 3D list filter/order/layout;native async and deferred spawn IO."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
CLASS='/Game/System/DefaultEditorMap/B_ExperienceList3D.B_ExperienceList3D_C'
METHODS=('begin','loaded')
GATES={m:'UEPEditorExperienceList'+m.title() for m in METHODS}
NATIVE={m:'UEPEditorExperienceListNative'+m.title() for m in ('load','spawn')}
def evidence(actor):
    if not hasattr(actor,'_uep_editor_experiences'):actor._uep_editor_experiences={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return actor._uep_editor_experiences
def filter_experiences(loaded,show_all,cls,initial=()):
    result=list(initial)
    for exp in loaded:
        if valid(exp) and exp.is_a(cls):
            if exp.get_property('bShowInFrontEnd') and exp.get_property('bIsDefaultExperience'):result.insert(0,exp)
            elif show_all:result.append(exp)
    return result
def invoke(actor,m,*args):
    evidence(actor)['python_'+m]+=1
    if m=='begin':actor.set_property('UserFacingExperienceList',list(actor.get_property('AdditionalExperiencesToShow')));actor.call_function(NATIVE['load'])
    elif m=='loaded':
        values=filter_experiences(args[0],bool(actor.get_property('ShowAllExperiences')),ue.find_class('LyraUserFacingExperienceDefinition'),actor.get_property('UserFacingExperienceList'))
        actor.set_property('UserFacingExperienceList',values)
        for index,exp in enumerate(values):
            offset=(float(index)-float(len(values))*.5+.5)*float(actor.get_property('PortalSpacing'));transform=actor.get_property('DefaultSceneRoot').call_function('K2_GetComponentToWorld');location=lib('KismetMathLibrary').call_function('TransformLocation',transform,ue.FVector(offset,0.,0.));portal=actor.call_function(NATIVE['spawn'],exp,location,actor.get_actor_rotation());portals=list(actor.get_property('ExperiencePortals'));portals.append(portal);actor.set_property('ExperiencePortals',portals)
    return False
def method(m,fallback):
    def apply(self,*args):
        if m=='loaded':evidence(self)['loaded_inputs']=list(args[0])
        if fallback:evidence(self)['fallback_'+m]+=1;return True
        return invoke(self,m,*args)
    apply.override=GATES[m];return apply
for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraEditorExperienceList'+profile+'Profile']=type('LyraEditorExperienceList'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
