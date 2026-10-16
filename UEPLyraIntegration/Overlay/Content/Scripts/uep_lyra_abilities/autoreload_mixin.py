"""Original auto-reload decisions; native inventory/equipment/GAS/tasks stay native."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayEventData
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/Game/Weapons/GA_Weapon_AutoReload.GA_Weapon_AutoReload_C"
NATIVE_END, GUARD = "UEPAutoReloadNativeEnded", "UEPAutoReloadTearingDown"
MAGAZINE, SPARE = "Lyra.ShooterGame.Weapon.MagazineAmmo", "Lyra.ShooterGame.Weapon.SpareAmmo"
_active = {}
_counts = {}
_stats = dict(activations=0, polls=0, ammo_checks=0, reload_requests=0, tasks_created=0,
    scopes_created=0, scopes_closed=0, native_ends=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def instance_snapshot(ability):
    return dict({key: 0 for key, value in _stats.items() if type(value) is int}, **_counts.get(ability.get_path_name(), {}))


def note(ability, key):
    _stats[key] += 1
    path = ability.get_path_name()
    values = _counts.setdefault(path, {})
    values[key] = values.get(key, 0)+1
    # Metadata only; retain no UObject or ended task. Bound inactive history.
    if len(_counts) > 256:
        active = set(_active.values())
        for old in list(_counts):
            if len(_counts) <= 256: break
            if old not in active and old != path: _counts.pop(old)


def close(ability):
    scope = ability._uep_autoreload_scope
    ability._uep_autoreload_scope = ability._uep_autoreload_wait = None
    _active.pop(id(ability), None)
    if scope is not None: scope.close(); note(ability, "scopes_closed")


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        if ability.get_property("bIsActive"): ability.call_function("K2_CancelAbility")
        if ability.get_property("bIsActive"): raise RuntimeError("native AutoReload refused teardown cancellation")
    finally: ability.set_property(GUARD, False)


def check_ammo(ability):
    note(ability, "ammo_checks")
    item = ability.call_function("GetAssociatedItem")
    if not valid(item): return False
    return (int(item.call_function("GetStatTagStackCount", GameplayTag(TagName=MAGAZINE))) == 0 and
            int(item.call_function("GetStatTagStackCount", GameplayTag(TagName=SPARE))) > 0)


def poll_finished(ability):
    # Each native wait owns one bounded scope, not an ever-growing list of old
    # task wrappers/delegates. Close it before any synchronous GAS reentrancy.
    close(ability); note(ability, "polls")
    if ability.call_function("CheckAmmoState"):
        equipment = ability.call_function("GetAssociatedEquipment")
        if valid(equipment) and equipment.is_a(ue.find_class("LyraWeaponInstance")) and \
                float(equipment.call_function("GetTimeSinceLastInteractedWith")) >= float(ability.TimeSinceActivityToReload):
            avatar = ability.call_function("GetAvatarActorFromActorInfo")
            reloading = valid(avatar) and ue.find_class("BlueprintGameplayTagLibrary").get_cdo().call_function(
                "DoesTagAssetInterfaceHaveTag", avatar, GameplayTag(TagName="Event.Movement.Reload"))
            if not reloading:
                ability.call_function("SendGameplayEvent", GameplayTag(TagName="InputTag.Weapon.Reload"), GameplayEventData())
                note(ability, "reload_requests")
    if ability.get_property("bIsActive"): ability.call_function("PeriodicCheck")


def periodic(ability):
    if not ability.get_property("bIsActive"): return
    close(ability)
    scope = SubscriptionScope(); ability._uep_autoreload_scope = scope
    note(ability, "scopes_created"); _active[id(ability)] = ability.get_path_name()
    try:
        task = ue.find_class("AbilityTask_WaitDelay").get_cdo().call_function("WaitDelay", ability, ability.PollInterval)
        ability._uep_autoreload_wait = task; note(ability, "tasks_created")
        scope.bind_event(task, "OnFinish", lambda: poll_finished(ability))
        task.call_function("ReadyForActivation")
    except Exception as error:
        _stats["errors"].append(str(error)); teardown(ability); raise


class LyraAutoReloadPythonProfile:
    def __init__(self): self._uep_autoreload_scope = self._uep_autoreload_wait = None

    def K2_ActivateAbility(self):
        note(self, "activations")
        self.call_function("PeriodicCheck")

    def CheckAmmoState(self): return check_ammo(self)

    def PeriodicCheck(self): periodic(self)

    def NativeEnded(self, bWasCancelled):
        close(self); note(self, "native_ends")
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self): teardown(self)


class LyraAutoReloadBlueprintFallbackProfile:
    def K2_ActivateAbility(self): self.call_mixin_original("K2_ActivateAbility")
    def CheckAmmoState(self): return self.call_mixin_original("CheckAmmoState")
    def PeriodicCheck(self): self.call_mixin_original("PeriodicCheck")

    def NativeEnded(self, bWasCancelled): self.call_mixin_original(NATIVE_END, bWasCancelled)
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self):
        self.set_property(GUARD, True)
        try:
            if self.get_property("bIsActive"): self.call_function("K2_CancelAbility")
            if self.get_property("bIsActive"): raise RuntimeError("native original AutoReload refused teardown cancellation")
        finally: self.set_property(GUARD, False)
