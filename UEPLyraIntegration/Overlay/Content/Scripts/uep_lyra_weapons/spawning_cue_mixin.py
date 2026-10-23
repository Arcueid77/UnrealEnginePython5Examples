"""Spawn Cue business with original native async/delegate/latent/Timeline flows."""
import unreal_engine as ue
from .macro_policies import ignore_tag
from unreal_engine.enums import EAttachLocation,ENCPoolMethod
from uep_lyra_world.effect_pad_mixin import valid
from .hero_burst_cue_mixin import lib,components

CLASS='/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C'
UPDATE='UEPSpawningTimelineUpdate'
WATCH='UEPSpawningBeginTeamWatch'
PARTS='UEPSpawningWaitForParts'
STOP='UEPSpawningUnbindParts'
METHODS=('OnApplication','OnRemoval','OnTeamColorChanged','SpawnEffectForEachMeshComponent','UpdateActorColors','StopWatchingForParts','OnCharacterPartsChanged',UPDATE)


def evidence(actor):
    if not hasattr(actor,'_uep_spawning_cue'):
        actor._uep_spawning_cue={p+'_'+n:0 for p in ('python','fallback') for n in ('application','removal','team','spawn','colors','stop','parts','update')}
        actor._uep_spawning_cue.update(spawns=0,existing_meshes=0,ignored_meshes=0,diagnostic_fallbacks=0,last_time=None)
    return actor._uep_spawning_cue


def mark(actor,name):evidence(actor)['python_'+name]+=1


def mesh_target(actor):
    # A removed target can leave an invalid cached wrapper until Cue recycle.
    # Native mesh helpers accept null and then do no work; retain the source
    # TargetActor field while allowing effects/listener cleanup to continue.
    target=actor.get_property('TargetActor')
    return target if valid(target) else None


def application(actor,target,parameters,results):
    mark(actor,'application');templates=list(actor.get_property('NiagaraSystemTemplates'))
    if not templates:
        evidence(actor)['diagnostic_fallbacks']+=1;return actor.call_mixin_original('OnApplication',target,parameters,results)
    actor.set_property('TargetActor',target);actor.set_property('Spawn Linear Time',0.)
    actor.set_property('TemplateToUse',templates[int(lib('KismetMathLibrary').call_function('RandomInteger',len(templates)))])
    actor.call_function(WATCH)
    # Two original Sequence outputs enter the same latent action and delegate.
    actor.call_function(PARTS);actor.call_function(PARTS)
    actor.call_function('SpawnEffectForEachMeshComponent');actor.call_function('UpdateActorColors')
    rate=lib('KismetMathLibrary').call_function('Divide_DoubleDouble',1.,actor.get_property('SpawningDuration'))
    timeline=actor.get_property('SpawnTimeline');timeline.call_function('SetPlayRate',rate);timeline.call_function('PlayFromStart')


def spawn(actor):
    mark(actor,'spawn');template=actor.get_property('TemplateToUse')
    if not valid(template):
        evidence(actor)['diagnostic_fallbacks']+=1;return actor.call_mixin_original('SpawnEffectForEachMeshComponent')
    mapping=dict(actor.get_property('SpawnedEffectMap'));effects=list(actor.get_property('SpawnedEffects'))
    for mesh in components(mesh_target(actor),'SkeletalMeshComponent',True):
        if ignore_tag(mesh):evidence(actor)['ignored_meshes']+=1;continue
        if mesh in mapping:evidence(actor)['existing_meshes']+=1;continue
        effect=lib('NiagaraFunctionLibrary').call_function('SpawnSystemAttached',SystemTemplate=template,AttachToComponent=mesh,AttachPointName='None',Location=ue.FVector(),Rotation=ue.FRotator(),LocationType=EAttachLocation.KeepRelativeOffset,bAutoDestroy=False,bAutoActivate=True,PoolingMethod=getattr(ENCPoolMethod,'None'),bPreCullCheck=True)
        effects.append(effect);actor.set_property('SpawnedEffects',effects);mapping[mesh]=effect;actor.set_property('SpawnedEffectMap',mapping);evidence(actor)['spawns']+=1
        effect.call_function('SetVariableFloat','SpawnTImeLength',actor.get_property('SpawningDuration'))
        effect.call_function('SetVariableVec3','BodyColor',lib('KismetMathLibrary').call_function('Conv_LinearColorToVector',actor.get_property('TeamColor')))


def team(actor,asset):
    mark(actor,'team');color=lib('LyraTeamStatics').call_function('GetTeamColorWithFallback',asset,'TeamColor',ue.FLinearColor(1.,0.,.721921,1.));actor.set_property('TeamColor',color)
    for effect in actor.get_property('SpawnedEffects'):
        if valid(effect):effect.call_function('SetVariableVec3','BodyColor',lib('KismetMathLibrary').call_function('Conv_LinearColorToVector',color))


def colors(actor):
    mark(actor,'colors');target=mesh_target(actor)
    lib('LyraSystemStatics').call_function('SetColorParameterValueOnAllMeshComponents',target,'KillEdgeColor',actor.get_property('TeamColor'),True)
    lib('LyraSystemStatics').call_function('SetScalarParameterValueOnAllMeshComponents',target,'SpawnAge',actor.get_property('Spawn Linear Time'),True)


def update(actor,value):
    mark(actor,'update');evidence(actor)['last_time']=float(value);actor.set_property('Spawn Linear Time',value)
    lib('LyraSystemStatics').call_function('SetScalarParameterValueOnAllMeshComponents',mesh_target(actor),'SpawnAge',value,True)
    for effect in actor.get_property('SpawnedEffects'):
        if valid(effect):effect.call_function('SetVariableFloat','SpawnTimeline',value)
    return False


def removal(actor):
    mark(actor,'removal');lib('LyraSystemStatics').call_function('SetScalarParameterValueOnAllMeshComponents',mesh_target(actor),'SpawnAge',1.,True)
    for effect in actor.get_property('SpawnedEffects'):
        if valid(effect):effect.call_function('Deactivate')
    actor.set_property('SpawnedEffects',[]);actor.set_property('SpawnedEffectMap',{})
    watcher=actor.get_property('TeamColorWatcherHandle')
    if valid(watcher):watcher.call_function('Cancel')
    actor.call_function('StopWatchingForParts')


class LyraSpawningCuePythonProfile:
    def OnApplication(self,Target,Parameters,SpawnResults):return application(self,Target,Parameters,SpawnResults)
    def OnRemoval(self,Target,Parameters,SpawnResults):removal(self)
    def OnTeamColorChanged(self,TeamDisplayAsset):team(self,TeamDisplayAsset)
    def SpawnEffectForEachMeshComponent(self):return spawn(self)
    def UpdateActorColors(self):colors(self)
    def StopWatchingForParts(self):mark(self,'stop');self.call_function(STOP)
    def OnCharacterPartsChanged(self,ComponentWithChangedParts):mark(self,'parts');self.call_function('SpawnEffectForEachMeshComponent');self.call_function('UpdateActorColors')
    def TimelineUpdate(self,Time):return update(self,Time)
    TimelineUpdate.override=UPDATE


class LyraSpawningCueBlueprintFallbackProfile:
    def OnApplication(self,Target,Parameters,SpawnResults):evidence(self)['fallback_application']+=1;return self.call_mixin_original('OnApplication',Target,Parameters,SpawnResults)
    def OnRemoval(self,Target,Parameters,SpawnResults):evidence(self)['fallback_removal']+=1;return self.call_mixin_original('OnRemoval',Target,Parameters,SpawnResults)
    def OnTeamColorChanged(self,TeamDisplayAsset):evidence(self)['fallback_team']+=1;return self.call_mixin_original('OnTeamColorChanged',TeamDisplayAsset)
    def SpawnEffectForEachMeshComponent(self):evidence(self)['fallback_spawn']+=1;return self.call_mixin_original('SpawnEffectForEachMeshComponent')
    def UpdateActorColors(self):evidence(self)['fallback_colors']+=1;return self.call_mixin_original('UpdateActorColors')
    def StopWatchingForParts(self):evidence(self)['fallback_stop']+=1;return self.call_mixin_original('StopWatchingForParts')
    def OnCharacterPartsChanged(self,ComponentWithChangedParts):evidence(self)['fallback_parts']+=1;return self.call_mixin_original('OnCharacterPartsChanged',ComponentWithChangedParts)
    def TimelineUpdate(self,Time):evidence(self)['fallback_update']+=1;evidence(self)['last_time']=float(Time);return True
    TimelineUpdate.override=UPDATE
