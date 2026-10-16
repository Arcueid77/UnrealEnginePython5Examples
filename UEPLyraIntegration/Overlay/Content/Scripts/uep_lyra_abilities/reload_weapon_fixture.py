"""Test-only native equipment fixture; remove only the temporary owned item."""
import unreal_engine as ue
from uep_lyra_world.inventory_pad_network_state import capture, services, path
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from .quickslot_network_validation import fingerprint
from .reload_magazine_contract import require, WEAPONS
AUTO = "/Game/Weapons/GA_Weapon_AutoReload.GA_Weapon_AutoReload_C"


def auto_instances(controller):
    _, quickbar = services(controller)
    item, asc = quickbar.call_function("GetActiveSlotItem"), ability_system(controller.get_controlled_pawn())
    cls = ue.load_class(AUTO)
    return [value for spec in asc.get_property("ActivatableAbilities").Items if valid(spec.Ability) and spec.Ability.get_class() == cls
        for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances)
        if valid(value) and value.call_function("GetAssociatedItem") == item]


def auto_state(controller):
    matches = auto_instances(controller)
    return bool(matches[0].get_property("bIsActive")) if len(matches) == 1 else None


def auto_active(controller):
    value = auto_state(controller)
    require(value is not None, "original equipped weapon AutoReload grant differs")
    return value


def baseline(controller):
    model, raw = capture(controller), fingerprint(controller)
    require(model is not None and "ID_Pistol" in model["definition"] and len(raw["items"]) == 1 and
        raw["active"] == 0 and raw["slots"][1:] == [None, None], "do not overwrite non-original weapon inventory")
    return dict(original_model=model, original_inventory=raw, original_auto_active=auto_active(controller))


def install(controller, weapon):
    require(int(controller.call_function("GetLocalRole")) == 3 and weapon in WEAPONS and WEAPONS[weapon][1] is not None, "native authority-only weapon fixture required")
    state = baseline(controller)
    inventory, quickbar = services(controller)
    slot = int(quickbar.call_function("GetNextFreeItemSlot"))
    require(slot > 0, "temporary weapon fixture has no spare slot")
    item = inventory.call_function("AddItemDefinition", ue.load_class(WEAPONS[weapon][1]), 1)
    require(valid(item), "native temporary weapon grant failed")
    state.update(owned_item=path(item), slot=slot, weapon=weapon)
    quickbar.call_function("AddItemToSlot", slot, item)
    quickbar.call_function("SetActiveSlotIndex", slot)
    return state


def restore(controller, state):
    require(int(controller.call_function("GetLocalRole")) == 3, "client must not restore inventory through writes")
    inventory, quickbar = services(controller)
    quickbar.call_function("SetActiveSlotIndex", state["original_inventory"]["active"])
    slots = quickbar.call_function("GetSlots")
    item = slots[state["slot"]]
    if valid(item):
        require(path(item) == state["owned_item"], "do not remove a foreign replacement from the temporary weapon slot")
        quickbar.call_function("RemoveItemFromSlot", state["slot"])
    for item in inventory.call_function("GetAllItems"):
        if path(item) == state["owned_item"]: inventory.call_function("RemoveItemInstance", item)
    require(restored(controller, state), "native temporary weapon restore differs from original pistol inventory")


def restored(controller, state):
    return fingerprint(controller) == state["original_inventory"] and capture(controller) == state["original_model"] and auto_active(controller) == state["original_auto_active"]
