"""Real DropWeapon input, temporary native items, exact original item restore."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture, services, path
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from .quickslot_network_validation import fingerprint
from . import drop_weapon_mixin as policy
from .drop_weapon_contract import PLAN, require, validate

DEFINITIONS = ("/ShooterCore/Weapons/Rifle/ID_Rifle.ID_Rifle_C", "/ShooterCore/Weapons/Shotgun/ID_Shotgun.ID_Shotgun_C")


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.sides = False, []
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(status="running", error=None, cases=[], original_player_restored=False, fixture_native_authority_inventory_api=True)
        for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
            "ability_activation_called_by_probe", "inventory_or_slots_written_as_properties", "world_pickup_spawned"): self.report[field] = False

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bHealthReady and not snap.bDamageImmune and snap.Health > 0): continue
            controller = self.statics.call_function("GetPlayerController", world, 0); model = capture(controller)
            if model is None or "ID_Pistol" not in model["definition"]: continue
            self.world, self.controller, self.pawn = world, controller, controller.get_controlled_pawn()
            self.inventory, self.quickbar = services(controller)
            self.asc, self.cls = ability_system(self.pawn), ue.load_class(policy.CLASS)
            values = [value for spec in self.asc.get_property("ActivatableAbilities").Items
                if valid(spec.Ability) and spec.Ability.get_class() == self.cls
                for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
            if len(values) != 1: continue
            self.ability, self.original, self.original_model = values[0], fingerprint(controller), model
            self.original_items = set(self.original["items"])
            require(len(self.original_items) == 1 and self.original["active"] == 0 and self.original["slots"][1:] == [None, None],
                "do not overwrite non-default original inventory/slots")
            self.action = ue.load_object(ue.find_class("InputAction"), "/ShooterCore/Input/Actions/IA_DropWeapon.IA_DropWeapon")
            self.begin(); return

    def begin(self):
        self.name, count, self.initial, self.expected = PLAN[self.index//2]
        self.profile = ("BlueprintFallback", "Python")[self.index % 2]
        require((getattr(self, "network_fixture", False) or fingerprint(self.controller) == self.original) and
            not self.ability.get_property("bIsActive"), "DropWeapon original baseline not restored")
        ue.set_mixin_profile(self.ability, self.profile)
        self.prepare_inventory(count, self.initial)
        self.enter("equipment")

    def prepare_inventory(self, count, initial):
        for definition in DEFINITIONS[:count]:
            slot = int(self.quickbar.call_function("GetNextFreeItemSlot"))
            require(slot >= 0, "temporary DropWeapon fixture has no free slot")
            item = self.inventory.call_function("AddItemDefinition", ue.load_class(definition), 1)
            self.quickbar.call_function("AddItemToSlot", slot, item)
        self.quickbar.call_function("SetActiveSlotIndex", initial)

    def equipment(self):
        require(time.monotonic()-self.phase_started < 8., "native DropWeapon fixture equipment timeout")
        if int(self.quickbar.call_function("GetActiveSlotIndex")) != self.initial: return
        slots = self.quickbar.call_function("GetSlots")
        if PLAN[self.index//2][1] > 0 and not valid(slots[self.initial]): return
        if valid(slots[self.initial]) and capture(self.controller) is None: return
        self.removed_path = path(slots[self.initial]); self.before = policy.snapshot()
        self.row = dict(native_type_preserved=self.ability.get_class() == self.cls, input_injections=1)
        # One true frame, then only false. The native ability ends synchronously;
        # repeating held input could delete the original next slot as well.
        self.controller.inject_enhanced_input_for_action(self.action, True)
        self.enter("observe")

    def observe(self):
        self.controller.inject_enhanced_input_for_action(self.action, False)
        require(time.monotonic()-self.phase_started < 8., "native DropWeapon input/delete/cycle timeout")
        current, model = fingerprint(self.controller), capture(self.controller)
        self.current_observation = dict(inventory=current, model=model, active=bool(self.ability.get_property("bIsActive")))
        removed = self.removed_path is None or self.removed_path not in current["items"]
        if not (removed and current["slots"][self.initial] is None and current["active"] == self.expected and model is not None): return
        self.row.update(original_item_identities_preserved=self.original_items.issubset(set(current["items"])),
            removed_item_absent=removed, dropped_slot_empty=True, active_slot=current["active"], inventory_model=model,
            native_ability_inactive=not self.ability.get_property("bIsActive"))
        stats = policy.snapshot(); self.row["counters"] = {key: value-self.before[key] for key, value in stats.items() if type(value) is int and key != "active_count"}
        self.at_drop_end = stats
        self.complete_trial()

    def complete_trial(self):
        self.rollback(); self.enter("restored")

    def rollback(self):
        self.quickbar.call_function("SetActiveSlotIndex", self.original["active"])
        for index, item in enumerate(self.quickbar.call_function("GetSlots")):
            if valid(item) and path(item) not in self.original_items: self.quickbar.call_function("RemoveItemFromSlot", index)
        for item in self.inventory.call_function("GetAllItems"):
            if path(item) not in self.original_items: self.inventory.call_function("RemoveItemInstance", item)

    def restored(self):
        require(time.monotonic()-self.phase_started < 8., "native DropWeapon original fixture restore timeout")
        if time.monotonic()-self.phase_started < .25: return
        require(all(policy.snapshot()[key] == self.at_drop_end[key] for key in ("activations", "fallback_activations")), "late held input reactivated native DropWeapon")
        if fingerprint(self.controller) != self.original or capture(self.controller) != self.original_model: return
        self.row["fixture_original_restored"] = self.row["no_late_activation"] = True; self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_DROP_WEAPON_CASE_OBSERVED "+self.name)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.begin()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "native DropWeapon total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            {"ready": self.ready, "equipment": self.equipment, "observe": self.observe, "restored": self.restored}[self.phase]()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        if error and hasattr(self, "current_observation"): self.report["failed_native_inventory"] = copy.deepcopy(self.current_observation)
        try:
            if hasattr(self, "action"): self.controller.inject_enhanced_input_for_action(self.action, False)
            if hasattr(self, "ability"):
                if self.ability.get_property("bIsActive"): self.ability.call_function("K2_EndAbility")
                self.rollback(); ue.set_mixin_profile(self.ability, "Python")
                self.report["original_player_restored"] = fingerprint(self.controller) == self.original and capture(self.controller) == self.original_model
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_DROP_WEAPON_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report, authority=not getattr(self, "network_fixture", False))
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DROP_WEAPON_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPDropWeaponResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPDropWeaponResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
