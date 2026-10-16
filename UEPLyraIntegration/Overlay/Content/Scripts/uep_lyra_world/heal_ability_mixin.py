"""Old heal ability BP policy; native GAS, Montage task and TimerManager remain."""
import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from .effect_pad_mixin import valid

CLASS = "/ShooterCore/Items/HealthPickup_Unused/GA_HealPickup.GA_HealPickup_C"
NATIVE_END, TEARING_DOWN = "UEPHealNativeEnded", "UEPHealTearingDown"
_active = {}
_stats = dict(activations=0, cost_rejections=0, commit_rejections=0, tasks_created=0,
              scopes_created=0, scopes_closed=0, heals=0, timers_created=0, timers_cleared=0,
              timer_callbacks=0, completed=0, interrupted=0, cancelled=0, end_requests=0,
              native_ends=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def close(ability):
    scope, timer = ability._uep_heal_scope, ability._uep_heal_timer
    ability._uep_heal_scope = ability._uep_heal_timer = None
    _active.pop(id(ability), None)
    # Disarm delegates before timer/native GAS cancellation can reenter.
    if scope is not None:
        scope.close(); _stats["scopes_closed"] += 1
    if timer is not None:
        timer.clear(); _stats["timers_cleared"] += 1


def end(ability, reason):
    if reason in ("completed", "interrupted", "cancelled"):
        _stats[reason] += 1
    elif reason == "timer":
        _stats["timer_callbacks"] += 1
    close(ability)
    _stats["end_requests"] += 1
    ability.call_function("K2_EndAbility")


def activate(ability):
    close(ability)
    _stats["activations"] += 1
    if not ability.call_function("K2_CheckAbilityCost"):
        _stats["cost_rejections"] += 1
        end(ability, "cost")
        return
    if not ability.call_function("K2_CommitAbility"):
        _stats["commit_rejections"] += 1
        end(ability, "commit")
        return
    task = ue.find_class("AbilityTask_PlayMontageAndWait").get_cdo().call_function("CreatePlayMontageAndWaitProxy",
        OwningAbility=ability, TaskInstanceName="None", MontageToPlay=ability.get_property("Heal Montage"),
        Rate=1., StartSection="None", bStopWhenAbilityEnds=False, AnimRootMotionTranslationScale=1.,
        StartTimeSeconds=0., bAllowInterruptAfterBlendOut=False)
    if not valid(task):
        raise RuntimeError("heal ability native Montage task creation failed")
    scope = SubscriptionScope()
    ability._uep_heal_task, ability._uep_heal_scope = task, scope
    _active[id(ability)] = ability.get_path_name()
    _stats["tasks_created"] += 1; _stats["scopes_created"] += 1
    try:
        for event, reason in (("OnCompleted", "completed"), ("OnInterrupted", "interrupted"), ("OnCancelled", "cancelled")):
            scope.bind_event(task, event, lambda cause=reason: end(ability, cause))
        # Match the original ability task node: activate after delegate binding,
        # then continue into the immediate GE application, NOT OnCompleted.
        task.call_function("ReadyForActivation")
        ability.call_function("BP_ApplyGameplayEffectToOwner", ability.get_property("Heal Effect"), 1, 1)
        _stats["heals"] += 1
        # The existing UEP timer wrapper resolves Actor/Component Worlds, not
        # GameplayAbility::GetWorld. Use the native actor-info Avatar rather
        # than introducing a timer ticker or altering the Engine implementation.
        avatar = ability.call_function("GetAvatarActorFromActorInfo")
        if not valid(avatar):
            raise RuntimeError("heal ability has no native Avatar for timer ownership")
        ability._uep_heal_timer = avatar.set_timer(1., lambda: end(ability, "timer"), False)
        _stats["timers_created"] += 1
    except Exception as error:
        _stats["errors"].append(str(error)); close(ability)
        ability.call_function("K2_EndAbility")
        raise


class LyraHealAbilityPythonProfile:
    def __init__(self):
        self._uep_heal_scope = self._uep_heal_timer = self._uep_heal_task = None

    def K2_ActivateAbility(self):
        activate(self)

    def NativeEnded(self, bWasCancelled):
        close(self)
        self._uep_heal_task = None
        _stats["native_ends"] += 1
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        self.set_property(TEARING_DOWN, True)
        try:
            close(self)
            self._uep_heal_task = None
            if self.get_property("bIsActive"):
                self.call_function("K2_CancelAbility")
        finally:
            self.set_property(TEARING_DOWN, False)


class LyraHealAbilityBlueprintFallbackProfile:
    def K2_ActivateAbility(self):
        self.call_mixin_original("K2_ActivateAbility")

    def NativeEnded(self, bWasCancelled):
        self.call_mixin_original(NATIVE_END, bWasCancelled)
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        self.set_property(TEARING_DOWN, True)
        try:
            if self.get_property("bIsActive"):
                self.call_function("K2_CancelAbility")
        finally:
            self.set_property(TEARING_DOWN, False)
