"""Native Quickbar equip/unequip, read-only boundary observer and CDO fixture."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture, services
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities import reload_weapon_fixture as fixtures
from . import weapon_instance_mixin as policy, weapon_instance_observation as observation
from .weapon_instance_contract import PLAN, require, validate


def optional_object(path):
    try: return ue.find_object(path)
    except Exception as error:
        if str(error) == "unable to find object "+path: return None
        raise


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.recording, self.fixture, self.saved_cdos, self.sides = False, False, None, {}, []
        self.gc_enabled, self.paused = "-UEPWeaponInstanceGC" in sys.argv, False
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(status="running", error=None, cases=[], original_player_restored=False,
            original_cdo_selectors_restored=False, observer_profiles_restored=False,
            read_only_profile_observer=True, fixture_cdo_profile_selector_written=True)
        self.report["native_gc_cases"] = []
        for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "lifecycle_called_by_probe",
            "animation_state_written_by_probe", "animation_assets_modified", "native_cpp_time_written", "death_branch_native_tested", "gc_stress_tested"): self.report[field] = False

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()

    def equipment(self):
        item = self.quickbar.call_function("GetActiveSlotItem")
        component = self.pawn.get_component_by_type(ue.find_class("LyraEquipmentManagerComponent"))
        matches = [value for value in component.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance"))
            if valid(value) and value.call_function("GetInstigator") == item]
        return matches[0] if len(matches) == 1 else None

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bHealthReady and not snap.bDamageImmune and snap.Health > 0): continue
            controller = self.statics.call_function("GetPlayerController", world, 0)
            model = capture(controller)
            if model is None or "ID_Pistol" not in model["definition"]: continue
            self.world, self.controller, self.pawn = world, controller, controller.get_controlled_pawn()
            self.inventory, self.quickbar = services(controller)
            self.original = fixtures.baseline(controller)
            equipment = self.equipment()
            if not valid(equipment): continue
            self.original_class = equipment.get_class()
            self.report["native_default_python_equipped"] = policy.instance_snapshot(equipment)["equips"] == 1
            self.root = ue.load_class(policy.CLASS)
            observation.install(self.root, self.observe)
            self.prepare(); return

    def observe(self, instance, equipped):
        if not self.recording or instance.get_class() != self.target_class or equipped != self.record_step: return
        require(instance.call_function("GetPawn") == self.pawn, "equipment observer crossed owner")
        key = "equip" if equipped else "unequip"
        self.events[key].append(dict(instance=instance.get_path_name(), state=observation.capture(instance, equipped),
            counters=policy.instance_snapshot(instance), native_class=instance.get_class().get_path_name(), profile=str(ue.get_mixin_profile(instance))))

    def prepare(self):
        self.recording = False
        if self.fixture is not None: fixtures.restore(self.controller, self.fixture)
        self.weapon, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        self.fixture = fixtures.install(self.controller, "rifle" if self.weapon == "pistol" else self.weapon)
        self.enter("fixture")

    def fixture_ready(self):
        instance = self.equipment(); model = capture(self.controller)
        if not valid(instance) or model is None or fixtures.WEAPONS[self.fixture["weapon"]][2] not in model["definition"]: return
        self.target_class = self.original_class if self.weapon == "pistol" else instance.get_class()
        cdo = self.target_class.get_cdo(); path = self.target_class.get_path_name()
        if path not in self.saved_cdos: self.saved_cdos[path] = (cdo, str(cdo.get_property("PythonMixinProfile")))
        cdo.set_property("PythonMixinProfile", self.profile)
        self.target_slot = 0 if self.weapon == "pistol" else self.fixture["slot"]
        self.other_slot = self.fixture["slot"] if self.weapon == "pistol" else 0
        self.quickbar.call_function("SetActiveSlotIndex", self.other_slot)
        self.enter("background")

    def background(self):
        if time.monotonic()-self.phase_started < .1 or capture(self.controller) is None: return
        self.events = dict(equip=[], unequip=[])
        self.expected_item = self.quickbar.call_function("GetSlots")[self.target_slot]
        self.record_step, self.recording = True, True
        self.quickbar.call_function("SetActiveSlotIndex", self.target_slot)
        self.instance = self.equipment()
        require(valid(self.instance), "native equipment grant did not produce one instance")
        self.row = dict(native_class=self.instance.get_class().get_path_name(), native_type_preserved=self.instance.get_class() == self.target_class,
            native_equipment_item_source_matches=self.instance.call_function("GetInstigator") == self.expected_item)
        self.enter("equipped")

    def equipped(self):
        if time.monotonic()-self.phase_started < .05: return
        if "native_outer_cpp_equip_time_observed" not in self.row:
            elapsed = float(self.instance.call_function("GetTimeSinceLastInteractedWith"))
            self.row["native_outer_cpp_equip_time_observed"] = 0. <= elapsed < .5
        if self.gc_enabled and self.profile == "Python" and not self.row.get("gc_done"):
            self.gc_proxy = policy.proxy_path(self.instance)
            require(self.gc_proxy and valid(ue.find_object(self.gc_proxy)), "native equipment proxy missing before GC")
            self.gc_before = observation.capture(self.instance, True)
            require(self.statics.call_function("SetGamePaused", self.world, True), "native equipment GC pause refused")
            self.paused = True
            ue.find_class("KismetSystemLibrary").get_cdo().call_function("CollectGarbage")
            self.enter("gc"); return
        require(len(self.events["equip"]) == 1 and self.events["equip"][0]["profile"] == self.profile, "native equipment CDO profile/equip dispatch differs")
        before = observation.capture(self.instance, True)
        ue.set_mixin_profile(self.instance, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
        self.row["instance_profile_switch_preserved_state"] = observation.capture(self.instance, True) == before
        ue.set_mixin_profile(self.instance, self.profile)
        self.record_step = False
        self.quickbar.call_function("SetActiveSlotIndex", self.other_slot)
        self.enter("unequipped")

    def collected(self):
        require(time.monotonic()-self.phase_started < 6., "native equipment proxy was not collected")
        if valid(optional_object(self.gc_proxy)): return
        after = observation.capture(self.instance, True)
        self.report["native_gc_cases"].append(dict(weapon=self.weapon, native_proxy_collected=True,
            paused_state_preserved=after == self.gc_before, before=self.gc_before, after=after))
        require(after == self.gc_before, "native proxy GC changed paused equipment animation")
        require(self.statics.call_function("SetGamePaused", self.world, False), "native equipment GC unpause refused")
        self.paused = False; self.row["gc_done"] = True; self.enter("equipped")

    def unequipped(self):
        require(len(self.events["equip"]) == len(self.events["unequip"]) == 1, "native equipment lifecycle callback count differs")
        equip, unequip = self.events["equip"][0], self.events["unequip"][0]
        require(equip["instance"] == unequip["instance"], "equipment lifecycle crossed native instances")
        self.row.update(equip=equip["state"], unequip=unequip["state"], native_equip_callbacks=1, native_unequip_callbacks=1, counters=unequip["counters"])
        self.recording = False
        cdo, original = self.saved_cdos[self.target_class.get_path_name()]
        cdo.set_property("PythonMixinProfile", original)
        fixtures.restore(self.controller, self.fixture)
        self.row["fixture_inventory_restored"] = fixtures.restored(self.controller, self.fixture)
        self.fixture = None; self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.weapon, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_WEAPON_INSTANCE_CASE_OBSERVED "+self.weapon)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.prepare()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "native equipment total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase != "ready": require(time.monotonic()-self.phase_started < 12., "native equipment phase timeout: "+self.phase)
            {"ready": self.ready, "fixture": self.fixture_ready, "background": self.background, "equipped": self.equipped, "gc": self.collected, "unequipped": self.unequipped}[self.phase]()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished, self.recording = True, False
        if error: self.report["failed_phase"] = self.phase; self.report["failed_events"] = copy.deepcopy(getattr(self, "events", {}))
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            for cdo, original in self.saved_cdos.values(): cdo.set_property("PythonMixinProfile", original)
            self.report["original_cdo_selectors_restored"] = all(str(cdo.get_property("PythonMixinProfile")) == original for cdo, original in self.saved_cdos.values())
            if self.fixture is not None: fixtures.restore(self.controller, self.fixture); self.fixture = None
            if hasattr(self, "controller"): self.report["original_player_restored"] = fixtures.restored(self.controller, self.original)
            if hasattr(self, "root"): observation.restore(self.root); self.report["observer_profiles_restored"] = True
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_WEAPON_INSTANCE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        self.report["gc_stress_tested"] = self.gc_enabled
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_WEAPON_INSTANCE_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPWeaponInstanceResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPWeaponInstanceResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
