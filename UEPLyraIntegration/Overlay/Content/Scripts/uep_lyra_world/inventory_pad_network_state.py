"""Read native owner inventory/equipment; no property or stat writes."""
import unreal_engine as ue
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_hud.ammo_mixin import _stat, MAGAZINE_AMMO, SPARE_AMMO


def path(value):
    return value.get_path_name() if valid(value) else None


def services(controller):
    return tuple(controller.get_component_by_type(ue.find_class(name)) for name in
                 ("LyraInventoryManagerComponent", "LyraQuickBarComponent"))


def capture(controller):
    if not valid(controller):
        return None
    inventory, quickbar = services(controller)
    pawn = controller.get_controlled_pawn()
    if not all(valid(value) for value in (inventory, quickbar, pawn)):
        return None
    item = quickbar.call_function("GetActiveSlotItem")
    items, slots = inventory.call_function("GetAllItems"), quickbar.call_function("GetSlots")
    if not valid(item) or not valid(item.ItemDef) or any(not valid(value) or not valid(value.ItemDef) for value in items):
        return None
    equipment = pawn.get_component_by_type(ue.find_class("LyraEquipmentManagerComponent"))
    if not valid(equipment):
        return None
    matches = [value for value in equipment.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance"))
               if valid(value) and value.call_function("GetInstigator") == item]
    if len(matches) != 1:
        return None
    return {"items": sorted(path(value.ItemDef) for value in items),
            "slots": [path(value.ItemDef) if valid(value) else None for value in slots],
            "active": int(quickbar.call_function("GetActiveSlotIndex")), "definition": path(item.ItemDef),
            "magazine": int(_stat(item, MAGAZINE_AMMO)), "spare": int(_stat(item, SPARE_AMMO)),
            "equipment_class": path(matches[0].get_class()), "equipment_instigator_matches": True}
