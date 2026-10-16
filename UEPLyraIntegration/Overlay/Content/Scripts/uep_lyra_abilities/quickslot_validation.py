"""Production native ability + real inventory/equipment; no handler replay."""
import atexit
import copy
import json
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayEventData, GameplayTag
from uep_lyra_world.inventory_pad_player_validation import Validation as InventoryFixture, path
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_network_bots import isolate_bots
from . import quickslot_mixin as policy
from .quickslot_contract import PLAN, require, validate


class Validation(InventoryFixture):
    def __init__(self, result):
        super().__init__(result)
        self.side_results = []
        self.report = dict(schema_version=1, status="running", error=None, cases=[], native_gameplay_event_producer=True,
            original_player_restored=False, original_ability_active_restored=False, fixture_native_inventory_setup=True,
            full_acceptance=False, network_acceptance=False, packaged_runtime=False, hardware_input_tested=False,
            enhanced_input_tested=False, python_handler_replayed=False, task_callbacks_replayed=False,
            inventory_properties_written=False, native_rpc_bypassed=False)

    def tasks(self):
        return sum(valid(task) and task.is_a(ue.find_class("AbilityTask_WaitGameplayEvent")) for task in self.ability.get_property("ActiveTasks"))

    def native_end(self, cancel=False):
        if self.ability.get_property("bIsActive"):
            self.ability.call_function("K2_CancelAbility" if cancel else "K2_EndAbility")

    def begin(self):
        if not hasattr(self, "ability"):
            self.asc, self.cls = ability_system(self.pawn), ue.load_class(policy.CLASS)
            matches = [value for spec in self.asc.get_property("ActivatableAbilities").Items
                if valid(spec.Ability) and spec.Ability.get_class() == self.cls
                for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
            require(len(matches) == 1, "original native Quickslot grant not unique")
            self.ability = matches[0]
            self.report["native_default_active_with_three_tasks"] = bool(self.ability.get_property("bIsActive")) and self.tasks() == 3
            self.report["native_default_owned_python_scope"] = self.ability.get_path_name() in policy.snapshot()["active_abilities"] and str(ue.get_mixin_profile(self.ability)) == "Python"
            require(self.report["native_default_active_with_three_tasks"], "OnSpawn default did not start three native tasks")
            require(self.report["native_default_owned_python_scope"], "OnSpawn used retained BP instead of Python")
            self.native_end()
            self.prepare_inventory()
        self.name, initial, self.expected = PLAN[self.index//2]
        self.profile = ("BlueprintFallback", "Python")[self.index % 2]
        self.native_end(); ue.set_mixin_profile(self.ability, self.profile)
        if getattr(self, "network_fixture", False):
            require(int(self.quickbar.call_function("GetActiveSlotIndex")) == initial, "native replicated starting slot not ready")
        else: self.quickbar.call_function("SetActiveSlotIndex", initial)
        self.before = policy.snapshot()
        require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native ASC refused Quickslot activation")
        self.tasks_before = self.tasks()
        require(self.tasks_before == 3, "native Quickslot did not create exactly three event tasks")
        self.switched = False
        if self.name == "active-profile-switch":
            ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
            require(not self.ability.get_property("bIsActive") and self.tasks() == 0, "Profile switch left old GAS tasks active")
            self.send("forward", 0.)
            require(int(self.quickbar.call_function("GetActiveSlotIndex")) == initial, "ended old Profile still received native event")
            require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "new Profile native reactivation refused")
            self.switched = True
        if self.name.startswith("select"):
            value = {"select-fraction": 1.9, "select-negative-fraction": -.9, "select-negative": -1.9, "select-out-of-range": 99.}[self.name]
            self.send("select", value)
        elif self.name == "unrelated-event": self.send("unrelated", 0.)
        else: self.send("backward" if self.name == "cycle-backward" else "forward", 0.)
        self.enter("equipment")

    def prepare_inventory(self):
        for definition in ("/ShooterCore/Weapons/Rifle/ID_Rifle.ID_Rifle_C", "/ShooterCore/Weapons/Shotgun/ID_Shotgun.ID_Shotgun_C"):
            slot = int(self.quickbar.call_function("GetNextFreeItemSlot"))
            require(slot >= 0, "fixture needs three actual inventory slots")
            item = self.inventory.call_function("AddItemDefinition", ue.load_class(definition), 1)
            self.quickbar.call_function("AddItemToSlot", slot, item)

    def send(self, kind, magnitude):
        tags = dict(policy.TAGS)
        tag = tags.get(kind, "InputTag.Ability.Jump")
        payload = GameplayEventData(EventTag=GameplayTag(TagName=tag), EventMagnitude=magnitude,
            Instigator=self.pawn, Target=self.pawn)
        ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function(
            "SendGameplayEventToActor", self.pawn, GameplayTag(TagName=tag), payload)

    def observe(self):
        current = capture(self.controller)
        if current is None or current["active"] != self.expected:
            require(time.monotonic()-self.phase_started < 5., "native Quickslot/equipment result not observed: "+repr(current))
            return
        self.native_end(self.name == "native-cancel")
        tasks_after = self.tasks()
        self.send("backward", 0.)
        require(int(self.quickbar.call_function("GetActiveSlotIndex")) == self.expected, "ended native event task still selected a slot")
        stats = policy.snapshot()
        counters = {key: value-self.before[key] for key, value in stats.items() if type(value) is int and key != "active_count"}
        row = dict(inventory=current, native_type_preserved=self.ability.get_class() == self.cls,
            native_tasks_before=self.tasks_before, native_tasks_after_end=tasks_after,
            ended_inactive=not self.ability.get_property("bIsActive"), ended_event_ignored=True,
            profile_switch_reactivated=self.switched, counters=counters)
        self.side_results.append(row)
        self.record_trial(row)
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.side_results[0], python=self.side_results[1]))
            self.side_results = []; ue.log("UEP_QUICKSLOT_CASE_PASSED "+self.name)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.begin()

    def record_trial(self, row):
        """Native network scheduler extension; no production callback replay."""

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "Quickslot native timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "equipment" and time.monotonic()-self.phase_started > .2: self.observe()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if hasattr(self, "ability"):
                self.native_end(); ue.set_mixin_profile(self.ability, "Python")
            if self.original_items is not None:
                self.rollback()
                require(self.pawn.set_actor_location(self.original_location), "native position restore failed")
                self.movement.call_function("StopMovementImmediately")
                self.movement.call_function("SetMovementMode", self.original_mode, self.original_custom_mode)
                self.controller.call_function("SetControlRotation", self.original_rotation)
                self.report["original_player_restored"] = self.fingerprint() == self.original and int(self.movement.MovementMode) == self.original_mode
            if hasattr(self, "ability"):
                require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "original OnSpawn ability reactivation failed")
                self.report["original_ability_active_restored"] = bool(self.ability.get_property("bIsActive")) and self.tasks() == 3
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_QUICKSLOT_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_QUICKSLOT_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPQuickslotResult=")), None)
if result is not None:
    validation = Validation(result); atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
