"""Test-only 0.10 adapter for real native weapon/HUD network checkpoints.

Original Pistol/Rifle/Shotgun definitions do not reference W_Reticle_AmmoBar.
Its test-owned overlay and original-BP comparison initialize from the real
weapon instance found on Lyra's production ammo counter. Definitions stay intact.
Clicking the bound BP event is programmatic, not physical touchscreen proof.
No ammo/inventory/ability state is set by this adapter.
"""

import unreal_engine as ue
from unreal_engine.structs import Geometry
from unreal_engine.structs import Vector2D

from uep_lyra_hud import weapon_observer
from uep_lyra_hud import state as hud_state
from uep_lyra_hud.fire_button_mixin import CLICK_EVENT
from uep_lyra_network_protocol import require
from uep_lyra_combat_hud_protocol import FIRE_PROFILES


RETICLE = "/ShooterCore/UserInterface/HUD/W_Reticle_AmmoBar.W_Reticle_AmmoBar_C"
FIRE_BUTTON = "/ShooterCore/UserInterface/W_FireButton.W_FireButton_C"


def material_values(widget):
    material = widget.ProgressBorder.call_function("GetDynamicMaterial")
    color = material.call_function("K2_GetVectorParameterValue", "ActiveRange")
    return {"segments": float(material.call_function("K2_GetScalarParameterValue", "Segments")),
            "range": [float(getattr(color, key)) for key in ("r", "g", "b", "a")]}


def agrees(left, right):
    return (abs(left["segments"] - right["segments"]) < 1e-6
            and all(abs(a - b) < 1e-6 for a, b in zip(left["range"], right["range"])))


class CombatHUDProbe:
    def __init__(self, debug_spread=False, reticle_hosts=False):
        self.world_token = None
        self.baseline = self.button = None
        self.reticle = None
        self.baseline_weapon = None
        self.fire_clicks = {"Python": 0, "BlueprintFallback": 0}
        self.selected_profile = "Python"
        self.debug_spread_enabled = debug_spread
        self.debug = self.debug_baseline = None
        self.debug_peak = 0.0
        self.debug_samples = 0
        self.production_reticle_baseline = None
        self.production_reticle_weapon = None
        self.reticle_hosts_enabled = reticle_hosts

    def close(self):
        for widget in (self.baseline, self.button, self.reticle, self.debug, self.debug_baseline, self.production_reticle_baseline):
            if weapon_observer.valid(widget):
                widget.RemoveFromParent()
                widget.remove_from_root()
        self.baseline = self.button = None
        self.reticle = None
        self.debug = self.debug_baseline = None
        self.production_reticle_baseline = self.production_reticle_weapon = None
        self.baseline_weapon = self.world_token = None

    def _create(self, controller, world_token):
        self.close()
        reticle_class, button_class = ue.load_class(RETICLE), ue.load_class(FIRE_BUTTON)
        ue.register_declared_mixin(reticle_class)
        ue.register_declared_mixin(button_class)
        self.baseline = controller.create_widget(reticle_class)
        self.baseline.add_to_root()
        ue.set_mixin_profile(self.baseline, "BlueprintFallback")
        self.reticle = controller.create_widget(reticle_class)
        self.reticle.AddToViewport(200)
        self.reticle.SetPositionInViewport(Vector2D(X=240.0, Y=140.0), False)
        self.reticle.SetDesiredSizeInViewport(Vector2D(X=160.0, Y=160.0))
        self.button = controller.create_widget(button_class)
        self.button.add_to_root()
        require(weapon_observer.valid(self.button.ActionTouchButton), "FireButton has no authored child")
        self.world_token = world_token
        self.selected_profile = "Python"
        if self.debug_spread_enabled:
            from uep_lyra_hud.debug_spread_mixin import CLASS
            cls = ue.load_class(CLASS)
            ue.register_declared_mixin(cls)
            self.debug_baseline = controller.create_widget(cls)
            self.debug_baseline.add_to_root()
            ue.set_mixin_profile(self.debug_baseline, "BlueprintFallback")
            self.debug = controller.create_widget(cls)
            self.debug.AddToViewport(201)
            self.debug.SetPositionInViewport(Vector2D(X=20.0, Y=75.0), False)
            self.debug.SetDesiredSizeInViewport(Vector2D(X=140.0, Y=40.0))

    def observe(self, controller, player, weapon):
        if self.world_token != player["world_token"]:
            self._create(controller, player["world_token"])
        matches = []
        for path in weapon_observer.snapshot()["active_widgets"]:
            widget = ue.find_object(path)
            if (weapon_observer.valid(widget) and widget.get_class().get_name() in (
                    "W_AmmoCounter_Pistol_C", "W_AmmoCounter_Rifle_C", "W_AmmoCounter_Shotgun_C")
                    and widget.call_function("GetOwningPlayer") == controller
                    and weapon_observer.path(widget.InventoryInstance) == weapon["item"]):
                matches.append(widget)
        require(len(matches) <= 1, "Multiple production ammo counters own one native item")
        if not matches:
            return None
        source, widget = matches[0], self.reticle
        if self.baseline_weapon != weapon_observer.path(source.WeaponInstance):
            for target in (self.baseline, widget):
                target.call_function("InitializeFromWeapon", source.WeaponInstance)
            if self.debug_spread_enabled:
                for target in (self.debug_baseline, self.debug):
                    target.call_function("InitializeFromWeapon", source.WeaponInstance)
            self.baseline_weapon = weapon_observer.path(source.WeaponInstance)
        require(weapon_observer.path(widget.InventoryInstance) == weapon["item"],
                "Native reticle initialization selected the wrong inventory")
        self.baseline.call_function("Tick", Geometry(), 0.016)
        original, actual = material_values(self.baseline), material_values(widget)
        expected = {"segments": float(weapon["maximum"] * 4 + 1),
                    "range": [0.0, weapon["magazine"] / weapon["maximum"] * 0.25
                              if weapon["maximum"] else 0.0, 0.0, 1.0]}
        if not agrees(actual, original) or not agrees(actual, expected):
            return None
        health_widgets = [ue.find_object(path) for path in hud_state.snapshot()["active_widgets"]]
        health_widgets = [entry for entry in health_widgets if weapon_observer.valid(entry)
                          and entry.call_function("GetOwningPlayer") == controller]
        require(len(health_widgets) == 1, "Missing/duplicate production health presenter")
        health_widget = health_widgets[0]
        text = str(health_widget.HealthNumber.call_function("GetText")).replace(",", "").strip()
        if not text:
            return None
        health_visuals = {"widget": health_widget.get_path_name(),
                          "controller": controller.get_path_name(),
                          "current": float(text),
                          "target": float(health_widget.HealthNumber.call_function("GetTargetValue")),
                          "updated": float(health_widget.BarFillMID.call_function("K2_GetScalarParameterValue", "Health_Updated"))}
        if (abs(health_visuals["current"] - player["health"]) > 0.05
                or abs(health_visuals["target"] - player["health"]) > 0.05
                or abs(health_visuals["updated"] - player["health"] / player["max_health"]) > 0.001):
            return None
        result = {"reticle": {"widget": widget.get_path_name(), "class": widget.get_class().get_name(),
                             "profile": ue.get_mixin_profile(widget),
                             "controller": controller.get_path_name(), "item": weapon["item"],
                             "production_widget": False, "origin": "test-owned-ammo-bar-overlay",
                             "source_widget": source.get_path_name(), "source_class": source.get_class().get_name(),
                             "weapon_instance": self.baseline_weapon, "python": actual,
                             "blueprint": original, "native": expected},
                "health_visuals": health_visuals,
                "fire_button": {"widget": self.button.get_path_name(),
                                "class": self.button.get_class().get_name(),
                                "controller": self.button.call_function("GetOwningPlayer").get_path_name(),
                                "profile": ue.get_mixin_profile(self.button),
                                "clicks": dict(self.fire_clicks), "entry": CLICK_EVENT,
                                "physical_touch_tested": False, "inventory_written": False}}
        if self.debug_spread_enabled:
            from uep_lyra_hud.debug_spread_mixin import format_angle
            self.debug_baseline.call_function("Tick", Geometry(), 0.016)
            angle = float(self.debug.call_function("ComputeSpreadAngle"))
            expected_text = str(format_angle(angle))
            original_text = str(self.debug_baseline.CommonTextBlock_52.call_function("GetText"))
            actual_text = str(self.debug.CommonTextBlock_52.call_function("GetText"))
            ticks = getattr(self.debug, "_uep_debug_spread_ticks", 0)
            # Do not manually invoke Python Tick to manufacture automatic Tick
            # evidence. Native Slate/game lifecycle owns the shown candidate.
            if actual_text != expected_text or original_text != expected_text or ticks <= 0:
                return None
            require(weapon_observer.path(self.debug.InventoryInstance) == weapon["item"], "Debug widget crossed inventory owner")
            self.debug_peak = max(self.debug_peak, angle)
            self.debug_samples += 1
            result["debug_spread"] = {"class": self.debug.get_class().get_name(), "profile": ue.get_mixin_profile(self.debug),
                                      "controller": controller.get_path_name(), "item": weapon["item"],
                                      "weapon_instance": self.baseline_weapon, "native_angle": angle,
                                      "native": expected_text, "blueprint": original_text, "python": actual_text,
                                      "python_ticks": ticks, "samples": self.debug_samples, "peak_angle": self.debug_peak,
                                      "production_widget": False, "origin": "test-owned-debug-spread-overlay",
                                      "python_tick_called_by_probe": False, "spread_written": False}
        # New optional assets may be absent in older stages. When a production
        # Python reticle is active, compare the actual widget, not an overlay.
        from uep_lyra_hud import weapon_reticle_mixin
        candidates = [ue.find_object(path) for path in weapon_reticle_mixin.snapshot()["active_widgets"]]
        candidates = [entry for entry in candidates if weapon_observer.valid(entry)
                      and entry.call_function("GetOwningPlayer") == controller
                      and weapon_observer.path(entry.InventoryInstance) == weapon["item"]]
        require(len(candidates) <= 1, "Multiple production reticles own one weapon")
        if candidates:
            actual_widget = candidates[0]
            cls = actual_widget.get_class()
            if (not weapon_observer.valid(self.production_reticle_baseline)
                    or self.production_reticle_baseline.get_class() != cls):
                if weapon_observer.valid(self.production_reticle_baseline):
                    self.production_reticle_baseline.remove_from_root()
                self.production_reticle_baseline = controller.create_widget(cls)
                self.production_reticle_baseline.add_to_root()
                ue.set_mixin_profile(self.production_reticle_baseline, "BlueprintFallback")
                self.production_reticle_weapon = None
            if self.production_reticle_weapon != self.baseline_weapon:
                self.production_reticle_baseline.call_function("InitializeFromWeapon", source.WeaponInstance)
                self.production_reticle_weapon = self.baseline_weapon
            self.production_reticle_baseline.call_function("Tick", Geometry(), 0.016)
            def shape(target):
                return {"radius": float(target.CrossHairs.get_property("Radius")),
                        "width": float(target.SBOuterReticle.get_property("WidthOverride")),
                        "height": float(target.SBOuterReticle.get_property("HeightOverride"))}
            original, actual = shape(self.production_reticle_baseline), shape(actual_widget)
            radius = float(actual_widget.call_function("ComputeMaxScreenspaceSpreadRadius"))
            expected = dict(zip(("radius", "width", "height"), weapon_reticle_mixin.geometry(str(actual_widget.UEPReticleKind), radius)))
            if not all(abs(original[key] - actual[key]) < 0.05 and abs(actual[key] - expected[key]) < 0.05 for key in expected):
                return None
            result["production_reticle"] = {"production_widget": True, "class": cls.get_name(),
                                            "profile": ue.get_mixin_profile(actual_widget),
                                            "controller": controller.get_path_name(), "item": weapon["item"],
                                            "kind": str(actual_widget.UEPReticleKind), "python": actual,
                                            "blueprint": original, "native": expected,
                                            "automatic_python_ticks": actual_widget._uep_reticle_ticks}
        if self.reticle_hosts_enabled:
            host = self.observe_host(controller, source)
            if host is None:
                return None
            result["reticle_host"] = host
        return result

    def observe_host(self, controller, source):
        from uep_lyra_hud import reticle_host_mixin
        candidates = [ue.find_object(path) for path in reticle_host_mixin.snapshot()["active_widgets"]]
        candidates = [host for host in candidates if weapon_observer.valid(host)
                      and host.call_function("GetOwningPlayer") == controller]
        require(len(candidates) <= 1, "Multiple production hosts own one controller")
        if not candidates:
            return None
        host = candidates[0]
        native_weapon = source.WeaponInstance
        if weapon_observer.path(host.CurrentInstance) != weapon_observer.path(native_weapon):
            return None
        fragment = source.InventoryInstance.call_function("FindFragmentByClass", ue.find_class("InventoryFragment_ReticleConfig"))
        require(weapon_observer.valid(fragment), "Native item lost reticle configuration")
        expected = [cls.get_name() for cls in fragment.ReticleWidgets]
        children = list(host.SpawnedWidgets)
        if [widget.get_class().get_name() for widget in children] != expected:
            return None
        pawn = controller.get_controlled_pawn()
        health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        if host.CurrentHealthComponent != health:
            return None
        return {"production_widget": True, "class": host.get_class().get_name(), "profile": ue.get_mixin_profile(host),
                "controller": controller.get_path_name(), "item": source.InventoryInstance.get_path_name(),
                "weapon_instance": native_weapon.get_path_name(), "native_config_classes": expected,
                "children": [{"class": widget.get_class().get_name(), "item": weapon_observer.path(widget.InventoryInstance),
                              "weapon_instance": weapon_observer.path(widget.WeaponInstance),
                              "horizontal": int(widget.Slot.HorizontalAlignment), "vertical": int(widget.Slot.VerticalAlignment)}
                             for widget in children],
                "overlay_children": int(host.WidgetStack.call_function("GetChildrenCount")),
                "native_dead": bool(health.call_function("IsDeadOrDying")),
                "visibility": int(host.VisWrapper.call_function("GetVisibility")),
                "automatic_python_ticks": host._uep_reticle_host_ticks,
                "python_tick_called_by_probe": False, "weapon_event_called_by_probe": False}

    def select_fire_profile(self, phase):
        require(weapon_observer.valid(self.button), "FireButton fixture is not ready")
        self.selected_profile = FIRE_PROFILES.get(phase, "Python")
        ue.set_mixin_profile(self.button, self.selected_profile)

    def fire(self, pressed):
        require(weapon_observer.valid(self.button), "FireButton expired during input")
        if pressed:
            self.button.call_function(CLICK_EVENT, self.button.ActionTouchButton)
            self.fire_clicks[self.selected_profile] += 1
