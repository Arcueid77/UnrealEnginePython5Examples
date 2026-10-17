"""Dash task/Cue/UI/continuation business; original engine task/Delay primitives."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayTagContainer, GameplayEffectContextHandle, LyraInteractionDurationMessage
from unreal_engine.enums import ERootMotionFinishVelocityMode
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from .dash_activation_mixin import LyraDashActivationPythonProfile, LyraDashActivationBlueprintFallbackProfile, TASKS
from .dash_rpc_input_mixin import received as store_remote

DELAY = "UEPDashBeginNativeDelay"
AFTER = "UEPDashAfterNativeDelay"
ENDED, GUARD = "UEPDashNativeEnded", "UEPDashTearingDown"
ADAPTER = "/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C"
_active, _instances = {}, {}
_stats = dict(task_starts=0, fallback_task_starts=0, montage_tasks=0, root_tasks=0, root_finished=0,
    native_delays_started=0, delay_completed=0, fallback_delay_completed=0, cues=0, ui_messages=0,
    montage_interrupted=0, montage_cancelled=0, native_ends=0, fallback_native_ends=0,
    remote_commits=0, scopes_created=0, scopes_closed=0, errors=[])


def snapshot(): return dict(copy.deepcopy(_stats), active_count=len(_active))
def instance_snapshot(ability): return copy.deepcopy(_instances.get(ability.get_path_name(), {}))
def library(name): return ue.find_class(name).get_cdo()
def note(ability, name):
    _stats[name] += 1
    values = _instances.setdefault(ability.get_path_name(), {}); values[name] = values.get(name, 0)+1
    while len(_instances) > 256: _instances.pop(next(iter(_instances)))


def close(ability):
    scope = getattr(ability, "_uep_dash_tasks_scope", None); ability._uep_dash_tasks_scope = None
    _active.pop(id(ability), None)
    if scope is not None:
        scope.close(); note(ability, "scopes_closed")


def ended_by_montage(ability, kind):
    note(ability, kind); ability.call_function("K2_EndAbility")


def root_finished(ability):
    note(ability, "root_finished")
    # Float parameters are captured by the native transport; the same original
    # latent node preserves pause, <=0 duration and ability-end cancellation.
    duration = float(ability.get_property("AbilityDuration"))-float(ability.get_property("RootMotionDuration"))
    ability.call_function(DELAY, duration); note(ability, "native_delays_started")


def cue(ability):
    if not ability.call_function("K2_HasAuthority"): return
    parameters = library("AbilitySystemBlueprintLibrary").call_function("MakeGameplayCueParameters",
        NormalizedMagnitude=float(ability.get_property("RootMotionDuration")), RawMagnitude=float(ability.get_property("Strength")),
        EffectContext=GameplayEffectContextHandle(), MatchedTagName=GameplayTag(), OriginalTag=GameplayTag(),
        AggregatedSourceTags=GameplayTagContainer(), AggregatedTargetTags=GameplayTagContainer(),
        Location=ue.FVector(0., 0., 0.), Normal=ability.get_property("Direction"), Instigator=None, EffectCauser=None,
        SourceObject=None, PhysicalMaterial=None, GameplayEffectLevel=1, AbilityLevel=1, TargetAttachComponent=None,
        bReplicateLocationWhenUsingMinimalRepProxy=False)
    ability.call_function("K2_ExecuteGameplayCueWithParams", GameplayTag(TagName="GameplayCue.Character.Dash"), parameters)
    note(ability, "cues")


def broadcast(ability):
    router = library("SubsystemBlueprintLibrary").call_function("GetGameInstanceSubsystem", ability, ue.find_class("GameplayMessageSubsystem"))
    payload = LyraInteractionDurationMessage(Instigator=ability.call_function("GetLyraCharacterFromActorInfo"),
        Duration=float(ability.call_function("GetCooldownTimeRemaining")))
    ue.load_class(ADAPTER).get_cdo().call_function("BroadcastDuration", router, GameplayTag(TagName="Ability.Dash.Duration.Message"), payload)
    note(ability, "ui_messages")


def start(ability):
    scope = getattr(ability, "_uep_dash_tasks_scope", None)
    if scope is None:
        scope = SubscriptionScope(); ability._uep_dash_tasks_scope = scope
        _active[id(ability)] = ability.get_path_name(); note(ability, "scopes_created")
    note(ability, "task_starts")
    try:
        montage = library("AbilityTask_PlayMontageAndWait").call_function("CreatePlayMontageAndWaitProxy",
            OwningAbility=ability, TaskInstanceName="None", MontageToPlay=ability.get_property("Montage"), Rate=1., StartSection="None",
            bStopWhenAbilityEnds=False, AnimRootMotionTranslationScale=1., StartTimeSeconds=0., bAllowInterruptAfterBlendOut=False)
        if not valid(montage): raise RuntimeError("native Dash montage task creation failed")
        note(ability, "montage_tasks")
        for event, kind in (("OnInterrupted", "montage_interrupted"), ("OnCancelled", "montage_cancelled")):
            scope.bind_event(montage, event, lambda kind=kind: ended_by_montage(ability, kind))
        montage.call_function("ReadyForActivation")
        root = library("AbilityTask_ApplyRootMotionConstantForce").call_function("ApplyRootMotionConstantForce",
            OwningAbility=ability, TaskInstanceName="None", WorldDirection=ability.get_property("Direction"),
            Strength=float(ability.get_property("Strength")), Duration=float(ability.get_property("RootMotionDuration")),
            bIsAdditive=True, StrengthOverTime=None, VelocityOnFinishMode=ERootMotionFinishVelocityMode.ClampVelocity,
            SetVelocityOnFinish=ue.FVector(0., 0., 0.), ClampVelocityOnFinish=1000., bEnableGravity=False)
        if not valid(root): raise RuntimeError("native Dash RootMotion task creation failed")
        note(ability, "root_tasks"); scope.bind_event(root, "OnFinish", lambda: root_finished(ability))
        root.call_function("ReadyForActivation")
        # Original Sequence: root task -> authority Cue, then duration message.
        cue(ability); broadcast(ability)
    except Exception as error:
        _stats["errors"] = (_stats["errors"]+[str(error)])[-16:]
        teardown(ability); raise


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        if ability.get_property("bIsActive"): ability.call_function("K2_EndAbility")
    finally: ability.set_property(GUARD, False)


class LyraDashTasksPythonProfile:
    def __init__(self): self._uep_dash_tasks_scope = None
    SelectDirectionalMontage = LyraDashActivationPythonProfile.__dict__["SelectDirectionalMontage"]
    PrepareLocalDirection = LyraDashActivationPythonProfile.__dict__["PrepareLocalDirection"]
    Activate = LyraDashActivationPythonProfile.__dict__["Activate"]
    def StoreRemoteInput(self, Vector, Montage):
        store_remote(self, Vector, Montage, True)
        # Original server body deliberately ignores Commit's return value.
        self.call_function("K2_CommitAbility"); note(self, "remote_commits")
        self.call_function(TASKS); return False
    StoreRemoteInput.override = "UEPDashStoreRemoteInput"
    def StartNativeTasks(self): start(self)
    StartNativeTasks.override = TASKS
    def AfterNativeDelay(self):
        note(self, "delay_completed"); self.call_function("K2_EndAbility"); return False
    AfterNativeDelay.override = AFTER
    def NativeEnded(self, bWasCancelled): close(self); note(self, "native_ends"); return False
    NativeEnded.override = ENDED
    def __uep_mixin_teardown__(self): teardown(self)


class LyraDashTasksBlueprintFallbackProfile:
    def __init__(self): self._uep_dash_tasks_scope = None
    SelectDirectionalMontage = LyraDashActivationBlueprintFallbackProfile.__dict__["SelectDirectionalMontage"]
    PrepareLocalDirection = LyraDashActivationBlueprintFallbackProfile.__dict__["PrepareLocalDirection"]
    Activate = LyraDashActivationBlueprintFallbackProfile.__dict__["Activate"]
    StoreRemoteInput = LyraDashActivationBlueprintFallbackProfile.__dict__["StoreRemoteInput"]
    def StartNativeTasks(self):
        note(self, "fallback_task_starts"); return self.call_mixin_original(TASKS)
    StartNativeTasks.override = TASKS
    def AfterNativeDelay(self): note(self, "fallback_delay_completed"); return True
    AfterNativeDelay.override = AFTER
    def NativeEnded(self, bWasCancelled):
        close(self); note(self, "fallback_native_ends"); return True
    NativeEnded.override = ENDED
    def __uep_mixin_teardown__(self): teardown(self)
