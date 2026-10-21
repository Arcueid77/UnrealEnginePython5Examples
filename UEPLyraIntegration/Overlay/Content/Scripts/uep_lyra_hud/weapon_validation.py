"""Opt-in BP/Python comparisons on real inventory, widgets and materials.

The isolated Entry-map fixture is not a claim of fire/GAS or network parity.
"""

import atexit
import json
import importlib
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.classes import GameplayStatics, KismetSystemLibrary
from unreal_engine.structs import Geometry, GameplayTag, Vector2D

from .ammo_mixin import MAGAZINE_AMMO, MAGAZINE_SIZE, SPARE_AMMO, RELOAD_EVENT
from . import weapon_observer
from uep_runtime import SubscriptionScope


ASSETS = {
    "W_WeaponAmmoAndName": "/ShooterCore/UserInterface/HUD/W_WeaponAmmoAndName.W_WeaponAmmoAndName_C",
    "W_AmmoCounter_Pistol": "/ShooterCore/Weapons/Pistol/W_AmmoCounter_Pistol.W_AmmoCounter_Pistol_C",
    "W_AmmoCounter_Rifle": "/ShooterCore/Weapons/Rifle/W_AmmoCounter_Rifle.W_AmmoCounter_Rifle_C",
    "W_AmmoCounter_Shotgun": "/ShooterCore/Weapons/Shotgun/W_AmmoCounter_Shotgun.W_AmmoCounter_Shotgun_C",
}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def set_stat(item, tag, value):
    tag_value = GameplayTag(TagName=tag)
    current = item.call_function("GetStatTagStackCount", tag_value)
    if current:
        item.call_function("RemoveStatTagStack", tag_value, current)
    if value:
        item.call_function("AddStatTagStack", tag_value, value)


def material_state(image):
    material = image.call_function("GetDynamicMaterial")
    return {name: float(material.call_function("K2_GetScalarParameterValue", name))
            for name in ("Rounds_Max", "Rounds_Current", "IsLowAmmo")}


def snapshot(widget, name):
    if name == "W_WeaponAmmoAndName":
        return {"magazine": str(widget.AmmoLeftInMagazineWidget.call_function("GetText")),
                "spare": str(widget.TotalCountWidget.call_function("GetText")),
                "name": str(widget.WeaponNameWidget.call_function("GetText")),
                "visibility": int(widget.VerticalBoxForHiding.call_function("GetVisibility"))}
    return {"bar": material_state(widget.AmmoCounter_Bar),
            "glow": material_state(widget.AmmoCounter_Glow)}


class WeaponValidation:
    def __init__(self, result_path):
        self.path = Path(result_path)
        check(not self.path.exists(), "refusing to overwrite weapon HUD evidence")
        self.started = time.monotonic()
        self.world = self.controller = None
        self.widgets, self.classes, self.items = [], [], []
        self.restored_classes = set()
        self.report = {"schema_version": 1, "status": "running", "full_acceptance": False,
                       "scope": "isolated-real-UMG-BP-Python-differential",
                       "network_acceptance": False, "cases": [], "images": [],
                       "declarations": []}
        self.phase, self.ready_at = "create", None

    def create(self, world, controller):
        self.world, self.controller = world, controller
        item_class = ue.find_class("LyraInventoryItemInstance")
        for index, (maximum, spare) in enumerate(((30, 1234), (8, 57))):
            item = ue.new_object(item_class, controller, "UEPWeaponHUDItem" + str(index))
            for tag, value in ((MAGAZINE_SIZE, maximum), (SPARE_AMMO, spare), (MAGAZINE_AMMO, maximum)):
                set_stat(item, tag, value)
            self.items.append(item)
        quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
        if quickbar is None:
            quickbar = controller.add_actor_component(ue.find_class("LyraQuickBarComponent"), "UEPWeaponHUDQuickbar")
        self.quickbar = quickbar
        # This is deterministic presenter input setup, not a claim
        # that equipment or the SetActiveSlotIndex server RPC was exercised.
        quickbar.set_property("Slots", self.items)
        quickbar.set_property("ActiveSlotIndex", 0)
        for index, (name, path) in enumerate(ASSETS.items()):
            cls = ue.load_class(path)
            cdo = cls.get_cdo()
            check(str(cdo.GetPythonMixinProfile()) == "Python", name + " has no persisted Python selector")
            mixin_set = cdo.GetPythonMixinSet()
            check(mixin_set is not None, name + " has no persisted Mixin Set")
            ue.register_declared_mixin(cls)
            self.report["declarations"].append({"asset": name, "mixin_set": mixin_set.get_path_name(),
                                                "default_profile": "Python", "runtime_class": cls.get_name()})
            self.classes.append(cls)
            pair = []
            for column, selected in enumerate(("BlueprintFallback", "Python")):
                widget = controller.create_widget(cls)
                # The candidate uses the authored Interface/CDO default, not
                # a test-only Python registration or instance override.
                if selected == "BlueprintFallback":
                    ue.set_mixin_profile(widget, selected)
                check(ue.get_mixin_profile(widget) == selected, name + " selected the wrong profile")
                widget.AddToViewport(100)
                widget.SetPositionInViewport(Vector2D(X=80.0 + column * 610.0, Y=100.0 + index * 110.0), False)
                widget.SetDesiredSizeInViewport(Vector2D(X=500.0, Y=95.0))
                if name != "W_WeaponAmmoAndName":
                    widget.set_property("InventoryInstance", self.items[0])
                pair.append(widget)
                self.widgets.append(widget)
            self.compare(name, pair, "initialized", initialize=True)
            for current in (5, 4, 3, 2, 1, 0, 30):
                set_stat(self.items[0], MAGAZINE_AMMO, current)
                self.compare(name, pair, "ammo-" + str(current))
            if name != "W_WeaponAmmoAndName":
                for widget in pair:
                    widget.set_property("InventoryInstance", self.items[1])
                self.compare(name, pair, "weapon-switch", initialize=True)
                for widget in pair:
                    resource_before = widget.AmmoCounter_Bar.Brush.ResourceObject
                    size_before = str(widget.AmmoCounter_Bar.Brush.ImageSize)
                    widget.call_function("SetWeaponSpecificImages", widget.AmmoCounter_Bar, widget.AmmoCounter_Glow)
                    check(widget.AmmoCounter_Bar.Brush.ResourceObject == widget.AmmoCounter_Glow,
                          name + " brush resource did not follow source")
                    check(str(widget.AmmoCounter_Bar.Brush.ImageSize) == size_before, name + " changed counter brush size")
                    restored_brush = widget.AmmoCounter_Bar.Brush
                    restored_brush.ResourceObject = resource_before
                    widget.AmmoCounter_Bar.call_function("SetBrush", restored_brush)
                self.report["cases"].append({"asset": name, "scenario": "brush-helper",
                                              "resource_matches_argument": True, "counter_style_preserved": True})
            else:
                quickbar.set_property("ActiveSlotIndex", 1)
                self.compare(name, pair, "weapon-switch")
                quickbar.set_property("ActiveSlotIndex", -1)
                self.compare(name, pair, "empty-slot")
                quickbar.set_property("ActiveSlotIndex", 0)
                self.compare(name, pair, "slot-restored")
                # Exercise the retained BP event and Python alias against a
                # real local input subsystem. Entry has no firing/reload GAS
                # abilities, so this is input dispatch, not gameplay reload.
                for widget in pair:
                    widget.call_function(RELOAD_EVENT)
                calls = dict(pair[1]._uep_weapon_hud_calls)
                check(calls.get("ReloadClicked", 0) == 1, "reload event did not dispatch to Python")
                self.report["cases"].append({"asset": name, "scenario": "reload-input-dispatch",
                                              "native_input_intent_only": True, "python_calls": calls})
            for widget in pair:
                check(widget.get_class() == cls, name + " changed UObject class")
        self.report["class_identity_preserved"] = True
        self.report["persisted_declarations_used"] = True
        received = []
        scope = SubscriptionScope()
        scope.listen_gameplay_signal(controller, "Lyra.QuickBar.Message.ActiveIndexChanged",
                                     lambda channel: received.append(str(channel.TagName)))
        quickbar.call_function("OnRep_ActiveSlotIndex")
        check(received == ["Lyra.QuickBar.Message.ActiveIndexChanged"], "native Gameplay Message did not dispatch")
        scope.close()
        quickbar.call_function("OnRep_ActiveSlotIndex")
        check(len(received) == 1 and scope.count == 0 and scope.closed, "cancelled native listener still fired")
        self.report["subscription_scope"] = {"status": "passed", "native_message_callbacks": len(received),
                                              "cancel_verified": True, "payload_access": False}
        self.report["profile_switches"] = []
        for index, name in enumerate(ASSETS):
            baseline, candidate = self.widgets[index * 2:index * 2 + 2]
            active = weapon_observer.snapshot()["active_count"]
            ue.set_mixin_profile(candidate, "BlueprintFallback")
            check(weapon_observer.snapshot()["active_count"] == active - 1, "profile switch retained Python observer")
            candidate.call_function("Tick", Geometry(), 0.016)
            ue.set_mixin_profile(candidate, "Python")
            candidate.call_function("Tick", Geometry(), 0.016)
            weapon_observer.refresh()
            check(weapon_observer.snapshot()["active_count"] == active, "return to Python did not resume observation")
            check(snapshot(baseline, name) == snapshot(candidate, name), "live profile switch changed presentation")
            self.report["profile_switches"].append({"asset": name, "status": "passed",
                                                      "without_reconstruct": True, "observer_count_restored": active})
        self.ready_at = time.monotonic()
        self.phase = "capture"

    def compare(self, name, pair, scenario, initialize=False):
        for widget in pair:
            if initialize and name != "W_WeaponAmmoAndName":
                widget.call_function("OnWeaponInitialized")
            widget.call_function("Tick", Geometry(), 0.016)
        weapon_observer.refresh()
        baseline, candidate = (snapshot(widget, name) for widget in pair)
        check(baseline == candidate, name + " " + scenario + " differs: " + repr((baseline, candidate)))
        counts = dict(pair[1]._uep_weapon_hud_calls)
        check(counts.get("Tick", 0) > 0, name + " did not execute Python Tick")
        self.report["cases"].append({"asset": name, "scenario": scenario,
                                      "baseline": baseline, "python": candidate, "python_calls": counts})

    def cleanup(self):
        for widget in self.widgets:
            if widget.is_valid():
                widget.RemoveFromParent()
        for cls in self.classes:
            check(ue.unregister_mixin(cls), "weapon router was not restored")
            self.restored_classes.add(cls.get_path_name())
        self.report["restored_classes"] = len(self.restored_classes)
        self.report["observer_cleanup"] = weapon_observer.snapshot()
        check(self.report["observer_cleanup"]["active_count"] == 0
              and not self.report["observer_cleanup"]["ticker_active"]
              and self.report["observer_cleanup"]["active_scopes"] == 0
              and self.report["observer_cleanup"]["scope_created"] == self.report["observer_cleanup"]["scope_closed"]
              and not self.report["observer_cleanup"]["errors"], "weapon observer was not cleaned up")
        self.widgets.clear()
        self.classes.clear()

    def reload_cycle(self):
        # Controlled workflow: old widgets are removed, routers are torn down,
        # modules reload, then NEW widgets are constructed. No lifecycle event
        # on an existing object is replayed or state migrated implicitly.
        from . import ammo_mixin
        importlib.reload(ammo_mixin)
        importlib.reload(weapon_observer)
        ue.py_gc()
        panel_class = ue.load_class(ASSETS["W_WeaponAmmoAndName"])
        ue.register_declared_mixin(panel_class)
        panel = self.controller.create_widget(panel_class)
        panel.AddToViewport(100)
        weapon_observer.refresh()
        check(ue.get_mixin_profile(panel) == "Python", "reloaded widget lost declared profile")
        check(panel.InventoryItem == self.quickbar.call_function("GetActiveSlotItem"), "reloaded widget lost native owner")
        check(weapon_observer.snapshot()["active_count"] == 1, "duplicate observer after reload")
        self.widgets, self.classes = [panel], [panel_class]
        try:
            ue.new_object(ue.find_class("Object"))
        except TypeError as error:
            check("abstract" in str(error), "unexpected abstract class rejection")
        else:
            raise AssertionError("new_object accepted an abstract class")
        self.report["abstract_class_rejected"] = True
        self.gc_probe = ue.new_object(ue.find_class("LyraInventoryItemInstance"))
        check(self.gc_probe.is_valid(), "GC probe was not live")
        KismetSystemLibrary.CollectGarbage()
        self.phase, self.ready_at = "reload-wait", time.monotonic()

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 120, "weapon fixture timeout in " + self.phase)
            if self.phase == "create":
                for world in ue.all_worlds():
                    if world.get_world_type() not in (1, 3, 5):
                        continue
                    check("/Engine/Maps/Entry" in world.get_path_name(), "requires isolated Entry map")
                    controller = GameplayStatics.GetPlayerController(world, 0)
                    if controller is not None:
                        self.create(world, controller)
                        break
            elif self.phase == "capture" and time.monotonic() - self.ready_at > 0.5:
                image = self.path.with_suffix(".png")
                KismetSystemLibrary.ExecuteConsoleCommand(self.world, 'Shot SHOWUI -nosuffix filename="' + str(image) + '"', self.controller)
                self.report["images"].append(str(image))
                self.phase = "image-wait"
            elif self.phase == "image-wait" and Path(self.report["images"][0]).exists():
                self.cleanup()
                self.report["reload_cycles"] = []
                self.reload_cycle()
            elif self.phase == "reload-wait" and time.monotonic() - self.ready_at > 0.25:
                check(not weapon_observer.valid(self.gc_probe), "requested native UE GC has not collected the unrooted probe")
                before = weapon_observer.snapshot()
                self.cleanup()
                after = weapon_observer.snapshot()
                check(before["native_signals"] >= 0 and after["subscribed"] == after["unsubscribed"], "reload cleanup mismatch")
                self.report["reload_cycles"].append({"status": "passed", "before": before, "after": after,
                                                     "new_widget": True, "native_gc_collected": True,
                                                     "python_housekeeper_gc_executed": True})
                if len(self.report["reload_cycles"]) < 3:
                    self.reload_cycle()
                    return True
                self.report["status"] = "awaiting_shutdown"
                self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
                ue.log("UEP_WEAPON_HUD_DIFFERENTIAL_PASSED")
                ue.request_exit()
                return False
            return True
        except Exception:
            self.report["status"], self.report["error"] = "failed", traceback.format_exc()
            ue.log_error(self.report["error"])
            self.cleanup()
            self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
            ue.log_error("UEP_WEAPON_HUD_DIFFERENTIAL_FAILED")
            ue.request_exit()
            return False

    def finalize(self):
        # Cleanup is sampled before engine teardown; atexit records completion
        # without dereferencing retired widgets or Actors.
        if self.report["status"] == "awaiting_shutdown":
            after = self.report["reload_cycles"][-1]["after"]
            closed = (after["active_count"] == after["active_scopes"] == 0 and
                      not after["ticker_active"] and after["subscribed"] == after["unsubscribed"])
            self.report["status"] = "passed" if closed else "failed"
            self.report["shutdown"] = {"phase": "python_atexit", "owned_resources_closed_before_exit": closed}
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)(
            "UEP_WEAPON_HUD_SHUTDOWN_" + self.report["status"].upper())


prefix = "-UEPLyraWeaponHUDResult="
result_path = next(arg[len(prefix):] for arg in sys.argv if arg.startswith(prefix))
fixture = WeaponValidation(result_path)
atexit.register(fixture.finalize)
ticker = ue.add_ticker(fixture.tick)
