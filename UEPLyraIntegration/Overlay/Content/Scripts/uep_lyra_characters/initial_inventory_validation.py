"""Actual typed BP loadout calls; protect originals with native-only fixture undo."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import services, path
from .quickbar_input_validation import fingerprint
from . import initial_inventory_mixin as policy
from .initial_inventory_contract import CLASS, PLAN, require, validate, natural_grant

PROBE = "/Game/UEPValidation/BP_CharacterLoadoutCallProbe.BP_CharacterLoadoutCallProbe_C"


def state(controller):
    inventory, quickbar = services(controller)
    item = quickbar.call_function("GetActiveSlotItem"); pawn = controller.get_controlled_pawn()
    equipment = pawn.get_component_by_type(ue.find_class("LyraEquipmentManagerComponent"))
    weapons = [value for value in equipment.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance")) if valid(value)]
    require(len(weapons) == int(valid(item)) and (not weapons or weapons[0].call_function("GetInstigator") == item), "native loadout equipment/active item differs")
    items = inventory.call_function("GetAllItems")
    return dict(items=sorted(path(value.ItemDef) for value in items), slots=[path(value.ItemDef) if valid(value) else None for value in quickbar.call_function("GetSlots")],
        active=int(quickbar.call_function("GetActiveSlotIndex")), definition=path(item.ItemDef) if valid(item) else None,
        equipment_class=path(weapons[0].get_class()) if weapons else None,
        stacks=sorted([[path(entry.Instance.ItemDef), int(entry.StackCount)] for entry in inventory.get_property("InventoryList").Entries]))


class Trial:
    probe_path = PROBE
    def __init__(self, controller):
        self.controller = controller; self.pawn = controller.get_controlled_pawn()
        self.inventory, self.quickbar = services(controller); self.probe = ue.load_class(self.probe_path).get_cdo()
        self.original, self.original_model = fingerprint(controller), state(controller)
        self.original_items = list(self.inventory.call_function("GetAllItems")); self.original_slots = list(self.quickbar.call_function("GetSlots"))
        self.profile, self.configuration = str(ue.get_mixin_profile(self.pawn)), list(self.pawn.get_property("InitialInventoryItems"))
        self.cdo = self.pawn.get_class().get_cdo(); self.cdo_before = self.cdo_state()
        self.audio = path(self.pawn.Emote_AudioComponent)

    def cdo_state(self): return (str(ue.get_mixin_profile(self.cdo)), [path(value) for value in self.cdo.get_property("InitialInventoryItems")], path(self.cdo.Emote_AudioComponent))

    def execute(self, index):
        name, profile, definitions, occupied = PLAN[index]
        for slot in range(len(self.quickbar.call_function("GetSlots"))):
            if not (occupied and slot == 0): self.quickbar.call_function("RemoveItemFromSlot", slot)
        self.pawn.set_property("InitialInventoryItems", [ue.load_class(value) for value in definitions]); ue.set_mixin_profile(self.pawn, profile)
        before = copy.deepcopy(policy.evidence(self.pawn)); self.probe.call_function("Grant", self.pawn)
        after = policy.evidence(self.pawn)
        added = [dict(path=path(value), definition=path(value.ItemDef)) for value in self.inventory.call_function("GetAllItems") if path(value) not in self.original["items"]]
        self.row = dict(name=name, profile=profile, configured_definitions=list(definitions), occupied_first=occupied,
            bp_reference_call=True, native_character_class=self.pawn.get_class().get_path_name(), native_model=state(self.controller), added_items=added,
            original_item_retained=all(value in self.inventory.call_function("GetAllItems") for value in self.original_items),
            new_items_are_new_identities=all(item["path"] not in self.original["items"] for item in added),
            counters={key: after[key]-before[key] for key in after if key != "last_call"})
        return self.row

    def restore(self):
        for index in range(len(self.quickbar.call_function("GetSlots"))): self.quickbar.call_function("RemoveItemFromSlot", index)
        for item in list(self.inventory.call_function("GetAllItems")):
            if path(item) not in self.original["items"]: self.inventory.call_function("RemoveItemInstance", item)
        for index, item in enumerate(self.original_slots):
            if valid(item): self.quickbar.call_function("AddItemToSlot", index, item)
        self.quickbar.call_function("SetActiveSlotIndex", self.original["active"])
        self.pawn.set_property("InitialInventoryItems", self.configuration); ue.set_mixin_profile(self.pawn, self.profile)
        restored = fingerprint(self.controller) == self.original and state(self.controller) == self.original_model
        fields = str(ue.get_mixin_profile(self.pawn)) == self.profile and list(self.pawn.get_property("InitialInventoryItems")) == self.configuration and self.cdo_state() == self.cdo_before and path(self.pawn.Emote_AudioComponent) == self.audio
        require(restored and fields, "loadout native undo did not restore original identity/configuration/CDO")
        return dict(original_inventory_identities_restored=restored, configuration_profile_cdo_restored=fields)


class Validation(Ready):
    trial_type = Trial
    marker = "UEP_CHARACTER_LOADOUT"
    validate_report = staticmethod(validate)
    def __init__(self, result):
        super().__init__(result); self.trial = None
        self.report.update(inventory_properties_written=False, python_handler_replayed=False, whole_character_migrated=False,
            full_acceptance=False, replication_tested=False, fixture_configuration_overrides=True,
            original_inventory_identities_restored=False, configuration_profile_cdo_restored=False)

    def begin(self):
        if self.trial is None:
            self.report["natural_startup_python_grant"] = copy.deepcopy(policy.evidence(self.pawn))
            natural_grant(self.report["natural_startup_python_grant"])
            self.trial = self.trial_type(self.controller)
        self.trial.execute(self.index); self.enter("observe")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240, "loadout native fixture timeout")
            if self.phase == "ready": self.ready()
            elif self.phase == "observe" and time.monotonic()-self.phase_started >= .1:
                require(state(self.controller) == self.trial.row["native_model"], "native loadout state changed before observation")
                self.trial.row.update(self.trial.restore()); self.report["cases"].append(copy.deepcopy(self.trial.row))
                ue.log(self.marker+"_CASE_PASSED "+PLAN[self.index][0]+"/"+PLAN[self.index][1])
                self.index += 1
                if self.index == len(PLAN): self.finish()
                else: self.begin()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if self.trial is not None: self.report.update(self.trial.restore())
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)(self.marker+"_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; self.validate_report(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)(self.marker+"_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterLoadoutResult=")), None)
if result and "-UEPCharacterLoadoutNatural" not in sys.argv:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
