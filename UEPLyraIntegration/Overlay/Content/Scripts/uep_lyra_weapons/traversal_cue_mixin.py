"""Launcher/teleporter Cue policy; original Timeline and native component APIs."""
import unreal_engine as ue
from unreal_engine.enums import EAttachLocation,ENCPoolMethod
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .hero_burst_cue_mixin import lib,components,team

CLASSES={k:'/ShooterCore/GameplayCues/'+v+'.'+v+'_C' for k,v in (('launcher','GCNL_Launcher_Activate'),('teleporter','GCNL_Teleporter_Activate'))}
LAUNCHER='/ShooterCore/Blueprint/B_Launcher.B_Launcher_C'
TELEPORTER='/ShooterCore/Blueprint/B_Teleport.B_Teleport_C'
UPDATE='UEPLauncherCueTimelineUpdate'
TIMELINE='LauncherMaterialEffect_Timeline'
JUMP='/Game/Effects/Particles/Environmental/NS_JumpPad.NS_JumpPad'
ENTER='/Game/Effects/Particles/Environmental/NS_WallPortalEnter.NS_WallPortalEnter'
EXIT='/Game/Effects/Particles/Environmental/NS_CharacterPortalDissolve.NS_CharacterPortalDissolve'


def evidence(actor):
    if not hasattr(actor,'_uep_traversal_cue'):
        actor._uep_traversal_cue=dict(python_burst=0,fallback_burst=0,python_updates=0,fallback_updates=0,python_clear=0,fallback_clear=0,
            spawns=0,ignored=0,entry_increments=0,exit_increments=0,diagnostic_fallbacks=0,last_time=None,last_material_value=None)
    return actor._uep_traversal_cue


def cue_fields(params):return native_outputs('AbilitySystemBlueprintLibrary','BreakGameplayCueParameters',lib('AbilitySystemBlueprintLibrary').call_function('BreakGameplayCueParameters',params))


def spawn_attached(mesh,system,auto,activate,pre_cull):
    return lib('NiagaraFunctionLibrary').call_function('SpawnSystemAttached',SystemTemplate=ue.load_object(ue.find_class('NiagaraSystem'),system),AttachToComponent=mesh,AttachPointName='None',Location=ue.FVector(),Rotation=ue.FRotator(),LocationType=EAttachLocation.KeepRelativeOffset,bAutoDestroy=auto,bAutoActivate=activate,PoolingMethod=getattr(ENCPoolMethod,'None'),bPreCullCheck=pre_cull)


def append(actor,field,value):
    values=list(actor.get_property(field));values.append(value);actor.set_property(field,values)


def launcher(actor,target,params):
    counts=evidence(actor);counts['python_burst']+=1
    if not valid(target):return
    actor.set_property('TargetActor',target);pad=cue_fields(params)['EffectCauser']
    if pad is None or not pad.is_a(ue.load_class(LAUNCHER)):return
    actor.set_property('LaunchPadActor',pad);movement=target.get_component_by_type(ue.find_class('MovementComponent'))
    if not valid(movement):counts['diagnostic_fallbacks']+=1;return actor.call_mixin_original('OnBurst',target,params,actor.get_property('BurstSpawnResults'))
    velocity=movement.get_property('Velocity');actor.set_property('TargetActorVelocity',velocity);color=team(actor,target)
    duration=float(actor.get_property('MaterialEffectDuration'));pad_color=pad.get_property('Light Color');math=lib('KismetMathLibrary')
    scale=pad.get_property('DefaultSceneRoot').call_function('K2_GetComponentScale')
    average=math.call_function('Divide_DoubleDouble',math.call_function('Add_DoubleDouble',math.call_function('Add_DoubleDouble',float(scale.x),float(scale.y)),float(scale.z)),3.)
    for mesh in components(target,'SkeletalMeshComponent',True):
        if mesh.call_function('ComponentHasTag','ignore'):counts['ignored']+=1;continue
        effect=spawn_attached(mesh,JUMP,False,False,True);append(actor,'SpawnedEffects',effect);counts['spawns']+=1
        if valid(effect):
            effect.call_function('SetVariablePosition','LaunchPadWorldPosition',pad.get_actor_location());effect.call_function('SetVariableLinearColor','LaunchPadColor',pad_color)
            effect.call_function('SetVariableFloat','LaunchPadScale',average);effect.call_function('SetVariableVec3','PawnVelocity',velocity)
            effect.call_function('SetVariableFloat','Duration',duration);effect.call_function('SetVariableLinearColor','TeamColor',color);effect.call_function('Activate',False)
    lib('LyraSystemStatics').call_function('SetColorParameterValueOnAllMeshComponents',target,'EdgeGlowColor',pad_color,True)
    timeline=actor.get_property(TIMELINE);timeline.call_function('SetPlayRate',math.call_function('Divide_DoubleDouble',1.,duration));timeline.call_function('PlayFromStart')


def clear(actor):
    evidence(actor)['python_clear']+=1
    for effect in actor.get_property('SpawnedEffects'):
        if valid(effect):effect.call_function('Deactivate')
    actor.set_property('SpawnedEffects',[]);target=actor.get_property('TargetActor')
    if valid(target):lib('LyraSystemStatics').call_function('SetScalarParameterValueOnAllMeshComponents',target,'EdgeGlowMagnitude',0.,True)


def update(actor,value):
    counts=evidence(actor);counts['python_updates']+=1;counts['last_time']=float(value);target=actor.get_property('TargetActor')
    if not valid(target):actor.call_function('Clear Trails');actor.get_property(TIMELINE).call_function('Stop');return False
    curve=actor.get_property('MaterialEffectCurve');effects=list(actor.get_property('SpawnedEffects'))
    if not valid(curve) or any(not valid(e) for e in effects):counts['diagnostic_fallbacks']+=1;return True
    evaluated=curve.call_function('GetFloatValue',value);counts['last_material_value']=float(evaluated)
    lib('LyraSystemStatics').call_function('SetScalarParameterValueOnAllMeshComponents',target,'EdgeGlowMagnitude',evaluated,True)
    for effect in effects:effect.call_function('SetVariableFloat','LaunchPadGCNLValue',value)
    return False


def center(teleporter):
    math=lib('KismetMathLibrary');z=math.call_function('Add_DoubleDouble',math.call_function('Divide_DoubleDouble',float(teleporter.get_property('TeleporterHeight')),2.),float(teleporter.get_property('TeleporterPhase')))
    return math.call_function('MakeVector',0.,0.,z)


def increment(actor,teleporter,enter):
    math=lib('KismetMathLibrary');count=math.call_function('Percent_IntInt',math.call_function('Add_IntInt',int(teleporter.get_property('TeleporterEntered')),1),1000000)
    teleporter.set_property('TeleporterEntered',count);effect=teleporter.get_property('Niagara')
    effect.call_function('SetVariableInt','SystemEntered',count);effect.call_function('SetVariableFloat','UseDirection',math.call_function('SelectFloat',1.,-.8,enter))
    evidence(actor)['entry_increments' if enter else 'exit_increments']+=1


def teleport(actor,target,params):
    counts=evidence(actor);counts['python_burst']+=1;actor.set_property('TargetActor',target);entry=cue_fields(params)['EffectCauser']
    if entry is None or not entry.is_a(ue.load_class(TELEPORTER)):return
    actor.set_property('As B Teleport',entry);math=lib('KismetMathLibrary');niagara=lib('NiagaraFunctionLibrary');source_component=entry.get_property('Niagara');source_position=source_component.call_function('K2_GetComponentLocation')
    for mesh in components(target,'SkeletalMeshComponent',True):
        if mesh.call_function('ComponentHasTag','ignore'):counts['ignored']+=1;continue
        flash=niagara.call_function('SpawnSystemAtLocation',WorldContextObject=actor,SystemTemplate=ue.load_object(ue.find_class('NiagaraSystem'),ENTER),Location=source_position,Rotation=ue.FRotator(),Scale=ue.FVector(1.,1.,1.),bAutoDestroy=True,bAutoActivate=True,PoolingMethod=getattr(ENCPoolMethod,'None'),bPreCullCheck=True)
        if valid(flash):
            niagara.call_function('OverrideSystemUserVariableSkeletalMeshComponent',flash,'SkeletalMesh',mesh)
            offset=math.call_function('Multiply_VectorVector',math.call_function('Subtract_VectorVector',mesh.call_function('K2_GetComponentLocation'),source_position),ue.FVector(0.,0.,1.))
            flash.call_function('SetVariableVec3','SkeletonPositionOffset',offset);flash.call_function('SetVariableVec3','TeleporterPosition',center(entry))
            flash.call_function('SetVariableVec3','TeleporterPlaneDirection',entry.call_function('GetActorForwardVector'))
            flash.call_function('SetVariableFloat','PortalWidth',entry.get_property('TeleporterWidth'));flash.call_function('SetVariableFloat','PortalHeight',entry.get_property('TeleporterHeight'))
        effect=spawn_attached(mesh,EXIT,True,True,False);append(actor,'ExitParticles',effect);counts['spawns']+=2
    increment(actor,entry,True);destination=entry.get_property('TeleporterDestination')
    if valid(destination):
        position=math.call_function('Add_VectorVector',destination.get_actor_location(),center(destination))
        for effect in actor.get_property('ExitParticles'):
            if valid(effect):effect.call_function('SetVariableVec3','TeleporterPosition',position)
        increment(actor,destination,False)


class LyraLauncherCuePythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):launcher(self,Target,Parameters)
    def TimelineUpdate(self,Time):return update(self,Time)
    TimelineUpdate.override=UPDATE
    def ClearTrails(self):clear(self)
    ClearTrails.override='Clear Trails'


class LyraLauncherCueBlueprintFallbackProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):evidence(self)['fallback_burst']+=1;return self.call_mixin_original('OnBurst',Target,Parameters,SpawnResults)
    def TimelineUpdate(self,Time):evidence(self)['fallback_updates']+=1;evidence(self)['last_time']=float(Time);return True
    TimelineUpdate.override=UPDATE
    def ClearTrails(self):evidence(self)['fallback_clear']+=1;return self.call_mixin_original('Clear Trails')
    ClearTrails.override='Clear Trails'


class LyraTeleporterCuePythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):teleport(self,Target,Parameters)


class LyraTeleporterCueBlueprintFallbackProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):evidence(self)['fallback_burst']+=1;return self.call_mixin_original('OnBurst',Target,Parameters,SpawnResults)
