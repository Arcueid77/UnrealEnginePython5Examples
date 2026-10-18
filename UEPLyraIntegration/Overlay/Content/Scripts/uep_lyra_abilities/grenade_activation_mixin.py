"""Original Grenade activation decisions; native aim/trace/spawn/montage/GAS."""
import unreal_engine as ue
from unreal_engine.structs import LyraInteractionDurationMessage
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod,ETraceTypeQuery,EDrawDebugTrace
from uep_lyra_world.effect_pad_mixin import valid
from .grenade_widget_mixin import LyraGrenadeWidgetPythonProfile as UiPython,LyraGrenadeWidgetBlueprintFallbackProfile as UiBlueprint
from .melee_trace_mixin import trace_outputs,break_hit
from .auto_respawn_events_mixin import broadcast

PROJECTILE="/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"
CHANNEL="Ability.Grenade.Duration.Message"


def evidence(ability):
    value=getattr(ability,"_uep_grenade_activation",None)
    if value is None:
        value=dict(python_calls=0,fallback_calls=0,cost_checks=0,cooldown_checks=0,commits=0,denied=0,
            aim_queries=0,near_control_rotation=0,hit_aim=0,miss_aim=0,projectiles=0,cooldown_writes=0,
            montage_tasks=0,duration_messages=0,native_ends=0,invalid_receiver_defaults=0,order=[],last=None)
        ability._uep_grenade_activation=value
    return value


def note(ability,key):
    counts=evidence(ability);counts[key]+=1;counts["order"].append(key);counts["order"]=counts["order"][-48:]


def lib(name): return ue.find_class(name).get_cdo()
def vector(value): return [float(value.x),float(value.y),float(value.z)]
def rotation(value): return [float(value.roll),float(value.pitch),float(value.yaw)]


def native_value(ability,obj,method,default):
    if valid(obj): return obj.call_function(method)
    # Original VM invalid-context values are zero-initialized. These receivers
    # normally exist for actual granted player abilities; keep defaults explicit.
    note(ability,"invalid_receiver_defaults")
    return default


def aim(ability):
    math=lib("KismetMathLibrary");character=ability.call_function("GetLyraCharacterFromActorInfo")
    point=native_value(ability,character,"K2_GetActorLocation",ue.FVector())
    forward=native_value(ability,character,"GetActorForwardVector",ue.FVector())
    up=native_value(ability,character,"GetActorUpVector",ue.FVector())
    point=math.call_function("Add_VectorVector",point,math.call_function("Multiply_VectorFloat",forward,5.))
    point=math.call_function("Add_VectorVector",point,math.call_function("Multiply_VectorFloat",up,25.))
    ability.set_property("Location",point)
    controller=ability.call_function("GetLyraPlayerControllerFromActorInfo")
    camera=controller.get_property("PlayerCameraManager") if valid(controller) else None
    eye=native_value(ability,camera,"GetCameraLocation",ue.FVector())
    look=native_value(ability,camera,"GetCameraRotation",ue.FRotator())
    facing=math.call_function("Conv_RotatorToVector",look)
    end=math.call_function("Add_VectorVector",eye,math.call_function("Multiply_VectorFloat",facing,ability.get_property("Default Targeting Range")))
    start=math.call_function("Add_VectorVector",eye,math.call_function("Multiply_VectorFloat",facing,ability.get_property("Start Trace Offset")))
    result=lib("KismetSystemLibrary").call_function("LineTraceSingle",WorldContextObject=ability,Start=start,End=end,TraceChannel=ETraceTypeQuery.TraceTypeQuery4,
        bTraceComplex=False,ActorsToIgnore=[character],DrawDebugType=getattr(EDrawDebugTrace,"None"),bIgnoreSelf=True,
        TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=5.)
    hit,record=trace_outputs("LineTraceSingle",result);fields=break_hit(record);note(ability,"aim_queries")
    # Original tests distance BEFORE the hit boolean (including miss defaults).
    if math.call_function("Less_DoubleDouble",float(fields["Distance"]),45.):
        direction=native_value(ability,controller,"GetControlRotation",ue.FRotator());note(ability,"near_control_rotation")
    else:
        target=fields["Location"] if hit else end
        direction=math.call_function("FindLookAtRotation",point,target);note(ability,"hit_aim" if hit else "miss_aim")
    ability.set_property("Direction",direction)
    evidence(ability)["last"]=dict(location=vector(point),direction=rotation(direction),trace_hit=hit,trace_distance=float(fields["Distance"]),
        trace_start=vector(start),trace_end=vector(end))
    return character,point,direction


def activate(ability):
    note(ability,"python_calls")
    cost=bool(ability.call_function("K2_CheckAbilityCost"));note(ability,"cost_checks")
    cooldown=bool(ability.call_function("K2_CheckAbilityCooldown"));note(ability,"cooldown_checks")
    if not(cost and cooldown):
        note(ability,"denied");ability.call_function("K2_EndAbility");note(ability,"native_ends");return
    ability.call_function("K2_CommitAbility");note(ability,"commits") # Return intentionally ignored, as in BP.
    character,point,direction=aim(ability)
    if ability.call_function("K2_HasAuthority"):
        scale=ESpawnActorScaleMethod.OverrideRootScale
        # The typed native wrapper avoids the generic Editor default importer:
        # MakeTransform's CPP_Default_Scale is a comma triple, not ImportText's
        # parenthesized FVector form (even when Scale is explicitly supplied).
        transform=ue.FTransform(point,direction,ue.FVector(1.,1.,1.))
        actor=lib("GameplayStatics").call_function("BeginDeferredActorSpawnFromClass",ability,ue.load_class(PROJECTILE),transform,
            ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        if valid(actor):
            actor.set_property("Instigator",character)
            lib("GameplayStatics").call_function("FinishSpawningActor",actor,transform,scale);note(ability,"projectiles")
        ability.set_property("Cooldown Time",ability.call_function("GetCooldownTimeRemaining"));note(ability,"cooldown_writes")
    task=lib("AbilityTask_PlayMontageAndWait").call_function("CreatePlayMontageAndWaitProxy",OwningAbility=ability,TaskInstanceName="None",
        MontageToPlay=ability.get_property("GrenadeThrowMontage"),Rate=1.,StartSection="None",bStopWhenAbilityEnds=False,
        AnimRootMotionTranslationScale=1.,StartTimeSeconds=0.,bAllowInterruptAfterBlendOut=False)
    if valid(task): task.call_function("ReadyForActivation");note(ability,"montage_tasks")
    broadcast(ability,"Duration",CHANNEL,LyraInteractionDurationMessage(Instigator=character,Duration=ability.get_property("Cooldown Time")))
    note(ability,"duration_messages")
    # No montage delegates were connected in the original graph. End now;
    # native bStopWhenAbilityEnds=False retains the authored montage behavior.
    ability.call_function("K2_EndAbility");note(ability,"native_ends")


class LyraGrenadeActivationPythonProfile:
    K2_OnPawnAvatarSet=UiPython.K2_OnPawnAvatarSet
    K2_OnAbilityRemoved=UiPython.K2_OnAbilityRemoved
    def K2_ActivateAbility(self): activate(self)


class LyraGrenadeActivationBlueprintFallbackProfile:
    K2_OnPawnAvatarSet=UiBlueprint.K2_OnPawnAvatarSet
    K2_OnAbilityRemoved=UiBlueprint.K2_OnAbilityRemoved
    def K2_ActivateAbility(self):
        note(self,"fallback_calls");return self.call_mixin_original("K2_ActivateAbility")
