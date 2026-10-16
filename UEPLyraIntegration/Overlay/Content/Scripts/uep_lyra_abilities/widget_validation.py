"""Native authority GiveAbility/ClearAbility; observe the real local UI pool.

Temporary CDO fixture defaults select a newly native-created ability's Profile
before OnGiveAbility executes. Restore immediately in finally; never save assets.
Existing production ability instances are neither cleared nor regranted.
"""
import atexit
import json
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture
from .jump_validation import Validation as JumpFixture
from . import jump_mixin as policy
from .widget_contract import PLAN, require, validate

GENERIC = "/Game/Characters/Heroes/Abilities/GA_AbilityWithWidget.GA_AbilityWithWidget_C"


class Validation(JumpFixture):
    def __init__(self, result):
        super().__init__(result)
        self.grant_handle = None
        self.report = dict(schema_version=1, status="running", error=None, cases=[], native_gas_grant_remove=True,
            cdo_defaults_restored=True, original_ability_specs_restored=False, jump_observer_closed=False,
            full_acceptance=False, network_acceptance=False, packaged_runtime=False, physical_input_tested=False,
            ability_callbacks_replayed=False, assets_saved=False, native_ui_pool_written=False)

    def specs(self):
        return sorted(value.get_path_name() for spec in self.asc.get_property("ActivatableAbilities").Items
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value))

    def entries(self):
        return sorted(value.get_path_name() for point in self.points for value in point.call_function("GetAllEntries"))

    def begin(self):
        if not hasattr(self, "equipment_baseline_ready"):
            self.baseline_specs, self.baseline_stable_since = None, time.monotonic()
            self.enter("settle-equipment"); return
        if not hasattr(self, "points"):
            self.tag = self.cls.get_cdo().WidgetExtensionPointTag
            point_cls = ue.find_class("UIExtensionPointWidget")
            self.points = [value for value in self.world.all_objects() if valid(value) and value.is_a(point_cls) and
                value.call_function("GetOwningPlayer") == self.controller and
                str(value.get_property("ExtensionPointTag").TagName) == str(self.tag.TagName)]
            require(bool(self.points), "production UI has no matching native local-player extension point")
            self.report["actual_extension_point_count"] = len(self.points)
            self.report["extension_points"] = [value.get_path_name() for value in self.points]
            self.pristine_specs = self.specs()
        self.name, self.expected = PLAN[self.index//2]
        self.profile = ("BlueprintFallback", "Python")[self.index % 2]
        self.target = self.cls if self.name.startswith("jump") else ue.load_class(GENERIC)
        self.cdo = self.target.get_cdo()
        fields = ["PythonMixinProfile"]+(["WidgetClass"] if self.name.startswith("jump") else ["WidgetClasses", "WidgetExtensionPointTags"])
        self.saved_defaults = {field: self.cdo.get_property(field) for field in fields}
        self.before_entries, self.before_specs = self.entries(), self.specs()
        self.original_single = self.cls.get_cdo().WidgetClass
        try:
            self.cdo.set_property("PythonMixinProfile", self.profile)
            if self.name == "jump-no-widget": self.cdo.set_property("WidgetClass", None)
            elif self.name.startswith("shared"):
                self.cdo.set_property("WidgetClasses", [self.original_single]*self.expected)
                self.cdo.set_property("WidgetExtensionPointTags", [self.tag]*self.expected)
            self.grant_handle = self.asc.call_function("K2_GiveAbility", self.target, 0, -1)
        finally:
            for field, value in self.saved_defaults.items(): self.cdo.set_property(field, value)
        added = [value for spec in self.asc.get_property("ActivatableAbilities").Items
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances)
            if valid(value) and value.get_path_name() not in self.before_specs]
        require(len(added) == 1 and added[0].get_class() == self.target, "native GiveAbility did not create one retained-class instance")
        self.granted = added[0]
        require(str(ue.get_mixin_profile(self.granted)) == self.profile, "native OnGiveAbility did not inherit the fixture CDO profile")
        self.enter("added")

    def settle_equipment(self):
        # Hero/input readiness precedes the asynchronous default equipment
        # grant. Do not mistake those legitimate fire/reload specs for a leak
        # from this fixture's unrelated native GiveAbility/ClearAbility pair.
        inventory = capture(self.controller)
        specs = self.specs()
        expected = ("GA_Weapon_AutoReload_C_", "GA_Weapon_Fire_Pistol_C_", "GA_Weapon_Reload_Pistol_C_")
        if inventory is None or not all(any(name in value for value in specs) for name in expected):
            require(time.monotonic()-self.phase_started < 12., "original pistol equipment/ability grants not ready")
            return
        if specs != self.baseline_specs:
            self.baseline_specs, self.baseline_stable_since = specs, time.monotonic(); return
        if time.monotonic()-self.baseline_stable_since < .5: return
        self.equipment_baseline_ready = True
        self.report["native_equipment_baseline"] = inventory
        self.begin()

    def verify_added(self):
        self.added_entries = self.entries()
        delta = len(self.added_entries)-len(self.before_entries)
        require(delta == self.expected*len(self.points), "native extension registration count differs: "+repr((self.name, delta, self.expected)))
        self.after_profile = "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback"
        ue.set_mixin_profile(self.granted, self.after_profile)
        self.enter("switched")

    def verify_switched(self):
        require(self.entries() == self.added_entries, "Profile teardown removed ability-owned native UI")
        self.granted_native_type_preserved = self.granted.get_class() == self.target
        require(str(ue.get_mixin_profile(self.granted)) == self.after_profile, "native removal Profile differs")
        self.asc.call_function("ClearAbility", self.grant_handle); self.grant_handle = None
        self.enter("removed")

    def verify_removed(self):
        current_entries, current_specs = self.entries(), self.specs()
        self.report["last_removal_observation"] = dict(name=self.name, profile=self.profile,
            before_entries=self.before_entries, after_entries=current_entries,
            before_specs=self.before_specs, after_specs=current_specs,
            specs_added=sorted(set(current_specs)-set(self.before_specs)),
            specs_missing=sorted(set(self.before_specs)-set(current_specs)))
        require(current_entries == self.before_entries and current_specs == self.before_specs,
                "native ClearAbility failed to restore UI entries/specs")
        # Compare reflected CDO arrays/classes without relying on struct repr.
        restored = all(self.cdo.get_property(field) == value for field, value in self.saved_defaults.items())
        require(restored, "native grant fixture CDO defaults not restored")
        self.report["cases"].append(dict(name=self.name, profile_at_grant=self.profile,
            profile_at_remove=self.after_profile, native_type_preserved=self.granted_native_type_preserved,
            specs_added=1, specs_restored=True, cdo_restored=restored,
            entries_added=len(self.added_entries)-len(self.before_entries),
            entries_unchanged_after_profile_switch=True, entries_restored_after_remove=True))
        ue.log("UEP_ABILITY_WIDGET_CASE_PASSED "+self.name+"/"+self.profile)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.begin()

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 180., "native ability UI timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "settle-equipment": self.settle_equipment()
            elif time.monotonic()-self.phase_started > .2:
                {"added": self.verify_added, "switched": self.verify_switched, "removed": self.verify_removed}[self.phase]()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, failure=None):
        if self.finished: return
        self.finished = True
        try:
            if self.grant_handle is not None:
                self.asc.call_function("ClearAbility", self.grant_handle); self.grant_handle = None
            if hasattr(self, "pristine_specs"):
                self.report["original_ability_specs_restored"] = self.specs() == self.pristine_specs
            if hasattr(self, "original_jump"):
                require(ue.unregister_mixin(self.player_class) and self.pawn.find_function("OnJumped") == self.original_jump,
                        "native observer not restored")
                self.report["jump_observer_closed"] = True
            if hasattr(self, "pristine_specs"):
                require(self.report["original_ability_specs_restored"], "original production ability specs changed")
        except Exception: failure = (failure or "")+traceback.format_exc()
        self.report.update(status="failed" if failure else "awaiting_shutdown", error=failure)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if failure else ue.log)("UEP_ABILITY_WIDGET_DIFFERENTIAL_"+("FAILED "+failure if failure else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_ABILITY_WIDGET_SHUTDOWN_"+self.report["status"].upper())


result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAbilityWidgetResult="))
validation = Validation(result); atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
