"""Quickbar selection decisions; GAS event tasks/RPC/equipment remain native."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope

CLASS = "/ShooterCore/Game/GA_QuickbarSlots.GA_QuickbarSlots_C"
NATIVE_END, GUARD = "UEPQuickslotNativeEnded", "UEPQuickslotTearingDown"
TAGS = (("select", "InputTag.Ability.Quickslot.SelectSlot"),
        ("backward", "InputTag.Ability.Quickslot.CycleBackward"),
        ("forward", "InputTag.Ability.Quickslot.CycleForward"))
_active = {}
_stats = dict(activations=0, tasks_created=0, scopes_created=0, scopes_closed=0,
              selects=0, backward=0, forward=0, native_ends=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def close(ability):
    scope = ability._uep_quickslot_scope
    ability._uep_quickslot_scope, ability._uep_quickslot_tasks = None, []
    _active.pop(id(ability), None)
    if scope is not None:
        scope.close(); _stats["scopes_closed"] += 1


def dispatch(ability, kind, payload):
    quickbar = ability.QuickBarComponent
    if kind == "select":
        # Preserve native Blueprint Truncate, including its numeric semantics.
        index = ue.find_class("KismetMathLibrary").get_cdo().call_function("FTrunc", payload.EventMagnitude)
        quickbar.call_function("SetActiveSlotIndex", index)
        _stats["selects"] += 1
    else:
        quickbar.call_function("CycleActiveSlotBackward" if kind == "backward" else "CycleActiveSlotForward")
        _stats[kind] += 1


def end_for_teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        if ability.get_property("bIsActive"): ability.call_function("K2_EndAbility")
    finally:
        ability.set_property(GUARD, False)


def activate(ability):
    close(ability)
    controller = ability.call_function("GetControllerFromActorInfo")
    ability.set_property("QuickBarComponent", controller.call_function("GetComponentByClass", ue.find_class("LyraQuickBarComponent")))
    ability._uep_quickslot_scope = SubscriptionScope()
    _stats["activations"] += 1; _stats["scopes_created"] += 1
    _active[id(ability)] = ability.get_path_name()
    try:
        for kind, tag in TAGS:
            task = ue.find_class("AbilityTask_WaitGameplayEvent").get_cdo().call_function(
                "WaitGameplayEvent", ability, GameplayTag(TagName=tag), None, False, True)
            ability._uep_quickslot_tasks.append(task); _stats["tasks_created"] += 1
            ability._uep_quickslot_scope.bind_event(task, "EventReceived", lambda payload, kind=kind: dispatch(ability, kind, payload))
            task.call_function("ReadyForActivation")
    except Exception as error:
        _stats["errors"].append(str(error)); end_for_teardown(ability); raise


class LyraQuickslotPythonProfile:
    def __init__(self):
        self._uep_quickslot_scope, self._uep_quickslot_tasks = None, []

    def K2_ActivateAbility(self):
        activate(self)

    def NativeEnded(self, bWasCancelled):
        close(self); _stats["native_ends"] += 1
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        end_for_teardown(self)


class LyraQuickslotBlueprintFallbackProfile:
    def K2_ActivateAbility(self):
        self.call_mixin_original("K2_ActivateAbility")

    def NativeEnded(self, bWasCancelled):
        self.call_mixin_original(NATIVE_END, bWasCancelled)
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        self.set_property(GUARD, True)
        try:
            if self.get_property("bIsActive"): self.call_function("K2_EndAbility")
        finally:
            self.set_property(GUARD, False)
