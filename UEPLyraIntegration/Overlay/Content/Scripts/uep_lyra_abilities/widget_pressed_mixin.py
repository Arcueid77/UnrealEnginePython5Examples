"""Pressed-widget policy; native GAS/streaming/UI retain their own lifetimes."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhenInputPressed.GAB_ShowWidget_WhenInputPressed_C"
CLASS_PATH, NATIVE_END = "UEPWidgetPressedClassPath", "UEPWidgetPressedNativeEnded"
GUARD, PENDING, WIDGET = "UEPWidgetPressedTearingDown", "UEPWidgetPressedPending", "UEPWidgetPressedWidget"
REMOVE = "UEPRemoveOriginalPressedWidgetBinding"
_active = {}
_stats = dict(activations=0, pushes_requested=0, widgets_pushed=0, widget_deactivated=0,
    scopes_created=0, scopes_closed=0, native_ends=0, pending_cancelled=0,
    fallback_activations=0, fallback_deactivated=0, fallback_native_ends=0,
    original_bindings_removed=0, teardown_widget_deactivated=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def close_scope(ability, field):
    scope = getattr(ability, field)
    setattr(ability, field, None)
    if scope is not None:
        scope.close(); _stats["scopes_closed"] += 1


def close(ability):
    close_scope(ability, "_uep_pressed_push")
    close_scope(ability, "_uep_pressed_widget")
    _active.pop(id(ability), None)
    action = ability.get_property(PENDING)
    ability.set_property(PENDING, None)
    if valid(action):
        action.call_function("Cancel"); _stats["pending_cancelled"] += 1
    # Ordinary native End does not deactivate the original UI-owned panel.
    # Forget the claim so later pool reuse cannot let us deactivate a new owner.
    ability.set_property(WIDGET, None)


def after_push(ability, scope, widget):
    if ability._uep_pressed_push is not scope:
        return
    if not valid(widget):
        raise RuntimeError("native pressed-widget push returned no widget")
    ability.set_property(PENDING, None)
    ability.set_property(WIDGET, widget)
    owned = SubscriptionScope(); ability._uep_pressed_widget = owned
    _stats["scopes_created"] += 1
    def deactivated():
        if ability._uep_pressed_widget is owned:
            ability.call_function("OnWidgetDeactivated")
    owned.bind_event(widget, "BP_OnWidgetDeactivated", deactivated)
    _stats["widgets_pushed"] += 1
    close_scope(ability, "_uep_pressed_push")


def activate(ability):
    close(ability)
    _active[id(ability)] = ability.get_path_name()
    _stats["activations"] += 1
    try:
        path = ability.call_function(CLASS_PATH)
        if not path: raise RuntimeError("pressed-widget requires its original configured WidgetToSpawn")
        controller = ability.call_function("GetLyraPlayerControllerFromActorInfo")
        action = ue.find_class("AsyncAction_PushContentToLayerForPlayer").get_cdo().call_function(
            "PushContentToLayerForPlayer", controller, path, GameplayTag(TagName="UI.Layer.GameMenu"), True)
        if not valid(action): raise RuntimeError("native pressed-widget action creation failed")
        scope = SubscriptionScope(); ability._uep_pressed_push = scope
        _stats["scopes_created"] += 1
        ability.set_property(PENDING, action)
        scope.bind_event(action, "AfterPush", lambda widget: after_push(ability, scope, widget))
        _stats["pushes_requested"] += 1
        action.call_function("Activate")
    except Exception as error:
        _stats["errors"] = (_stats["errors"] + [str(error)])[-16:]
        teardown(ability); raise


def teardown(ability):
    previous = ability.get_property(GUARD)
    ability.set_property(GUARD, True)
    widget, was_active = ability.get_property(WIDGET), bool(ability.get_property("bIsActive"))
    try:
        # Disarm Python and the exact original-BP binding before native UI/End
        # can reenter the mutating router. Never clear a foreign subscriber.
        close(ability)
        if valid(widget):
            ability.call_function(REMOVE, widget); _stats["original_bindings_removed"] += 1
        if was_active: ability.call_function("K2_EndAbility")
        if was_active and valid(widget) and widget.call_function("IsActivated"):
            widget.call_function("DeactivateWidget"); _stats["teardown_widget_deactivated"] += 1
    finally:
        ability.set_property(GUARD, previous)


class LyraWidgetPressedPythonProfile:
    def __init__(self): self._uep_pressed_push, self._uep_pressed_widget = None, None
    def K2_ActivateAbility(self): activate(self)
    def OnWidgetDeactivated(self):
        _stats["widget_deactivated"] += 1
        self.call_function("K2_EndAbility")
    def NativeEnded(self, bWasCancelled):
        close(self); _stats["native_ends"] += 1
    NativeEnded.override = NATIVE_END
    def __uep_mixin_teardown__(self): teardown(self)


class LyraWidgetPressedBlueprintFallbackProfile:
    def __init__(self): self._uep_pressed_push, self._uep_pressed_widget = None, None
    def K2_ActivateAbility(self):
        _stats["fallback_activations"] += 1; self.call_mixin_original("K2_ActivateAbility")
    def OnWidgetDeactivated(self):
        _stats["fallback_deactivated"] += 1; self.call_mixin_original("OnWidgetDeactivated")
    def NativeEnded(self, bWasCancelled): _stats["fallback_native_ends"] += 1
    NativeEnded.override = NATIVE_END
    def __uep_mixin_teardown__(self): teardown(self)
