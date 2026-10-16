"""Emote choices in Python; native GAS/montage/character movement remain."""
import copy

import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from . import widget_lifecycle as widgets

CLASS = "/ShooterCore/Game/Emote/GA_Emote.GA_Emote_C"
ACTIVATE, MOVEMENT, NATIVE_END = "UEPEmoteActivateGate", "UEPEmoteMovementGate", "UEPEmoteNativeEndGate"
GUARD, REMOVE = "UEPEmoteTearingDown", "UEPRemoveOriginalEmoteBinding"
_active, _instances = {}, {}
_stats = dict(activations=0, scopes_created=0, scopes_closed=0, tasks_created=0,
    movement_checks=0, movement_stops=0, uncrouches=0, native_ends=0,
    montage_completed=0, montage_interrupted=0, montage_cancelled=0,
    fallback_activations=0, fallback_movement_checks=0, fallback_native_ends=0,
    widget_added=0, widget_removed=0, original_bindings_removed=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def instance_snapshot(ability):
    return dict({key: 0 for key, value in _stats.items() if type(value) is int}, **_instances.get(ability.get_path_name(), {}))


def note(ability, key):
    _stats[key] += 1
    counts = _instances.setdefault(ability.get_path_name(), {})
    counts[key] = counts.get(key, 0) + 1
    while len(_instances) > 256:
        _instances.pop(next(iter(_instances)))


def close_movement(ability):
    scope, ability._uep_emote_movement = ability._uep_emote_movement, None
    if scope is not None:
        scope.close(); note(ability, "scopes_closed")


def close(ability):
    close_movement(ability)
    scope, ability._uep_emote_tasks = ability._uep_emote_tasks, None
    _active.pop(id(ability), None)
    if scope is not None:
        scope.close(); note(ability, "scopes_closed")


def completed(ability, kind):
    note(ability, kind)
    ability.call_function("K2_EndAbility")


def activate(ability):
    close(ability)
    character = ability.call_function("GetLyraCharacterFromActorInfo")
    if not valid(character):
        raise RuntimeError("Emote requires its native Lyra Character")
    scope = SubscriptionScope()
    ability._uep_emote_tasks = scope
    _active[id(ability)] = ability.get_path_name()
    note(ability, "activations"); note(ability, "scopes_created")
    try:
        if character.get_property("bIsCrouched"):
            character.call_function("UnCrouch", False); note(ability, "uncrouches")
        montage = ue.find_class("AbilityTask_PlayMontageAndWait").get_cdo().call_function(
            "CreatePlayMontageAndWaitProxy", OwningAbility=ability, TaskInstanceName="None",
            MontageToPlay=ability.get_property("Montage to Play"), Rate=1., StartSection="None",
            bStopWhenAbilityEnds=True, AnimRootMotionTranslationScale=1., StartTimeSeconds=0.,
            bAllowInterruptAfterBlendOut=False)
        if not valid(montage):
            raise RuntimeError("native Emote montage task creation failed")
        note(ability, "tasks_created")
        for event, kind in (("OnCompleted", "montage_completed"), ("OnInterrupted", "montage_interrupted"), ("OnCancelled", "montage_cancelled")):
            scope.bind_event(montage, event, lambda kind=kind: completed(ability, kind))
        montage.call_function("ReadyForActivation")
        # Native task activation may synchronously fail/end. Never bind a new
        # movement listener after that native End has already closed the scope.
        if ability.get_property("bIsActive"):
            movement = SubscriptionScope()
            ability._uep_emote_movement = movement
            note(ability, "scopes_created")
            movement.bind_event(character, "OnCharacterMovementUpdated", lambda delta, old_location, old_velocity:
                ability.call_function("CheckForMovement", delta, old_location, old_velocity))
    except Exception as error:
        _stats["errors"] = (_stats["errors"] + [str(error)])[-16:]
        teardown(ability)
        raise


def check_movement(ability, old_velocity):
    note(ability, "movement_checks")
    character = ability.call_function("GetLyraCharacterFromActorInfo")
    length = ue.find_class("KismetMathLibrary").get_cdo().call_function("VSize", old_velocity)
    if float(length) > 0. or bool(character.get_property("bIsCrouched")):
        # Keep montage interruption subscribed until the native stop actually
        # ends it. Only this movement listener is removed; no ClearAll call.
        close_movement(ability)
        note(ability, "movement_stops")
        character.call_function("StopAnimMontage", ability.get_property("Montage to Play"))


def remove_original_binding(ability):
    character = ability.call_function("GetLyraCharacterFromActorInfo")
    if valid(character):
        ability.call_function(REMOVE, character)
        note(ability, "original_bindings_removed")


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        # Exact ability+CheckForMovement dynamic delegate, including a previous
        # original-BP activation. Not another ability or a foreign subscriber.
        remove_original_binding(ability)
        if ability.get_property("bIsActive"):
            ability.call_function("K2_EndAbility")
    finally:
        ability.set_property(GUARD, False)


class LyraEmotePythonProfile:
    def __init__(self):
        self._uep_emote_tasks, self._uep_emote_movement = None, None

    def K2_ActivateAbility(self):
        activate(self); return False
    K2_ActivateAbility.override = ACTIVATE

    def CheckForMovement(self, DeltaSeconds, OldLocation, OldVelocity):
        check_movement(self, OldVelocity); return False
    CheckForMovement.override = MOVEMENT

    def NativeEnded(self, bWasCancelled):
        close(self); note(self, "native_ends"); return False
    NativeEnded.override = NATIVE_END

    def K2_OnAbilityAdded(self):
        note(self, "widget_added"); widgets.add_many(self)

    def K2_OnAbilityRemoved(self):
        widgets.remove_many(self); note(self, "widget_removed")

    def __uep_mixin_teardown__(self):
        teardown(self)


class LyraEmoteBlueprintFallbackProfile:
    def __init__(self):
        self._uep_emote_tasks, self._uep_emote_movement = None, None

    def K2_ActivateAbility(self):
        note(self, "fallback_activations"); return True
    K2_ActivateAbility.override = ACTIVATE

    def CheckForMovement(self, DeltaSeconds, OldLocation, OldVelocity):
        note(self, "fallback_movement_checks"); return True
    CheckForMovement.override = MOVEMENT

    def NativeEnded(self, bWasCancelled):
        # Preserve original BP's natural-end listener behavior for comparison.
        # The fixture or an explicit Profile teardown removes that exact binding.
        note(self, "fallback_native_ends"); return True
    NativeEnded.override = NATIVE_END

    def K2_OnAbilityAdded(self):
        widgets.add_many(self)

    def K2_OnAbilityRemoved(self):
        widgets.remove_many(self)

    def __uep_mixin_teardown__(self):
        teardown(self)
