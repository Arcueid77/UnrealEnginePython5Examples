"""Original prototype activation; native targeting, montage ownership and spawn."""
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod
from unreal_engine.structs import GameplayEffectContextHandle,GameplayTag,GameplayTagContainer,HitResult
from uep_lyra_world.effect_pad_mixin import valid

CLASS="/ShooterCore/Weapons/NetShooter_PROTO/GA_WeaponNetShooter.GA_WeaponNetShooter_C"
PROJECTILE="/ShooterCore/Weapons/NetShooter_PROTO/B_NetShooter.B_NetShooter_C"
BIND="UEPNetShooterBindMontageTask"
CALLBACKS={name:name+"_CBD1B4EC430B0115F3F85FB83619F775" for name in ("OnCompleted","OnInterrupted","OnCancelled")}
METHODS=("K2_ActivateAbility","OnRangedWeaponTargetDataReady")+tuple(CALLBACKS.values())


def lib(name):return ue.find_class(name).get_cdo()
def evidence(ability):
    row=getattr(ability,"_uep_netshooter_ability",None)
    if row is None:
        row={key:0 for key in ("activations","fallback_activations","targeting_requests","montage_tasks","firing_cues","authority_spawns",
            "target_data_noops","fallback_target_data_noops","completed","interrupted","cancelled","fallback_callbacks")}
        ability._uep_netshooter_ability=row
    return row


def pose(ability):
    controller=ability.call_function("GetLyraPlayerControllerFromActorInfo");camera=controller.get_property("PlayerCameraManager");math=lib("KismetMathLibrary")
    offset=math.call_function("Multiply_VectorFloat",controller.call_function("GetActorForwardVector"),350.)
    location=math.call_function("Add_VectorVector",offset,camera.call_function("GetCameraLocation"))
    ability.set_property("Location",location);ability.set_property("Direction",camera.call_function("GetCameraRotation"))


def cue(ability,character):
    mesh=character.get_property("Mesh");math=lib("KismetMathLibrary");offset=ability.get_property("OffsetGCN")
    location=mesh.call_function("GetSocketLocation","weapon_r_muzzle")
    for method,amount in (("GetActorForwardVector",offset.x),("GetActorUpVector",offset.z),("GetActorRightVector",offset.y)):
        location=math.call_function("Add_VectorVector",location,math.call_function("Multiply_VectorFloat",character.call_function(method),float(amount)))
    normal=math.call_function("Conv_RotatorToVector",mesh.call_function("GetSocketRotation","weapon_r_muzzle"))
    params=lib("AbilitySystemBlueprintLibrary").call_function("MakeGameplayCueParameters",NormalizedMagnitude=0.,RawMagnitude=0.,
        EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),
        AggregatedTargetTags=GameplayTagContainer(),Location=location,Normal=normal,Instigator=None,EffectCauser=None,SourceObject=None,PhysicalMaterial=None,
        GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
    ability.call_function("K2_ExecuteGameplayCueWithParams",ability.get_property("Gameplay Cue TagFiring"),params)


def activate(ability):
    row=evidence(ability);row["activations"]+=1
    if ability.call_function("IsLocallyControlled"):
        row["targeting_requests"]+=1;ability.call_function("StartRangedWeaponTargeting")
    task=lib("AbilityTask_PlayMontageAndWait").call_function("CreatePlayMontageAndWaitProxy",OwningAbility=ability,TaskInstanceName="None",
        MontageToPlay=ability.get_property("CharacterFireMontage"),Rate=float(ability.get_property("AutoRate")),StartSection="None",
        bStopWhenAbilityEnds=False,AnimRootMotionTranslationScale=1.,StartTimeSeconds=0.,bAllowInterruptAfterBlendOut=False)
    row["montage_tasks"]+=1
    if valid(task):ability.call_function(BIND,task);task.call_function("ReadyForActivation")
    pose(ability);character=ability.call_function("GetLyraCharacterFromActorInfo");cue(ability,character);row["firing_cues"]+=1
    if ability.call_function("K2_HasAuthority"):
        transform=ue.FTransform(ability.get_property("Location"),ability.get_property("Direction"),lib("KismetMathLibrary").call_function("MakeVector",.1,.1,.1))
        scale=ESpawnActorScaleMethod.OverrideRootScale;statics=lib("GameplayStatics")
        actor=statics.call_function("BeginDeferredActorSpawnFromClass",WorldContextObject=ability,ActorClass=ue.load_class(PROJECTILE),SpawnTransform=transform,
            CollisionHandlingOverride=ESpawnActorCollisionHandlingMethod.Undefined,Owner=None,TransformScaleMethod=scale)
        if valid(actor):
            actor.set_property("HitBreakResult",HitResult());actor.set_property("Instigator",character);statics.call_function("FinishSpawningActor",actor,transform,scale)
        row["authority_spawns"]+=1
    lib("KismetSystemLibrary").call_function("PrintString",WorldContextObject=ability,InString="NETSHOOTER",bPrintToScreen=True,bPrintToLog=True,
        TextColor=ue.FLinearColor(0.,.66,1.,1.),Duration=2.,Key="None")


class LyraNetShooterAbilityPythonProfile:
    def Activate(self):activate(self)
    Activate.override="K2_ActivateAbility"
    def TargetData(self,TargetData):evidence(self)["target_data_noops"]+=1
    TargetData.override="OnRangedWeaponTargetDataReady"
    def Completed(self):evidence(self)["completed"]+=1;self.call_function("K2_EndAbility")
    Completed.override=CALLBACKS["OnCompleted"]
    def Interrupted(self):evidence(self)["interrupted"]+=1;self.call_function("K2_EndAbility")
    Interrupted.override=CALLBACKS["OnInterrupted"]
    def Cancelled(self):evidence(self)["cancelled"]+=1;self.call_function("K2_EndAbility")
    Cancelled.override=CALLBACKS["OnCancelled"]


class LyraNetShooterAbilityBlueprintFallbackProfile:
    def Activate(self):evidence(self)["fallback_activations"]+=1;return self.call_mixin_original("K2_ActivateAbility")
    Activate.override="K2_ActivateAbility"
    def TargetData(self,TargetData):evidence(self)["fallback_target_data_noops"]+=1;return self.call_mixin_original("OnRangedWeaponTargetDataReady",TargetData)
    TargetData.override="OnRangedWeaponTargetDataReady"
    def Completed(self):evidence(self)["fallback_callbacks"]+=1;return self.call_mixin_original(CALLBACKS["OnCompleted"])
    Completed.override=CALLBACKS["OnCompleted"]
    def Interrupted(self):evidence(self)["fallback_callbacks"]+=1;return self.call_mixin_original(CALLBACKS["OnInterrupted"])
    Interrupted.override=CALLBACKS["OnInterrupted"]
    def Cancelled(self):evidence(self)["fallback_callbacks"]+=1;return self.call_mixin_original(CALLBACKS["OnCancelled"])
    Cancelled.override=CALLBACKS["OnCancelled"]
