"""Original Character loadout orchestration; native inventory/equipment remain."""
import copy
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .inventory_clear_mixin import components, inventory_state
from .quickbar_input_mixin import LyraCharacterQuickbarPythonProfile as InputPython, LyraCharacterQuickbarBlueprintFallbackProfile as InputBlueprint


def evidence(actor):
    value = getattr(actor, "_uep_character_initial_inventory", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, authority_noops=0, missing_controller_noops=0,
            missing_inventory_noops=0, missing_quickbar_noops=0, grant_calls=0, slot_add_attempts=0,
            slot_zero_requests=0, last_call=None)
        actor._uep_character_initial_inventory = value
    return value


def context(actor, profile):
    authority = bool(actor.call_function("HasAuthority"))
    controller = actor.call_function("GetController") if authority else None
    row = dict(profile=profile, authority=authority, role=int(actor.call_function("GetLocalRole")),
        actor=actor.get_path_name(), configured_definitions=[item.get_path_name() if valid(item) else None for item in actor.get_property("InitialInventoryItems")],
        before=inventory_state(controller) if authority else None)
    return controller, row


def finish(actor, row, controller):
    row["after"] = inventory_state(controller) if row["authority"] else None
    evidence(actor)["last_call"] = copy.deepcopy(row)


class LyraCharacterLoadoutPythonProfile:
    ClearInventory = InputPython.ClearInventory
    GetEmoteAudioComponent = InputPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = InputPython.SetEmoteAudioComponent
    ChangeQuickbarSlot = InputPython.ChangeQuickbarSlot

    def AddInitialInventory(self):
        counts = evidence(self); counts["python_calls"] += 1
        controller, row = context(self, "Python")
        if not row["authority"]: counts["authority_noops"] += 1
        elif not valid(controller): counts["missing_controller_noops"] += 1
        else:
            quickbar, inventory = components(controller)
            if not valid(inventory): counts["missing_inventory_noops"] += 1
            elif not valid(quickbar): counts["missing_quickbar_noops"] += 1
            else:
                definitions = list(self.get_property("InitialInventoryItems"))
                for index, definition in enumerate(definitions):
                    item = inventory.call_function("AddItemDefinition", definition, 1); counts["grant_calls"] += 1
                    quickbar.call_function("AddItemToSlot", index, item); counts["slot_add_attempts"] += 1
                if definitions:
                    quickbar.call_function("SetActiveSlotIndex", 0); counts["slot_zero_requests"] += 1
        finish(self, row, controller)


class LyraCharacterLoadoutBlueprintFallbackProfile:
    ClearInventory = InputBlueprint.ClearInventory
    GetEmoteAudioComponent = InputBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = InputBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = InputBlueprint.ChangeQuickbarSlot

    def AddInitialInventory(self):
        counts = evidence(self); counts["fallback_calls"] += 1
        controller, row = context(self, "BlueprintFallback")
        self.call_mixin_original("AddInitialInventory")
        finish(self, row, controller)
