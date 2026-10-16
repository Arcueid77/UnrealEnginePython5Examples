"""Original inventory/equipment grants real GAS ability; no Activate replay."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from .inventory_pad_player_validation import Validation as NativeInventoryFixture
from . import heal_ability_mixin as policy
from .heal_ability_contract import PLAN, equal, require
from .effect_pad_mixin import valid, ability_system


class Validation(NativeInventoryFixture):
    def __init__(self, result):
        super().__init__(result)
        self.report = dict(schema_version=1, status="running", error=None, cases=[],
            native_inventory_equipment_ability_grant=True, original_player_restored=False)
        for field in ("network_acceptance", "full_acceptance", "packaged_runtime", "ability_activate_called_by_probe",
                      "task_callbacks_called_by_probe", "health_properties_written", "animation_assets_modified", "production_placement_tested"):
            self.report[field] = False
        self.side_results, self.elapsed, self.pauses, self.rollbacks = [], [], [], []
        self.switches = []
        self.paused = False

    def game_time(self):
        return float(self.statics.call_function("GetTimeSeconds", self.world))

    def health(self):
        return float(self.health_component.call_function("GetHealth"))

    def set_health_fixture(self, value):
        current = self.health()
        if abs(value-current) > .01:
            result = self.bridge.call_function("ApplyAuthorityHealthDelta", "heal-ability."+str(self.index), value-current)
            require(result.bApplied and abs(result.HealthAfter-value) < .01, "native fixture Health setup rejected")

    def instances(self):
        result = []
        for spec in self.asc.get_property("ActivatableAbilities").Items:
            if valid(spec.Ability) and spec.Ability.get_class() == self.cls:
                self.source_object = spec.SourceObject
                result.extend(list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances))
        return [ability for ability in result if valid(ability)]

    def begin(self):
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        self.cls = ue.load_class(policy.CLASS)
        self.health_component = self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        self.asc = ability_system(self.pawn)
        self.bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        if not hasattr(self, "original_health"):
            self.original_health = self.health()
            self.report["pawn"] = self.pawn.get_path_name()
        self.set_health_fixture(75.)
        self.health_before = self.health()
        # The native RangedWeapon superclass CHECKS that SourceObject is a
        # ranged equipment instance. Never grant this class without its source.
        definition = ue.load_class("/ShooterCore/Items/HealthPickup_Unused/ID_HealPickup.ID_HealPickup_C")
        equipment_definition = ue.load_class("/ShooterCore/Items/HealthPickup_Unused/WID_HealPickup.WID_HealPickup_C")
        instance_type = equipment_definition.get_cdo().InstanceType
        require(valid(instance_type), "original heal equipment has no instance type")
        self.report["native_equipment_instance_type"] = instance_type.get_path_name()
        require(instance_type.get_cdo().is_a(ue.find_class("LyraRangedWeaponInstance")),
                "original heal definition cannot satisfy native ranged-weapon source; do not activate invalid fixture")
        self.created_item = self.inventory.call_function("AddItemDefinition", definition, 1)
        slot = int(self.quickbar.call_function("GetNextFreeItemSlot"))
        require(slot >= 0 and valid(self.created_item), "native heal inventory fixture could not grant original item")
        self.quickbar.call_function("AddItemToSlot", slot, self.created_item)
        self.quickbar.call_function("SetActiveSlotIndex", slot)
        self.enter("equipment")

    def activate(self):
        values = self.instances()
        if len(values) != 1:
            require(time.monotonic()-self.phase_started < 8., "original heal item did not grant one native ability")
            return
        self.ability = values[0]
        require(valid(self.source_object) and self.source_object.is_a(ue.find_class("LyraRangedWeaponInstance")) and
                self.source_object.call_function("GetInstigator") == self.created_item,
                "native heal ability source is not the actual equipped inventory item")
        require(not self.ability.get_property("bIsActive"), "heal ability active before native ASC activation")
        ue.set_mixin_profile(self.ability, self.profile)
        self.montage = self.ability.get_property("Heal Montage")
        if self.name == "native-timer":
            self.montage = ue.load_object(ue.find_class("AnimMontage"), "/Game/Weapons/Rifle/Animations/AM_MM_Rifle_Reload.AM_MM_Rifle_Reload")
            self.ability.set_property("Heal Montage", self.montage)
            require(float(self.montage.call_function("GetPlayLength")) > 1.2, "timer trial needs a genuinely longer native Montage")
        self.anim = self.pawn.Mesh.call_function("GetAnimInstance")
        self.stats_before = policy.snapshot()
        self.native_started, self.pause_observed, self.cancelled, self.profile_switched = self.game_time(), False, False, False
        result = self.asc.call_function("TryActivateAbilityByClass", self.cls, False)
        require(result, "native ASC rejected original heal activation")
        self.enter("observe")

    def observe(self):
        elapsed = self.game_time()-self.native_started
        active = bool(self.ability.get_property("bIsActive"))
        if self.name in ("native-cancel", "native-interrupt") and not self.cancelled and elapsed > .1 and active:
            self.cancelled = True
            if self.name == "native-cancel":
                self.ability.call_function("K2_CancelAbility")
            else:
                self.anim.call_function("Montage_Stop", 0., self.montage)
            return
        if self.name == "external-native-end" and not self.cancelled and elapsed > .1 and active:
            self.cancelled = True
            self.ability.call_function("K2_EndAbility")
            return
        if self.name == "paused-world-time" and not self.pause_observed and elapsed > .1 and active:
            self.frozen_time, self.paused_wall = self.game_time(), time.monotonic()
            require(self.statics.call_function("SetGamePaused", self.world, True), "native heal pause failed")
            self.paused = True; self.enter("paused")
            return
        if self.name == "active-profile-switch" and not self.profile_switched and elapsed > .1 and active:
            self.profile_switched = True
            ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
            return
        if active:
            require(elapsed < 3., "native heal ability did not end")
            return
        if self.name in ("native-cancel", "native-interrupt"):
            require(self.cancelled, "native heal finished before cancellation fixture")
        value = dict(health_before=self.health_before, health_after=self.health(),
            max_health=float(self.health_component.call_function("GetMaxHealth")), active_after=active,
            montage=self.montage.get_path_name(), montage_still_playing=bool(self.anim.call_function("Montage_IsPlaying", self.montage)),
            native_type_preserved=self.ability.get_class() == self.cls)
        after = policy.snapshot()
        self.counts = {key: after[key]-self.stats_before[key] for key in after if isinstance(after[key], int) and key != "active_count"}
        self.side_results.append(value); self.elapsed.append(elapsed); self.pauses.append(self.pause_observed)
        self.switches.append(self.profile_switched)
        self.anim.call_function("Montage_Stop", 0., self.montage)
        self.rollback(); self.rollbacks.append(self.fingerprint() == self.original)
        if self.index % 2:
            require(equal(*self.side_results), "heal ability native BP/Python differs: "+repr(self.side_results))
            self.report["cases"].append(dict(name=self.name, passed=True, blueprint=self.side_results[0], python=self.side_results[1],
                python_counters=self.counts, native_elapsed_seconds=self.elapsed, native_pause_observed=self.pauses,
                native_profile_switch_exercised=self.switches,
                inventory_rollbacks=self.rollbacks))
            ue.log("UEP_HEAL_ABILITY_CASE_PASSED "+self.name)
            self.side_results, self.elapsed, self.pauses, self.rollbacks = [], [], [], []
            self.switches = []
        self.index += 1
        if self.index == len(PLAN)*2:
            self.finish()
        else:
            self.begin()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 220., "heal ability timeout: "+self.phase)
            if self.phase == "ready":
                self.ready()
            elif self.phase == "equipment":
                self.activate()
            elif self.phase == "observe":
                self.observe()
            elif self.phase == "paused" and time.monotonic()-self.paused_wall > .3:
                require(self.game_time() == self.frozen_time and self.ability.get_property("bIsActive"), "native heal advanced while world paused")
                require(self.statics.call_function("SetGamePaused", self.world, False), "native heal unpause failed")
                self.paused = False; self.pause_observed = True; self.enter("observe")
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finish(self, failure=None):
        if self.finished:
            return
        self.finished = True
        try:
            if self.paused:
                self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            ability = getattr(self, "ability", None)
            if valid(ability) and ability.get_property("bIsActive"):
                ability.call_function("K2_CancelAbility")
            if self.original_items is not None:
                self.rollback()
                self.set_health_fixture(self.original_health)
                self.pawn.set_actor_location(self.original_location)
                self.movement.call_function("SetMovementMode", self.original_mode, self.original_custom_mode)
                self.controller.call_function("SetControlRotation", self.original_rotation)
                require(self.fingerprint() == self.original and abs(self.health()-self.original_health) < .01,
                        "native heal inventory/Health restore incomplete")
                self.report["original_player_restored"] = True
        except Exception:
            failure = (failure or "")+traceback.format_exc()
        self.report.update(status="failed" if failure else "awaiting_shutdown", error=failure, elapsed_seconds=time.monotonic()-self.started)
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if failure else ue.log)("UEP_HEAL_ABILITY_DIFFERENTIAL_"+("FAILED "+failure if failure else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .heal_ability_contract import validate
                self.report["status"] = "passed"; validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_HEAL_ABILITY_SHUTDOWN_"+self.report["status"].upper())


result = next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-UEPHealAbilityResult="))
validation = Validation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
