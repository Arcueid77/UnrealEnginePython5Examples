"""Retained held-widget BP policy; native GAS, streaming and UI own execution."""
import copy

import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhileInputHeld.GAB_ShowWidget_WhileInputHeld_C"
NATIVE_END, GUARD = "UEPWidgetHeldNativeEnded", "UEPWidgetHeldTearingDown"
CLASS_PATH = "UEPWidgetHeldClassPath"
_active, _instances = {}, {}
_stats = dict(activations=0, scopes_created=0, scopes_closed=0, tasks_created=0,
    pushes_requested=0, widgets_pushed=0, widgets_removed=0, pending_cancelled=0,
    cached_widget_skips=0, input_released=0, state_ended=0, state_interrupted=0,
    native_ends=0, fallback_activations=0, fallback_native_ends=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def instance_snapshot(ability):
    return dict({key: 0 for key, value in _stats.items() if type(value) is int}, **_instances.get(ability.get_path_name(), {}))


def note(ability, key):
    _stats[key] += 1
    counts = _instances.setdefault(ability.get_path_name(), {}); counts[key] = counts.get(key, 0) + 1
    while len(_instances) > 256: _instances.pop(next(iter(_instances)))


def close_push(ability):
    scope, ability._uep_widget_push = ability._uep_widget_push, None
    if scope is not None:
        scope.close(); note(ability, "scopes_closed")


def close(ability):
    close_push(ability)
    scope, ability._uep_widget_tasks = ability._uep_widget_tasks, None
    _active.pop(id(ability), None)
    if scope is not None:
        scope.close(); note(ability, "scopes_closed")


def remove_widget(ability):
    # Disarm the owned Python completion before native cancellation can reenter.
    close_push(ability)
    action = ability.get_property("Async Action")
    ability.set_property("Async Action", None)
    if valid(action):
        action.call_function("Cancel"); note(ability, "pending_cancelled")
    widget = ability.get_property("SpawnedWidget")
    ability.set_property("SpawnedWidget", None)
    if valid(widget):
        widget.call_function("DeactivateWidget"); note(ability, "widgets_removed")


def pushed(ability, scope, widget):
    if ability._uep_widget_push is not scope:
        return
    try:
        ability.set_property("SpawnedWidget", widget)
        ability.set_property("Async Action", None)
        note(ability, "widgets_pushed")
    finally:
        # The completed native proxy can now be collected, even while held.
        close_push(ability)


def display_widget(ability):
    if valid(ability.get_property("SpawnedWidget")):
        note(ability, "cached_widget_skips"); return
    if valid(ability.get_property("Async Action")):
        # Public repeated requests must not orphan a previously owned pending
        # native action. This is an explicit lifetime improvement over the BP.
        remove_widget(ability)
    controller = ability.call_function("GetLyraPlayerControllerFromActorInfo")
    # A reflected soft-class property reads as None before its target is loaded.
    # The typed VM adapter preserves the original per-instance soft path without
    # synchronously loading a class or hardcoding either scoreboard child.
    widget_class = ability.call_function(CLASS_PATH)
    if not widget_class:
        raise RuntimeError("held-widget requires its original configured Widget Class")
    action = ue.find_class("AsyncAction_PushContentToLayerForPlayer").get_cdo().call_function(
        "PushContentToLayerForPlayer", controller, widget_class,
        ability.get_property("Layer Name"), False)
    if not valid(action): raise RuntimeError("native held-widget push action creation failed")
    scope = SubscriptionScope(); ability._uep_widget_push = scope; note(ability, "scopes_created")
    ability.set_property("Async Action", action)
    scope.bind_event(action, "AfterPush", lambda widget: pushed(ability, scope, widget))
    note(ability, "pushes_requested")
    action.call_function("Activate")


def state_ended(ability, interrupted):
    note(ability, "state_interrupted" if interrupted else "state_ended")
    ability.call_function("RemoveWidget")


def input_released(ability, elapsed):
    note(ability, "input_released"); ability.call_function("K2_EndAbility")


def activate(ability):
    close(ability)
    scope = SubscriptionScope(); ability._uep_widget_tasks = scope
    _active[id(ability)] = ability.get_path_name()
    note(ability, "activations"); note(ability, "scopes_created")
    try:
        task = ue.find_class("AbilityTask_StartAbilityState").get_cdo().call_function(
            "StartAbilityState", ability, "ShowWidget_WhenInputHeld", True)
        if not valid(task): raise RuntimeError("native held-widget ability state missing")
        note(ability, "tasks_created")
        scope.bind_event(task, "OnStateEnded", lambda: state_ended(ability, False))
        scope.bind_event(task, "OnStateInterrupted", lambda: state_ended(ability, True))
        task.call_function("ReadyForActivation")
        if ability._uep_widget_tasks is not scope:
            return
        ability.call_function("CreateAndDisplayWidget")
        if ability._uep_widget_tasks is not scope:
            return
        release = ue.find_class("AbilityTask_WaitInputRelease").get_cdo().call_function("WaitInputRelease", ability, False)
        if not valid(release): raise RuntimeError("native held-widget input-release task missing")
        note(ability, "tasks_created")
        scope.bind_event(release, "OnRelease", lambda elapsed: input_released(ability, elapsed))
        release.call_function("ReadyForActivation")
    except Exception as error:
        _stats["errors"] = (_stats["errors"] + [str(error)])[-16:]
        teardown(ability); raise


def teardown(ability):
    previous = ability.get_property(GUARD)
    ability.set_property(GUARD, True)
    try:
        close(ability); remove_widget(ability)
        if ability.get_property("bIsActive"): ability.call_function("K2_EndAbility")
    finally:
        ability.set_property(GUARD, previous)


class LyraWidgetHeldPythonProfile:
    def __init__(self): self._uep_widget_tasks, self._uep_widget_push = None, None
    def K2_ActivateAbility(self): activate(self)
    def CreateAndDisplayWidget(self): display_widget(self)
    def RemoveWidget(self): remove_widget(self)
    def NativeEnded(self, bWasCancelled):
        close(self); remove_widget(self); note(self, "native_ends"); return False
    NativeEnded.override = NATIVE_END
    def __uep_mixin_teardown__(self): teardown(self)


class LyraWidgetHeldBlueprintFallbackProfile:
    def __init__(self): self._uep_widget_tasks, self._uep_widget_push = None, None
    def K2_ActivateAbility(self):
        note(self, "fallback_activations"); self.call_mixin_original("K2_ActivateAbility")
    def CreateAndDisplayWidget(self): self.call_mixin_original("CreateAndDisplayWidget")
    def RemoveWidget(self): self.call_mixin_original("RemoveWidget")
    def NativeEnded(self, bWasCancelled):
        note(self, "fallback_native_ends"); return True
    NativeEnded.override = NATIVE_END
    def __uep_mixin_teardown__(self): teardown(self)
