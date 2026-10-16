"""Hero Heal BP decisions; native GAS effect, montage/state/input tasks remain."""
import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/Game/Characters/Heroes/Abilities/GA_Hero_Heal.GA_Hero_Heal_C"
NATIVE_END, GUARD = "UEPHeroHealNativeEnded", "UEPHeroHealTearingDown"
_active = {}
_stats = dict(activations=0, tasks_created=0, scopes_created=0, scopes_closed=0, native_ends=0,
    effects_applied=0, effects_removed=0, movement_locks=0, movement_unlocks=0,
    state_ends=0, state_interrupts=0, montage_blends=0, montage_interrupts=0,
    montage_cancels=0, input_presses=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def close(ability):
    scope = ability._uep_hero_heal_scope
    ability._uep_hero_heal_scope = None
    _active.pop(id(ability), None)
    if scope is not None: scope.close(); _stats["scopes_closed"] += 1


def cleanup(ability):
    if not ability._uep_hero_heal_effects_live: return
    ability._uep_hero_heal_effects_live = False
    controller = ability.call_function("GetControllerFromActorInfo")
    if valid(controller): controller.call_function("SetIgnoreMoveInput", False)
    _stats["movement_unlocks"] += 1
    asc = ability.call_function("GetLyraAbilitySystemComponentFromActorInfo")
    if valid(asc):
        # Preserve the original disconnected InstigatorAbilitySystemComponent
        # pin (None) and StacksToRemove -1; never clear foreign effects by handle.
        asc.call_function("RemoveActiveGameplayEffectBySourceEffect", ability.GE_Heal, None, -1)
        _stats["effects_removed"] += 1


def task(ability, class_name, factory, *args, **kwargs):
    value = ue.find_class(class_name).get_cdo().call_function(factory, *args, **kwargs)
    if not valid(value): raise RuntimeError("Hero Heal native task factory failed: "+class_name)
    _stats["tasks_created"] += 1
    return value


def state_finished(ability, reason):
    _stats[reason] += 1
    cleanup(ability)


def request_end(ability, reason):
    _stats[reason] += 1
    ability.call_function("K2_EndAbility")


def activate(ability):
    close(ability)
    scope = SubscriptionScope(); ability._uep_hero_heal_scope = scope
    _active[id(ability)] = ability.get_path_name()
    _stats["activations"] += 1; _stats["scopes_created"] += 1
    try:
        state = task(ability, "AbilityTask_StartAbilityState", "StartAbilityState", ability, "HealAbility", True)
        for name, reason in (("OnStateEnded", "state_ends"), ("OnStateInterrupted", "state_interrupts")):
            scope.bind_event(state, name, lambda cause=reason: state_finished(ability, cause))
        state.call_function("ReadyForActivation")
        ability.call_function("GetControllerFromActorInfo").call_function("SetIgnoreMoveInput", True)
        ability._uep_hero_heal_effects_live = True; _stats["movement_locks"] += 1
        montage = task(ability, "AbilityTask_PlayMontageAndWait", "CreatePlayMontageAndWaitProxy",
            OwningAbility=ability, TaskInstanceName="None", MontageToPlay=ability.HealMontage,
            Rate=1., StartSection="None", bStopWhenAbilityEnds=True, AnimRootMotionTranslationScale=1.,
            StartTimeSeconds=0., bAllowInterruptAfterBlendOut=False)
        for name, reason in (("OnBlendOut", "montage_blends"), ("OnInterrupted", "montage_interrupts"), ("OnCancelled", "montage_cancels")):
            scope.bind_event(montage, name, lambda cause=reason: request_end(ability, cause))
        montage.call_function("ReadyForActivation")
        ability.call_function("BP_ApplyGameplayEffectToOwner", ability.GE_Heal, 1, 1)
        _stats["effects_applied"] += 1
        pressed = task(ability, "AbilityTask_WaitInputPress", "WaitInputPress", ability, False)
        scope.bind_event(pressed, "OnPress", lambda elapsed: request_end(ability, "input_presses"))
        pressed.call_function("ReadyForActivation")
        ue.find_class("KismetSystemLibrary").get_cdo().call_function("PrintString", ability, "HEAL", True, True,
            ue.FLinearColor(0., .66, 1., 1.), 2., "None")
    except Exception as error:
        _stats["errors"].append(str(error)); teardown(ability); raise


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        if ability.get_property("bIsActive"):
            cleanup(ability)
            ability.call_function("K2_EndAbility")
    finally: ability.set_property(GUARD, False)


class LyraHeroHealPythonProfile:
    def __init__(self):
        self._uep_hero_heal_scope, self._uep_hero_heal_effects_live = None, False

    def K2_ActivateAbility(self): activate(self)

    def NativeEnded(self, bWasCancelled):
        close(self); cleanup(self); _stats["native_ends"] += 1
        return False  # Typed gate suppresses retained original BP cleanup.
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self): teardown(self)


class LyraHeroHealBlueprintFallbackProfile:
    def __init__(self):
        self._uep_hero_heal_scope, self._uep_hero_heal_effects_live = None, False

    def K2_ActivateAbility(self):
        self._uep_hero_heal_effects_live = True
        self.call_mixin_original("K2_ActivateAbility")

    def NativeEnded(self, bWasCancelled):
        self._uep_hero_heal_effects_live = False
        return self.call_mixin_original(NATIVE_END, bWasCancelled)
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self): teardown(self)
