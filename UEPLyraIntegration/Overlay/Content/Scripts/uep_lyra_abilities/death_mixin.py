"""Death BP camera/cue/delay decisions; native death/GAS/respawn stay native."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope

CLASS = "/Game/Characters/Heroes/Abilities/GA_Hero_Death.GA_Hero_Death_C"
NATIVE_END, GUARD = "UEPDeathNativeEnded", "UEPDeathTearingDown"
_active = {}
_stats = dict(activations=0, cameras_set=0, cues_executed=0, waits_created=0, waits_finished=0,
              scopes_created=0, scopes_closed=0, native_ends=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def close(ability):
    scope = ability._uep_death_scope
    ability._uep_death_scope = ability._uep_death_wait = None
    _active.pop(id(ability), None)
    if scope is not None:
        scope.close(); _stats["scopes_closed"] += 1


def end_for_teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        # Native Death is deliberately non-cancelable. Do not change its flag
        # or leave a callback-less active death after Profile teardown. End it
        # through the same native FinishDeath path, with the busy router guarded.
        if ability.get_property("bIsActive"): ability.call_function("K2_EndAbility")
    finally:
        ability.set_property(GUARD, False)


def finished(ability):
    _stats["waits_finished"] += 1
    ability.call_function("K2_EndAbility")


def activate(ability, event):
    close(ability)
    ability._uep_death_scope = SubscriptionScope()
    _stats["activations"] += 1; _stats["scopes_created"] += 1
    _active[id(ability)] = ability.get_path_name()
    try:
        ability.call_function("SetCameraMode", ability.get_property("Camera Mode")); _stats["cameras_set"] += 1
        # Match every original MakeGameplayCueParameters pin. Use the native
        # builder so context handles and quantized vectors remain native values.
        params = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function(
            "MakeGameplayCueParameters", event.EventMagnitude, event.EventMagnitude, event.ContextHandle,
            event.EventTag, event.EventTag, event.InstigatorTags, event.TargetTags,
            ue.FVector(0., 0., 0.), ue.FVector(0., 0., 0.), event.Instigator, None, event.Target, None, 1, 1, None, False)
        ability.call_function("K2_ExecuteGameplayCueWithParams", GameplayTag(TagName="GameplayCue.Character.Death"), params)
        _stats["cues_executed"] += 1
        task = ue.find_class("AbilityTask_WaitDelay").get_cdo().call_function("WaitDelay", ability, ability.Duration)
        ability._uep_death_wait = task; _stats["waits_created"] += 1
        ability._uep_death_scope.bind_event(task, "OnFinish", lambda: finished(ability))
        task.call_function("ReadyForActivation")
    except Exception as error:
        _stats["errors"].append(str(error)); end_for_teardown(ability); raise


class LyraDeathPythonProfile:
    def __init__(self):
        self._uep_death_scope = self._uep_death_wait = None

    def K2_ActivateAbilityFromEvent(self, EventData):
        activate(self, EventData)

    def NativeEnded(self, bWasCancelled):
        close(self); _stats["native_ends"] += 1
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        end_for_teardown(self)


class LyraDeathBlueprintFallbackProfile:
    def K2_ActivateAbilityFromEvent(self, EventData):
        self.call_mixin_original("K2_ActivateAbilityFromEvent", EventData)

    def NativeEnded(self, bWasCancelled):
        self.call_mixin_original(NATIVE_END, bWasCancelled)
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        self.set_property(GUARD, True)
        try:
            if self.get_property("bIsActive"): self.call_function("K2_EndAbility")
        finally:
            self.set_property(GUARD, False)
