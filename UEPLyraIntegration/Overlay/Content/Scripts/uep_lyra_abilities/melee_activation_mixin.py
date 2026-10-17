"""Melee native activation/equipment/montage lifecycle; original authority trace body."""
import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from .melee_hit_montage_mixin import LyraMeleeHitMontagePythonProfile, LyraMeleeHitMontageBlueprintFallbackProfile

TRACE, ENDED, GUARD = "UEPMeleeAuthorityTrace", "UEPMeleeNativeEnded", "UEPMeleeTearingDown"
WEAPON = "/ShooterCore/Weapons/B_WeaponInstance_Base.B_WeaponInstance_Base_C"
_active, _instances = {}, {}
_stats = dict(activations=0, fallback_activations=0, commits=0, cast_failed=0, montage_tasks=0,
    completed=0, blend_out=0, interrupted=0, cancelled=0, authority_trace_entries=0,
    native_ends=0, fallback_native_ends=0, scopes_created=0, scopes_closed=0, errors=[])


def snapshot(): return dict(copy.deepcopy(_stats), active_count=len(_active))
def instance_snapshot(ability): return copy.deepcopy(_instances.get(ability.get_path_name(), {}))
def note(ability, key):
    _stats[key] += 1; values = _instances.setdefault(ability.get_path_name(), {}); values[key] = values.get(key, 0)+1
    while len(_instances) > 256: _instances.pop(next(iter(_instances)))


def close(ability):
    scope = getattr(ability, "_uep_melee_montage_scope", None); ability._uep_melee_montage_scope = None
    _active.pop(id(ability), None)
    if scope is not None: scope.close(); note(ability, "scopes_closed")


def finished(ability, event): note(ability, event); ability.call_function("K2_EndAbility")


def activate(ability):
    note(ability, "activations")
    # Original BP does not branch on Commit's return value.
    ability.call_function("K2_CommitAbility"); note(ability, "commits")
    actor = ability.call_function("GetLyraCharacterFromActorInfo")
    manager = actor.call_function("GetComponentByClass", ue.find_class("LyraEquipmentManagerComponent"))
    values = manager.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance")) if valid(manager) else []
    weapon = values[0] if values else None
    if not valid(weapon) or not weapon.is_a(ue.load_class(WEAPON)):
        note(ability, "cast_failed"); ability.call_function("K2_EndAbility"); return
    scope = SubscriptionScope(); ability._uep_melee_montage_scope = scope
    _active[id(ability)] = ability.get_path_name(); note(ability, "scopes_created")
    try:
        task = ue.find_class("AbilityTask_PlayMontageAndWait").get_cdo().call_function("CreatePlayMontageAndWaitProxy",
            OwningAbility=ability, TaskInstanceName="None", MontageToPlay=weapon.get_property("MeleeAttackMontage"), Rate=1., StartSection="None",
            bStopWhenAbilityEnds=True, AnimRootMotionTranslationScale=1., StartTimeSeconds=0., bAllowInterruptAfterBlendOut=False)
        if not valid(task): raise RuntimeError("native Melee montage task creation failed")
        note(ability, "montage_tasks")
        for event, name in (("OnCompleted", "completed"), ("OnBlendOut", "blend_out"), ("OnInterrupted", "interrupted"), ("OnCancelled", "cancelled")):
            scope.bind_event(task, event, lambda name=name: finished(ability, name))
        task.call_function("ReadyForActivation")
        if ability.call_function("K2_HasAuthority"):
            ability.call_function(TRACE); note(ability, "authority_trace_entries")
    except Exception as error:
        _stats["errors"] = (_stats["errors"]+[str(error)])[-16:]; teardown(ability); raise


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        if ability.get_property("bIsActive"): ability.call_function("K2_EndAbility")
    finally: ability.set_property(GUARD, False)


class LyraMeleeActivationPythonProfile:
    def __init__(self): self._uep_melee_montage_scope = None
    SelectHitMontage = LyraMeleeHitMontagePythonProfile.__dict__["SelectHitMontage"]
    def Activate(self): activate(self)
    Activate.override = "K2_ActivateAbility"
    def NativeEnded(self, bWasCancelled): close(self); note(self, "native_ends"); return False
    NativeEnded.override = ENDED
    def __uep_mixin_teardown__(self): teardown(self)


class LyraMeleeActivationBlueprintFallbackProfile:
    def __init__(self): self._uep_melee_montage_scope = None
    SelectHitMontage = LyraMeleeHitMontageBlueprintFallbackProfile.__dict__["SelectHitMontage"]
    def Activate(self): note(self, "fallback_activations"); return self.call_mixin_original("K2_ActivateAbility")
    Activate.override = "K2_ActivateAbility"
    def NativeEnded(self, bWasCancelled): close(self); note(self, "fallback_native_ends"); return True
    NativeEnded.override = ENDED
    def __uep_mixin_teardown__(self): teardown(self)
