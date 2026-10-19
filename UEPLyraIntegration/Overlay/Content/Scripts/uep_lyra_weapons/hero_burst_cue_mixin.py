"""Dash/death business with original native Timeline clocks/curves and parent FX."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from unreal_engine.enums import EAttachLocation,ENCPoolMethod
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs

CLASSES={name:'/ShooterCore/GameplayCues/'+asset+'.'+asset+'_C' for name,asset in (('dash','GCNL_Dash'),('death','GCNL_Death'))}
UPDATE,FINISH='UEPHeroBurstTimelineUpdate','UEPHeroBurstTimelineFinished'
TIMELINES={'dash':'DashDeformTimeline','death':'DeathCubesTimeline'}
DASH='/Game/Effects/Particles/Environmental/NS_CharacterDash.NS_CharacterDash'
DEATH='/Game/Effects/Particles/Impacts/NS_DeathCubes.NS_DeathCubes'
ELECTRIC='/Game/Effects/Particles/Environmental/NS_ElectricMovement.NS_ElectricMovement'


def lib(name):return ue.find_class(name).get_cdo()


def evidence(actor):
    if not hasattr(actor,'_uep_hero_burst'):
        actor._uep_hero_burst=dict(python_burst=0,fallback_burst=0,python_updates=0,fallback_updates=0,
            python_finished=0,fallback_finished=0,spawns=0,ignored_meshes=0,electric=0,deleted_decals=0,timeline_starts=0,diagnostic_fallbacks=0,last_curves=None)
    return actor._uep_hero_burst


def team(actor,target):
    result=native_outputs('LyraTeamStatics','FindTeamFromObject',lib('LyraTeamStatics').call_function('FindTeamFromObject',target,False))
    asset=result['DisplayAsset'];actor.set_property('TeamDisplayAsset',asset)
    color=lib('LyraTeamStatics').call_function('GetTeamColorWithFallback',asset,'TeamColor',ue.FLinearColor(1.,0.,.721921,1.));actor.set_property('TeamColor',color);return color


def components(target,cls,children):return lib('LyraSystemStatics').call_function('FindComponentsByClass',target,ue.find_class(cls),children)


def append(actor,component):
    values=list(actor.get_property('SpawnedEffects'));values.append(component);actor.set_property('SpawnedEffects',values)


def attached(actor,mesh,system,activate):
    return lib('NiagaraFunctionLibrary').call_function('SpawnSystemAttached',SystemTemplate=ue.load_object(ue.find_class('NiagaraSystem'),system),AttachToComponent=mesh,AttachPointName='None',
        Location=ue.FVector(),Rotation=ue.FRotator(),LocationType=EAttachLocation.KeepRelativeOffset,bAutoDestroy=False,bAutoActivate=activate,PoolingMethod=getattr(ENCPoolMethod,'None'),bPreCullCheck=True)


def start_timeline(actor,kind,duration):
    rate=lib('KismetMathLibrary').call_function('Divide_DoubleDouble',1.,duration)
    timeline=actor.get_property(TIMELINES[kind]);timeline.call_function('SetPlayRate',rate);timeline.call_function('PlayFromStart');evidence(actor)['timeline_starts']+=1


def dash(actor,target,params):
    counts=evidence(actor);counts['python_burst']+=1
    fields=native_outputs('AbilitySystemBlueprintLibrary','BreakGameplayCueParameters',lib('AbilitySystemBlueprintLibrary').call_function('BreakGameplayCueParameters',params))
    actor.set_property('TargetActor',target);actor.set_property('Duration',fields['NormalizedMagnitude']);actor.set_property('Strenght',fields['RawMagnitude']);actor.set_property('Direction',fields['Normal'])
    color=team(actor,target);duration=float(actor.get_property('Duration'));direction=actor.get_property('Direction')
    for mesh in components(target,'SkeletalMeshComponent',True):
        if mesh.call_function('ComponentHasTag','ignore'):counts['ignored_meshes']+=1;continue
        effect=attached(actor,mesh,DASH,True);append(actor,effect);counts['spawns']+=1
        if valid(effect):
            lib('NiagaraFunctionLibrary').call_function('OverrideSystemUserVariableSkeletalMeshComponent',effect,'SkeletalMesh',mesh)
            effect.call_function('SetVariableFloat','DashDuration',lib('KismetMathLibrary').call_function('Multiply_DoubleDouble',duration,2.))
            effect.call_function('SetVariableVec3','DashDirection',direction);effect.call_function('SetVariableLinearColor','TeamColor',color)
    lib('LyraSystemStatics').call_function('SetVectorParameterValueOnAllMeshComponents',target,'DashDirection',direction,True)
    start_timeline(actor,'dash',duration)


def death(actor,target,params):
    counts=evidence(actor);counts['python_burst']+=1;actor.set_property('TargetActor',target)
    kill=bool(lib('BlueprintGameplayTagLibrary').call_function('HasTag',params.AggregatedSourceTags,GameplayTag(TagName='Gameplay.Damage.FellOutOfWorld'),False));actor.set_property('KillPlaneDeath',kill)
    color=team(actor,target);duration=float(actor.get_property('SpawningDuration'))
    if kill:
        root=target.get_property('RootComponent') if target is not None else None
        if valid(root):
            effect=lib('NiagaraFunctionLibrary').call_function('SpawnSystemAtLocation',WorldContextObject=actor,SystemTemplate=ue.load_object(ue.find_class('NiagaraSystem'),ELECTRIC),Location=root.call_function('K2_GetComponentLocation'),Rotation=ue.FRotator(),Scale=ue.FVector(1.,1.,1.),bAutoDestroy=True,bAutoActivate=True,PoolingMethod=getattr(ENCPoolMethod,'None'),bPreCullCheck=False)
            if valid(effect):effect.call_function('SetColorParameter','BodyColor',color)
            counts['electric']+=1
    for mesh in components(target,'SkeletalMeshComponent',True):
        if mesh.call_function('ComponentHasTag','ignore'):counts['ignored_meshes']+=1;continue
        effect=attached(actor,mesh,DEATH,False);append(actor,effect);counts['spawns']+=1
        if valid(effect):
            effect.call_function('SetVariableFloat','KillTimeLength',duration)
            effect.call_function('SetVariableVec3','BodyColor',lib('KismetMathLibrary').call_function('Conv_LinearColorToVector',color));effect.call_function('Activate',True)
    for decal in components(target,'DecalComponent',False):decal.call_function('K2_DestroyComponent',target);counts['deleted_decals']+=1
    for name in ('KillEdgeColor','EdgeGlowColor'):lib('LyraSystemStatics').call_function('SetColorParameterValueOnAllMeshComponents',target,name,color,True)
    start_timeline(actor,'death',duration)


def update(actor,kind,a,b):
    counts=evidence(actor);counts['python_updates']+=1;counts['last_curves']=[float(a),float(b)]
    target=actor.get_property('TargetActor');values=list(actor.get_property('SpawnedEffects'))
    if kind=='dash' and any(not valid(v) for v in values):counts['diagnostic_fallbacks']+=1;return True
    lib('LyraSystemStatics').call_function('SetScalarParameterValueOnAllMeshComponents',target,'DashDeform' if kind=='dash' else 'KillAge',a,True)
    if kind=='death':lib('LyraSystemStatics').call_function('SetScalarParameterValueOnAllMeshComponents',target,'EdgeGlowMagnitude',lib('KismetMathLibrary').call_function('Multiply_DoubleDouble',b,20.),True)
    for effect in values:
        if kind=='dash':effect.call_function('SetVariableFloat','LifetimeMultiplier',b)
        elif valid(effect):effect.call_function('SetFloatParameter','KillTimeline',a)
    return False


def finish(actor,kind):
    counts=evidence(actor);counts['python_finished']+=1;values=list(actor.get_property('SpawnedEffects'))
    if kind=='dash' and any(not valid(v) for v in values):counts['diagnostic_fallbacks']+=1;return True
    if kind=='death':lib('LyraSystemStatics').call_function('SetScalarParameterValueOnAllMeshComponents',actor.get_property('TargetActor'),'EdgeGlowMagnitude',0.,True)
    for effect in values:
        if kind=='dash' or valid(effect):effect.call_function('Deactivate')
    actor.set_property('SpawnedEffects',[]);return False


class LyraDashCuePythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):dash(self,Target,Parameters)
    def TimelineUpdate(self,ValueA,ValueB):return update(self,'dash',ValueA,ValueB)
    TimelineUpdate.override=UPDATE
    def TimelineFinished(self):return finish(self,'dash')
    TimelineFinished.override=FINISH


class LyraDeathCuePythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):death(self,Target,Parameters)
    def TimelineUpdate(self,ValueA,ValueB):return update(self,'death',ValueA,ValueB)
    TimelineUpdate.override=UPDATE
    def TimelineFinished(self):return finish(self,'death')
    TimelineFinished.override=FINISH


class LyraHeroBurstBlueprintFallbackProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):evidence(self)['fallback_burst']+=1;return self.call_mixin_original('OnBurst',Target,Parameters,SpawnResults)
    def TimelineUpdate(self,ValueA,ValueB):evidence(self)['fallback_updates']+=1;evidence(self)['last_curves']=[float(ValueA),float(ValueB)];return True
    TimelineUpdate.override=UPDATE
    def TimelineFinished(self):evidence(self)['fallback_finished']+=1;return True
    TimelineFinished.override=FINISH


LyraDashCueBlueprintFallbackProfile=LyraHeroBurstBlueprintFallbackProfile
LyraDeathCueBlueprintFallbackProfile=LyraHeroBurstBlueprintFallbackProfile
