"""Original jump BP intent with native GAS tasks and movement; no BP reparent."""
import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from . import widget_lifecycle as widgets

CLASS = "/Game/Characters/Heroes/Abilities/GA_Hero_Jump.GA_Hero_Jump_C"
NATIVE_END, TEARING_DOWN = "UEPJumpNativeEnded", "UEPJumpTearingDown"
_active = {}
_stats = dict(activations=0, states_created=0, releases_created=0, state_ended=0, state_interrupted=0,
    input_releases=0, native_ends=0, scopes_created=0, scopes_closed=0, widget_added=0, widget_removed=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def close(ability):
    scope = ability._uep_jump_scope
    ability._uep_jump_scope = None
    ability._uep_jump_state = ability._uep_jump_release = None
    _active.pop(id(ability), None)
    if scope is not None:
        scope.close(); _stats["scopes_closed"] += 1


def stop(ability, interrupted=False):
    _stats["state_interrupted" if interrupted else "state_ended"] += 1
    ability.call_function("CharacterJumpStop")


def release(ability, held):
    _stats["input_releases"] += 1
    ability.call_function("K2_EndAbility")


def activate(ability):
    close(ability)
    scope = SubscriptionScope()
    ability._uep_jump_scope = scope
    _stats["scopes_created"] += 1; _stats["activations"] += 1
    _active[id(ability)] = ability.get_path_name()
    try:
        ability.call_function("CharacterJumpStart")
        state = ue.find_class("AbilityTask_StartAbilityState").get_cdo().call_function(
            "StartAbilityState", ability, "Jumping", True)
        ability._uep_jump_state = state; _stats["states_created"] += 1
        scope.bind_event(state, "OnStateEnded", lambda: stop(ability))
        scope.bind_event(state, "OnStateInterrupted", lambda: stop(ability, True))
        state.call_function("ReadyForActivation")
        task = ue.find_class("AbilityTask_WaitInputRelease").get_cdo().call_function("WaitInputRelease", ability, True)
        ability._uep_jump_release = task; _stats["releases_created"] += 1
        scope.bind_event(task, "OnRelease", lambda held: release(ability, held))
        task.call_function("ReadyForActivation")
    except Exception as error:
        _stats["errors"].append(str(error)); close(ability)
        ability.call_function("K2_EndAbility")
        raise


class LyraJumpPythonProfile:
    def __init__(self):
        self._uep_jump_scope = self._uep_jump_state = self._uep_jump_release = None

    def K2_ActivateAbility(self):
        activate(self)

    def K2_OnAbilityAdded(self):
        if widgets.add_single(self): _stats["widget_added"] += 1

    def K2_OnAbilityRemoved(self):
        widgets.remove_single(self); _stats["widget_removed"] += 1

    def NativeEnded(self, bWasCancelled):
        close(self); _stats["native_ends"] += 1
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        self.set_property(TEARING_DOWN, True)
        try:
            close(self)
            if self.get_property("bIsActive"): self.call_function("K2_CancelAbility")
        finally:
            self.set_property(TEARING_DOWN, False)


class LyraJumpBlueprintFallbackProfile:
    def K2_ActivateAbility(self):
        self.call_mixin_original("K2_ActivateAbility")

    def K2_OnAbilityAdded(self):
        self.call_mixin_original("K2_OnAbilityAdded")

    def K2_OnAbilityRemoved(self):
        self.call_mixin_original("K2_OnAbilityRemoved")

    def NativeEnded(self, bWasCancelled):
        self.call_mixin_original(NATIVE_END, bWasCancelled)
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        self.set_property(TEARING_DOWN, True)
        try:
            if self.get_property("bIsActive"): self.call_function("K2_CancelAbility")
        finally:
            self.set_property(TEARING_DOWN, False)
