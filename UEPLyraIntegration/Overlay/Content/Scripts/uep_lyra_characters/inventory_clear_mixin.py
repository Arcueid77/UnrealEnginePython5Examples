"""Character-owned inventory decisions; QuickBar/inventory/replication stay native."""
import copy
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin_C"


def components(controller):
    if not valid(controller): return None, None
    return tuple(controller.call_function("GetComponentByClass", ue.find_class(name))
        for name in ("LyraQuickBarComponent", "LyraInventoryManagerComponent"))


def inventory_state(controller):
    quick, inventory = components(controller)
    items = list(inventory.call_function("GetAllItems")) if valid(inventory) else []
    return dict(controller_valid=valid(controller), quickbar_valid=valid(quick), inventory_valid=valid(inventory),
        slots=[item.get_path_name() if valid(item) else None for item in quick.call_function("GetSlots")] if valid(quick) else [],
        active=int(quick.call_function("GetActiveSlotIndex")) if valid(quick) else -1,
        items=[dict(path=item.get_path_name(), definition=definition.get_path_name() if valid(definition) else None)
            for item in items if valid(item) for definition in (item.get_property("ItemDef"),)])


def evidence(actor):
    # Keep only one POD snapshot and counters per Actor. A fixture may retain
    # this dict through native Actor GC without retaining/dereferencing a UObject.
    value = getattr(actor, "_uep_character_clear_evidence", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, authority_noops=0, missing_controller_noops=0,
            missing_quickbar_noops=0, missing_inventory_noops=0, slots_removed=0, items_removed=0, last_call=None)
        actor._uep_character_clear_evidence = value
    return value


def context(actor, profile):
    controller = actor.call_function("GetController")
    return controller, dict(profile=profile, actor=actor.get_path_name(), authority=bool(actor.call_function("HasAuthority")),
        native_role=int(actor.call_function("GetLocalRole")), before=inventory_state(controller))


def finish(value, row, controller):
    row["after"] = inventory_state(controller)
    value["last_call"] = copy.deepcopy(row)


class LyraCharacterInventoryPythonProfile:
    def ClearInventory(self):
        value = evidence(self); value["python_calls"] += 1
        controller, row = context(self, "Python")
        if not row["authority"]: value["authority_noops"] += 1
        elif not valid(controller): value["missing_controller_noops"] += 1
        else:
            quick, inventory = components(controller)
            if not valid(quick): value["missing_quickbar_noops"] += 1
            else:
                # Original Sequence order: every slot, then a copied item list.
                for index in range(len(quick.call_function("GetSlots"))):
                    quick.call_function("RemoveItemFromSlot", index); value["slots_removed"] += 1
                if valid(inventory):
                    for item in list(inventory.call_function("GetAllItems")):
                        inventory.call_function("RemoveItemInstance", item); value["items_removed"] += 1
                else: value["missing_inventory_noops"] += 1
        finish(value, row, controller)


class LyraCharacterInventoryBlueprintFallbackProfile:
    def ClearInventory(self):
        value = evidence(self); value["fallback_calls"] += 1
        controller, row = context(self, "BlueprintFallback")
        self.call_mixin_original("ClearInventory")
        finish(value, row, controller)
