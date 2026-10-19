"""Character damage Cue policy; native effects/RNG data/RPC transport stay native."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from unreal_engine.enums import EAttachLocation
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import break_hit,native_outputs

CLASS='/Game/GameplayCueNotifies/GCNL_Character_DamageTaken.GCNL_Character_DamageTaken_C'
EXECUTE='UEPCharacterDamageAfterNativeExecute'
RPC='UEPCharacterDamageMontageBody'
LONG,SIDE='UEPDamageFrontBackMontage','UEPDamageSideMontage'
BROADCAST='BroadcastDamageVerb'
LENS_COUNT,LENS_OBJECT='UEPDamageLensCount','UEPDamageLensObject'
LENS='/Game/Effects/Camera/Damage/NCLE_DamageTaken.NCLE_DamageTaken_C'
DECAL='/Game/Effects/Materials/Decals/M_Honetcomb_BulletHit_Decal.M_Honetcomb_BulletHit_Decal'
SELECT='Select Hit Montage'
ANIMATE='Damage Animation'


def lib(name):return ue.find_class(name).get_cdo()


def evidence(actor):
    if not hasattr(actor,'_uep_character_damage'):
        actor._uep_character_damage=dict(python_burst=0,fallback_burst=0,python_execute=0,fallback_execute=0,
            python_broadcast=0,fallback_broadcast=0,python_weak=0,fallback_weak=0,python_select=0,fallback_select=0,
            python_animation=0,fallback_animation=0,python_rpc_body=0,fallback_rpc_body=0,messages=0,
            number_pops=0,sounds=0,decals=0,lens_updates=0,montages=0,diagnostic_fallbacks=0,last_selection=None)
    return actor._uep_character_damage


def output(actor,name,*args):
    value=actor.call_mixin_original(name,*args)
    if not isinstance(value,tuple) or len(value)!=1:raise RuntimeError('single named damage output required: '+name)
    return value[0]


def weak(actor,obj):
    evidence(actor)['python_weak']+=1
    result=bool(obj is not None and obj.is_a(ue.find_class('PhysicalMaterialWithTags')) and lib('BlueprintGameplayTagLibrary').call_function('HasTag',obj.get_property('Tags'),GameplayTag(TagName='Gameplay.Zone.WeakSpot'),True))
    return {'DidHitWeakSpot':result}


def select(actor,normal,target):
    counts=evidence(actor);counts['python_select']+=1
    if target is None:
        counts['diagnostic_fallbacks']+=1;return {'Hit Montage':output(actor,SELECT,normal,target)}
    math=lib('KismetMathLibrary')
    forward=float(math.call_function('Dot_VectorVector',target.call_function('GetActorForwardVector'),normal))
    right=float(math.call_function('Dot_VectorVector',target.call_function('GetActorRightVector'),normal))
    # The source tests a narrowed float right dot, but strict sign tests remain doubles.
    straight=bool(math.call_function('InRange_FloatFloat',right,-.5,.5,True,True))
    choice=(forward>0.) if straight else (right>0.)
    value=actor.call_function(LONG if straight else SIDE,choice)
    counts['last_selection']=dict(forward=forward,right=right,straight=straight,positive=choice)
    return {'Hit Montage':value}


def broadcast(actor,target,params):
    counts=evidence(actor);counts['python_broadcast']+=1
    if not valid(target):
        counts['diagnostic_fallbacks']+=1;return actor.call_mixin_original('BroadcastDamageTaken',target,params)
    message=lib('LyraVerbMessageHelpers').call_function('CueParametersToVerbMessage',params);message.Target=target
    router=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',target,ue.find_class('GameplayMessageSubsystem'))
    actor.call_function(BROADCAST,router,GameplayTag(TagName='Lyra.Damage.Taken.Message'),message);counts['messages']+=1


def capture_hit(actor,params):
    # The original event's persistent ubergraph frame retains its last Parameters.
    # Keep equivalent per-actor context for the argument-less Damage Animation event.
    actor._uep_character_damage_hit=lib('AbilitySystemBlueprintLibrary').call_function('GetHitResult',params)
    return actor._uep_character_damage_hit


def animation(actor):
    counts=evidence(actor);counts['python_animation']+=1;target=actor.get_property('Target')
    asc=lib('AbilitySystemBlueprintLibrary').call_function('GetAbilitySystemComponent',target)
    if not valid(asc):return
    hit=break_hit(getattr(actor,'_uep_character_damage_hit',ue.find_struct('HitResult')()))
    chosen,=actor.call_function(SELECT,hit['Normal'],target);actor.set_property('Montage',chosen)
    if valid(target) and target.is_a(ue.find_class('Character')):actor.call_function('MontageHit',target,chosen)


def play_montage(actor,character,montage):
    counts=evidence(actor);counts['python_rpc_body']+=1
    if not valid(character):counts['diagnostic_fallbacks']+=1;return True
    character.call_function('PlayAnimMontage',montage,1.,'None');counts['montages']+=1;return False


def burst(actor,target,params,spawns):
    counts=evidence(actor);counts['python_burst']+=1;raw=capture_hit(actor,params)
    if not valid(target):counts['diagnostic_fallbacks']+=1;return actor.call_mixin_original('OnBurst',target,params,spawns)
    actor.call_function('BroadcastDamageTaken',target,params);actor.set_property('Target',target)
    if not target.is_a(ue.find_class('Character')):return
    actor.call_function(ANIMATE);hit=break_hit(raw);math=lib('KismetMathLibrary')
    if valid(hit['PhysMat']) and int(hit['PhysMat'].get_property('SurfaceType'))!=0:
        rotation=math.call_function('Conv_VectorToRotator',math.call_function('Multiply_VectorVector',hit['ImpactNormal'],ue.FVector(-1.,-1.,-1.)))
        mesh=target.get_property('Mesh')
        transformed=native_outputs('SkinnedMeshComponent','TransformToBoneSpace',mesh.call_function('TransformToBoneSpace',hit['HitBoneName'],hit['Location'],rotation))
        decal=lib('GameplayStatics').call_function('SpawnDecalAttached',DecalMaterial=ue.load_object(ue.find_class('MaterialInterface'),DECAL),DecalSize=ue.FVector(5.,8.,8.),AttachToComponent=mesh,AttachPointName=hit['HitBoneName'],
            Location=transformed['OutPosition'],Rotation=transformed['OutRotation'],LocationType=EAttachLocation.KeepRelativeOffset,LifeSpan=10.)
        if valid(decal):decal.call_function('SetFadeOut',5.,5.,False)
        counts['decals']+=1
    direction=math.call_function('Normal',math.call_function('Subtract_VectorVector',hit['TraceStart'],hit['TraceEnd']),.0001)
    lens_cls=ue.load_class(LENS)
    for index in range(actor.call_function(LENS_COUNT,spawns)):
        lens=actor.call_function(LENS_OBJECT,spawns,index)
        if lens is not None and lens.is_a(lens_cls):
            component=lens.get_property('NiagaraComponent')
            if valid(component):
                component.call_function('SetVariableVec3','HitDirection',direction);component.call_function('SetVariablePosition','AttackWorldPosition',hit['TraceStart']);counts['lens_updates']+=1


def sound(actor,kind,critical=False):
    name='sfx_Character_'+kind+('WeakSpot' if critical else '')+'_nl_meta';path='/Game/Audio/MetaSounds/'+name+'.'+name
    lib('GameplayStatics').call_function('PlaySound2D',WorldContextObject=actor,Sound=ue.load_object(ue.find_class('SoundBase'),path),VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,ConcurrencySettings=None,OwningActor=None,bIsUISound=True)
    evidence(actor)['sounds']+=1


def execute_body(actor,target,params):
    counts=evidence(actor);counts['python_execute']+=1;ability=lib('AbilitySystemBlueprintLibrary')
    instigator=ability.call_function('EffectContextGetInstigatorActor',params.EffectContext)
    if instigator is None or not instigator.is_a(ue.find_class('PlayerState')):return False
    pawn=instigator.call_function('GetPawn')
    if not valid(pawn):counts['diagnostic_fallbacks']+=1;return True
    hit=break_hit(ability.call_function('EffectContextGetHitResult',params.EffectContext))
    if pawn.call_function('IsLocallyControlled'):
        controller=pawn.call_function('GetController')
        if not valid(controller):counts['diagnostic_fallbacks']+=1;return True
        pops=controller.get_component_by_type(ue.find_class('LyraNumberPopComponent'))
        if not valid(pops):return False
        critical,=actor.call_function('EvaluateWeakSpot',hit['PhysMat'])
        request=ue.find_struct('LyraNumberPopRequest')(WorldLocation=hit['Location'],SourceTags=params.AggregatedSourceTags,TargetTags=params.AggregatedTargetTags,
            NumberToDisplay=lib('KismetMathLibrary').call_function('Round',params.RawMagnitude),bIsCriticalDamage=critical)
        pops.call_function('AddNumberPop',request);counts['number_pops']+=1
        victim=hit['HitActor']
        if not valid(victim):return False
        sound(actor,'DamageGiven',critical);health=victim.get_component_by_type(ue.find_class('LyraHealthComponent'))
        if valid(health) and float(health.call_function('GetHealthNormalized'))<=0.:sound(actor,'DamageGivenKill')
    elif valid(target):
        controller=lib('LyraVerbMessageHelpers').call_function('GetPlayerControllerFromObject',target)
        if valid(controller):
            viewed=controller.call_function('K2_GetPawn')
            if not valid(viewed):counts['diagnostic_fallbacks']+=1;return True
            if viewed.call_function('IsLocallyViewed'):
                critical,=actor.call_function('EvaluateWeakSpot',hit['PhysMat']);sound(actor,'DamageTaken',critical)
    return False


class LyraCharacterDamagePythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):burst(self,Target,Parameters,SpawnResults)
    def ExecuteBody(self,MyTarget,Parameters):return execute_body(self,MyTarget,Parameters)
    ExecuteBody.override=EXECUTE
    def BroadcastDamageTaken(self,TargetActor,Params):return broadcast(self,TargetActor,Params)
    def EvaluateWeakSpot(self,Object):return weak(self,Object)
    EvaluateWeakSpot.uep_named_outputs=True
    def SelectMontage(self,HitNormal,HitActor):return select(self,HitNormal,HitActor)
    SelectMontage.override=SELECT;SelectMontage.uep_named_outputs=True
    def DamageAnimation(self):animation(self)
    DamageAnimation.override=ANIMATE
    def MontageBody(self,Character,Montage):return play_montage(self,Character,Montage)
    MontageBody.override=RPC


class LyraCharacterDamageBlueprintFallbackProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):
        evidence(self)['fallback_burst']+=1;capture_hit(self,Parameters);return self.call_mixin_original('OnBurst',Target,Parameters,SpawnResults)
    def ExecuteBody(self,MyTarget,Parameters):evidence(self)['fallback_execute']+=1;return True
    ExecuteBody.override=EXECUTE
    def BroadcastDamageTaken(self,TargetActor,Params):evidence(self)['fallback_broadcast']+=1;return self.call_mixin_original('BroadcastDamageTaken',TargetActor,Params)
    def EvaluateWeakSpot(self,Object):evidence(self)['fallback_weak']+=1;return {'DidHitWeakSpot':output(self,'EvaluateWeakSpot',Object)}
    EvaluateWeakSpot.uep_named_outputs=True
    def SelectMontage(self,HitNormal,HitActor):evidence(self)['fallback_select']+=1;return {'Hit Montage':output(self,SELECT,HitNormal,HitActor)}
    SelectMontage.override=SELECT;SelectMontage.uep_named_outputs=True
    def DamageAnimation(self):evidence(self)['fallback_animation']+=1;return self.call_mixin_original(ANIMATE)
    DamageAnimation.override=ANIMATE
    def MontageBody(self,Character,Montage):evidence(self)['fallback_rpc_body']+=1;return True
    MontageBody.override=RPC
