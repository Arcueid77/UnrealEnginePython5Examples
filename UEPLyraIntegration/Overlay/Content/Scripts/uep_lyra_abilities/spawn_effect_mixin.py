"""Spawn BP decisions; native GAS, animation, world timers and effects remain."""
import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/ShooterCore/Game/Respawn/GA_SpawnEffect.GA_SpawnEffect_C"
EFFECT = "/ShooterCore/Game/Respawn/GE_SpawnIn.GE_SpawnIn_C"
NATIVE_END, GUARD = "UEPSpawnEffectNativeEnded", "UEPSpawnEffectTearingDown"
_active = {}
_instances = {}
_stats = dict(activations=0, scopes_created=0, scopes_closed=0, tasks_created=0, native_ends=0,
    effects_applied=0, effects_removed=0, movement_locks=0, movement_unlocks=0,
    duration_finished=0, input_delay_finished=0, montage_completed=0,
    enable_requests=0, fallback_activations=0, fallback_native_ends=0, errors=[])


def snapshot(): return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def instance_snapshot(ability):
    return dict({key: 0 for key, value in _stats.items() if type(value) is int}, **_instances.get(ability.get_path_name(), {}))


def note(ability, key):
    _stats[key] += 1
    counts = _instances.setdefault(ability.get_path_name(), {}); counts[key] = counts.get(key, 0)+1
    while len(_instances) > 256: _instances.pop(next(iter(_instances)))


def close(ability):
    scope = ability._uep_spawn_scope; ability._uep_spawn_scope = None
    _active.pop(id(ability), None)
    if scope is not None: scope.close(); note(ability, "scopes_closed")


def disable_input(ability):
    controller = ability.CachedController
    if not valid(controller): raise RuntimeError("SpawnEffect requires its original native controller")
    controller.call_function("SetIgnoreMoveInput", True)
    ability._uep_spawn_input_live = True; note(ability, "movement_locks")


def enable_input(ability):
    if not ability._uep_spawn_input_live: return
    ability._uep_spawn_input_live = False
    controller = ability.CachedController
    if valid(controller): controller.call_function("SetIgnoreMoveInput", False)
    note(ability, "movement_unlocks")


def cleanup(ability, routed=True):
    if ability._uep_spawn_effect_live:
        ability._uep_spawn_effect_live = False
        ability.call_function("BP_RemoveGameplayEffectFromOwnerWithHandle", ability.SpawnInGE_Spec, -1)
        note(ability, "effects_removed")
    if routed: ability.call_function("EnableInputAgain")
    else: enable_input(ability)


def task(ability, cls, factory, *args, **kwargs):
    value = ue.find_class(cls).get_cdo().call_function(factory, *args, **kwargs)
    if not valid(value): raise RuntimeError("SpawnEffect native task creation failed: "+cls)
    note(ability, "tasks_created")
    return value


def ended(ability, reason):
    note(ability, reason); ability.call_function("K2_EndAbility")


def input_ready(ability):
    note(ability, "input_delay_finished"); ability.call_function("EnableInputAgain")


def activate(ability):
    close(ability)
    scope = SubscriptionScope(); ability._uep_spawn_scope = scope
    _active[id(ability)] = ability.get_path_name()
    note(ability, "activations"); note(ability, "scopes_created")
    try:
        ability.set_property("CachedController", ability.call_function("GetControllerFromActorInfo"))
        asc = ability.call_function("GetAbilitySystemComponentFromActorInfo")
        # Original BP Level pin is zero, not one. Keep the exact native context.
        handle = asc.call_function("BP_ApplyGameplayEffectToSelf", ue.load_class(EFFECT), 0., asc.call_function("MakeEffectContext"))
        ability.set_property("SpawnInGE_Spec", handle)
        ability._uep_spawn_effect_live = True; note(ability, "effects_applied")
        ability.call_function("DisableInput")
        duration = float(ability.SpawnMontage.call_function("GetPlayLength"))
        complete = task(ability, "AbilityTask_WaitDelay", "WaitDelay", ability, duration)
        scope.bind_event(complete, "OnFinish", lambda: ended(ability, "duration_finished")); complete.call_function("ReadyForActivation")
        release = task(ability, "AbilityTask_WaitDelay", "WaitDelay", ability, duration*float(ability.EnableInputAfterTimeFraction))
        scope.bind_event(release, "OnFinish", lambda: input_ready(ability)); release.call_function("ReadyForActivation")
        montage = task(ability, "AbilityTask_PlayMontageAndWait", "CreatePlayMontageAndWaitProxy",
            OwningAbility=ability, TaskInstanceName="None", MontageToPlay=ability.SpawnMontage, Rate=1., StartSection="None",
            bStopWhenAbilityEnds=False, AnimRootMotionTranslationScale=1., StartTimeSeconds=0., bAllowInterruptAfterBlendOut=False)
        # Original interrupt/cancel outputs are disconnected: timer still ends it.
        scope.bind_event(montage, "OnCompleted", lambda: ended(ability, "montage_completed")); montage.call_function("ReadyForActivation")
    except Exception as error:
        _stats["errors"].append(str(error)); teardown(ability); raise


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        if ability.get_property("bIsActive"):
            cleanup(ability, routed=False); ability.call_function("K2_EndAbility")
    finally: ability.set_property(GUARD, False)


class LyraSpawnEffectPythonProfile:
    def __init__(self): self._uep_spawn_scope, self._uep_spawn_effect_live, self._uep_spawn_input_live = None, False, False
    def K2_ActivateAbility(self): activate(self)
    def DisableInput(self): disable_input(self)
    def EnableInputAgain(self): note(self, "enable_requests"); enable_input(self)
    def NativeEnded(self, bWasCancelled):
        close(self); cleanup(self); note(self, "native_ends")
        return False
    NativeEnded.override = NATIVE_END
    def __uep_mixin_teardown__(self): teardown(self)


class LyraSpawnEffectBlueprintFallbackProfile:
    def __init__(self): self._uep_spawn_scope, self._uep_spawn_effect_live, self._uep_spawn_input_live = None, False, False
    def K2_ActivateAbility(self):
        self._uep_spawn_effect_live = True; note(self, "fallback_activations")
        self.call_mixin_original("K2_ActivateAbility")
    def DisableInput(self):
        self.call_mixin_original("DisableInput"); self._uep_spawn_input_live = True
    def EnableInputAgain(self):
        self.call_mixin_original("EnableInputAgain"); self._uep_spawn_input_live = False
    def NativeEnded(self, bWasCancelled):
        self._uep_spawn_effect_live = False; note(self, "fallback_native_ends")
        return True
    NativeEnded.override = NATIVE_END
    def __uep_mixin_teardown__(self): teardown(self)
