"""Original DropWeapon decisions; native inventory/Quickbar/equipment/GAS stay."""
import copy
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/ShooterCore/Input/Abilities/GA_DropWeapon.GA_DropWeapon_C"
NATIVE_END, GUARD = "UEPDropWeaponNativeEnded", "UEPDropWeaponTearingDown"
_active = {}
_stats = dict(activations=0, authority_branches=0, client_branches=0, invalid_quickbar=0,
    items_removed=0, cycles=0, native_ends=0, fallback_activations=0, fallback_native_ends=0, errors=[])


def snapshot(): return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def activate(ability):
    _stats["activations"] += 1; _active[id(ability)] = ability.get_path_name()
    try:
        if ability.call_function("K2_HasAuthority"):
            _stats["authority_branches"] += 1
            controller = ability.call_function("GetControllerFromActorInfo")
            quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent")) if valid(controller) else None
            if valid(quickbar):
                slot = quickbar.call_function("GetActiveSlotIndex")
                item = quickbar.call_function("RemoveItemFromSlot", slot)
                inventory = controller.get_component_by_type(ue.find_class("LyraInventoryManagerComponent"))
                inventory.call_function("RemoveItemInstance", item)
                _stats["items_removed"] += int(valid(item))
                quickbar.call_function("CycleActiveSlotForward"); _stats["cycles"] += 1
            else: _stats["invalid_quickbar"] += 1
        else: _stats["client_branches"] += 1
    except Exception as error:
        _stats["errors"].append(str(error)); raise
    finally: ability.call_function("K2_EndAbility")


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        _active.pop(id(ability), None)
        if ability.get_property("bIsActive"): ability.call_function("K2_EndAbility")
    finally: ability.set_property(GUARD, False)


class LyraDropWeaponPythonProfile:
    def K2_ActivateAbility(self): activate(self)
    def NativeEnded(self, bWasCancelled):
        _active.pop(id(self), None); _stats["native_ends"] += 1
    NativeEnded.override = NATIVE_END
    def __uep_mixin_teardown__(self): teardown(self)


class LyraDropWeaponBlueprintFallbackProfile:
    def K2_ActivateAbility(self):
        _stats["fallback_activations"] += 1; self.call_mixin_original("K2_ActivateAbility")
    def NativeEnded(self, bWasCancelled):
        _stats["fallback_native_ends"] += 1; self.call_mixin_original(NATIVE_END, bWasCancelled)
    NativeEnded.override = NATIVE_END
    def __uep_mixin_teardown__(self): teardown(self)
