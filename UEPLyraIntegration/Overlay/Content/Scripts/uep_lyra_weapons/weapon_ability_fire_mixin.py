"""Original shared weapon firing policy; targeting/GAS/tasks/timers stay native."""
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs,break_hit

CLASS="/Game/Weapons/GA_Weapon_Fire.GA_Weapon_Fire_C"
SELECT="Slelect Hit Montage"
COMPLETE="FireComplete"
FAILURE_COMPLETE="FailureMontage Delay Complete"
LISTEN="UEPWeaponFireBeginFailureListener"
FAILURE="UEPWeaponFireFailureMessage"
BIND="UEPWeaponFireBindMontageTask"
FAILURE_CHANNEL="Ability.PlayMontageOnActivateFail.Message"
NO_FIRING="Ability.Weapon.NoFiring"
DIRECT_METHODS=("K2_ActivateAbility","K2_OnAbilityAdded","OnRangedWeaponTargetDataReady",COMPLETE,FAILURE_COMPLETE,SELECT)
FIRE_CALLBACKS={name:name+"_16B35DCA428CE59995878BA3D5354270" for name in ("OnCompleted","OnInterrupted","OnCancelled")}
MONTAGES={key:tuple("/Game/Characters/Heroes/Mannequin/Animations/Actions/"+name+"."+name for name in names) for key,names in (
    ("front",("AM_MM_HitReact_Front_Lgt_01","AM_MM_HitReact_Front_Lgt_02","AM_MM_HitReact_Front_Med_01","AM_MM_HitReact_Front_Med_02")),
    ("back",("AM_MM_HitReact_Back_Med_01","AM_MM_HitReact_Front_Med_02")),
    ("right",("AM_MM_HitReact_Right_Med_01","AM_MM_HitReact_Front_Lgt_02")),
    ("left",("AM_MM_HitReact_Left_Med_01","AM_MM_HitReact_Front_Lgt_02")))}


def lib(name):return ue.find_class(name).get_cdo()


def evidence(ability):
    row=getattr(ability,"_uep_weapon_ability_fire",None)
    if row is None:
        row={key:0 for key in ("activations","fallback_activations","targeting_requests","fire_tasks","fire_timers","added","fallback_added",
            "target_data_calls","fallback_target_data_calls","firing_cues","impact_cues","field_spawns","damage_requests",
            "fire_complete","fallback_fire_complete","failure_messages","fallback_failure_messages","failure_tasks","failure_timers",
            "failure_complete","fallback_failure_complete","montage_choices","fallback_montage_choices","invalid_actor_native_fallback",
            "montage_completed","montage_interrupted","montage_cancelled","fallback_montage_callbacks")}
        ability._uep_weapon_ability_fire=row
    return row


def schedule(ability,name,duration):
    return lib("KismetSystemLibrary").call_function("K2_SetTimer",Object=ability,FunctionName=name,Time=duration,
        bLooping=False,bMaxOncePerFrame=False,InitialStartDelay=0.,InitialStartDelayVariance=0.)


def montage(ability,asset,rate,stop_on_end,bind_completion):
    task=lib("AbilityTask_PlayMontageAndWait").call_function("CreatePlayMontageAndWaitProxy",OwningAbility=ability,TaskInstanceName="None",
        MontageToPlay=asset,Rate=rate,StartSection="None",bStopWhenAbilityEnds=stop_on_end,AnimRootMotionTranslationScale=1.,
        StartTimeSeconds=0.,bAllowInterruptAfterBlendOut=False)
    if valid(task):
        if bind_completion:ability.call_function(BIND,task)
        task.call_function("ReadyForActivation")
    return task


def activate(ability):
    row=evidence(ability);row["activations"]+=1
    if ability.call_function("IsLocallyControlled"):
        row["targeting_requests"]+=1;ability.call_function("StartRangedWeaponTargeting")
    montage(ability,ability.get_property("CharacterFireMontage"),float(ability.get_property("AutoRate")),False,True);row["fire_tasks"]+=1
    schedule(ability,COMPLETE,float(ability.get_property("FireDelayTimeSecs")));row["fire_timers"]+=1


def make_cue(hit):
    result=lib("GameplayCueFunctionLibrary").call_function("MakeGameplayCueParametersFromHitResult",hit)
    return native_outputs("GameplayCueFunctionLibrary","MakeGameplayCueParametersFromHitResult",result)["ReturnValue"]


def target_data(ability,data):
    row=evidence(ability);row["target_data_calls"]+=1;system=lib("AbilitySystemBlueprintLibrary")
    first=system.call_function("GetHitResultFromTargetData",data,0);ability.set_property("GCNParameter",make_cue(first))
    ability.call_function("K2_ExecuteGameplayCueWithParams",ability.get_property("Gameplay Cue TagFiring"),ability.get_property("GCNParameter"));row["firing_cues"]+=1
    count=int(system.call_function("GetDataCountFromTargetData",data))
    for index in range(count):
        hit=system.call_function("GetHitResultFromTargetData",data,index);parts=break_hit(hit)
        if not parts["bBlockingHit"]:continue
        ability.call_function("K2_ExecuteGameplayCueWithParams",ability.get_property("GameplayCue_Impact"),make_cue(hit));row["impact_cues"]+=1
        if ability.call_function("K2_HasAuthority"):
            cls=ability.get_property("FieldActorToSpawnOnImpact")
            if lib("KismetSystemLibrary").call_function("IsValidClass",cls):
                transform=ue.FTransform(parts["ImpactPoint"],ue.FRotator(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.SelectDefaultAtRuntime
                actor=lib("GameplayStatics").call_function("BeginDeferredActorSpawnFromClass",WorldContextObject=ability,ActorClass=cls,
                    SpawnTransform=transform,CollisionHandlingOverride=ESpawnActorCollisionHandlingMethod.Undefined,Owner=None,TransformScaleMethod=scale)
                if valid(actor):lib("GameplayStatics").call_function("FinishSpawningActor",actor,transform,scale)
                row["field_spawns"]+=1
    if ability.call_function("K2_HasAuthority"):
        ability.call_function("BP_ApplyGameplayEffectToTarget",TargetData=data,GameplayEffectClass=ability.get_property("GE_Damage"),GameplayEffectLevel=1,Stacks=1)
        row["damage_requests"]+=1


def failure(ability,avatar,asset):
    row=evidence(ability);row["failure_messages"]+=1
    if avatar!=ability.call_function("GetAvatarActorFromActorInfo"):return
    health=lib("LyraHealthComponent").call_function("FindHealthComponent",ability.call_function("GetAvatarActorFromActorInfo"))
    if valid(health) and health.call_function("IsDeadOrDying"):return
    asc=ability.call_function("GetAbilitySystemComponentFromActorInfo")
    blocked=valid(asc) and lib("BlueprintGameplayTagLibrary").call_function("DoesTagAssetInterfaceHaveTag",asc,GameplayTag(TagName=NO_FIRING))
    if not ability.get_property("Can Trigger Failure Montage") or blocked:return
    montage(ability,asset,1.,True,False);row["failure_tasks"]+=1
    ability.set_property("Can Trigger Failure Montage",False)
    schedule(ability,FAILURE_COMPLETE,float(ability.get_property("Failure Montage Delay Time")));row["failure_timers"]+=1


def original_select(ability,normal,actor):
    result=ability.call_mixin_original(SELECT,normal,actor)
    if not isinstance(result,tuple) or len(result)!=1:raise RuntimeError("native weapon named montage output shape differs")
    return {"Hit Montage":result[0]}


def select(ability,normal,actor):
    row=evidence(ability);row["montage_choices"]+=1
    if actor is None:
        row["invalid_actor_native_fallback"]+=1;return original_select(ability,normal,actor)
    math=lib("KismetMathLibrary")
    forward=float(math.call_function("Dot_VectorVector",actor.call_function("GetActorForwardVector"),normal))
    right=float(math.call_function("Dot_VectorVector",actor.call_function("GetActorRightVector"),normal))
    straight=bool(math.call_function("InRange_FloatFloat",right,-.5,.5,True,True))
    # Preserve bool Select option order and the unusual authored fallback assets.
    choice=("front" if forward>0. else "back") if straight else ("right" if right>0. else "left")
    if straight:
        # The compiled pure Select inputs evaluate Front then Back, even when
        # only one option is returned. Preserve both native random draws.
        front=int(math.call_function("RandomIntegerInRange",0,3));back=int(math.call_function("RandomIntegerInRange",0,1))
        index=front if forward>0. else back
    else:index=int(math.call_function("RandomIntegerInRange",0,1))
    return {"Hit Montage":ue.load_object(ue.find_class("AnimMontage"),MONTAGES[choice][index])}


class LyraWeaponAbilityFirePythonProfile:
    def Activate(self):activate(self)
    Activate.override="K2_ActivateAbility"
    def Added(self):evidence(self)["added"]+=1;self.call_function(LISTEN)
    Added.override="K2_OnAbilityAdded"
    def TargetData(self,TargetData):target_data(self,TargetData)
    TargetData.override="OnRangedWeaponTargetDataReady"
    def FireComplete(self):evidence(self)["fire_complete"]+=1;self.call_function("K2_EndAbility")
    def MontageCompleted(self):evidence(self)["montage_completed"]+=1;self.call_function("K2_EndAbility")
    MontageCompleted.override=FIRE_CALLBACKS["OnCompleted"]
    def MontageInterrupted(self):evidence(self)["montage_interrupted"]+=1;self.call_function("K2_EndAbility")
    MontageInterrupted.override=FIRE_CALLBACKS["OnInterrupted"]
    def MontageCancelled(self):evidence(self)["montage_cancelled"]+=1;self.call_function("K2_EndAbility")
    MontageCancelled.override=FIRE_CALLBACKS["OnCancelled"]
    def FailureComplete(self):evidence(self)["failure_complete"]+=1;self.set_property("Can Trigger Failure Montage",True)
    FailureComplete.override=FAILURE_COMPLETE
    def FailureMessage(self,AvatarActor,FailureMontage):failure(self,AvatarActor,FailureMontage)
    FailureMessage.override=FAILURE
    def SelectHitMontage(self,HitNormal,HitActor):return select(self,HitNormal,HitActor)
    SelectHitMontage.override=SELECT;SelectHitMontage.uep_named_outputs=True


class LyraWeaponAbilityFireBlueprintFallbackProfile:
    def Activate(self):evidence(self)["fallback_activations"]+=1;return self.call_mixin_original("K2_ActivateAbility")
    Activate.override="K2_ActivateAbility"
    def Added(self):evidence(self)["fallback_added"]+=1;return self.call_mixin_original("K2_OnAbilityAdded")
    Added.override="K2_OnAbilityAdded"
    def TargetData(self,TargetData):evidence(self)["fallback_target_data_calls"]+=1;return self.call_mixin_original("OnRangedWeaponTargetDataReady",TargetData)
    TargetData.override="OnRangedWeaponTargetDataReady"
    def FireComplete(self):evidence(self)["fallback_fire_complete"]+=1;return self.call_mixin_original(COMPLETE)
    def MontageCompleted(self):evidence(self)["fallback_montage_callbacks"]+=1;return self.call_mixin_original(FIRE_CALLBACKS["OnCompleted"])
    MontageCompleted.override=FIRE_CALLBACKS["OnCompleted"]
    def MontageInterrupted(self):evidence(self)["fallback_montage_callbacks"]+=1;return self.call_mixin_original(FIRE_CALLBACKS["OnInterrupted"])
    MontageInterrupted.override=FIRE_CALLBACKS["OnInterrupted"]
    def MontageCancelled(self):evidence(self)["fallback_montage_callbacks"]+=1;return self.call_mixin_original(FIRE_CALLBACKS["OnCancelled"])
    MontageCancelled.override=FIRE_CALLBACKS["OnCancelled"]
    def FailureComplete(self):evidence(self)["fallback_failure_complete"]+=1;return self.call_mixin_original(FAILURE_COMPLETE)
    FailureComplete.override=FAILURE_COMPLETE
    def FailureMessage(self,AvatarActor,FailureMontage):evidence(self)["fallback_failure_messages"]+=1;return self.call_mixin_original(FAILURE,AvatarActor,FailureMontage)
    FailureMessage.override=FAILURE
    def SelectHitMontage(self,HitNormal,HitActor):evidence(self)["fallback_montage_choices"]+=1;return original_select(self,HitNormal,HitActor)
    SelectHitMontage.override=SELECT;SelectHitMontage.uep_named_outputs=True
