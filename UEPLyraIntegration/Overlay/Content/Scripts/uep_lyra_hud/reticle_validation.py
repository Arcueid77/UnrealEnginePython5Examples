"""Opt-in 0.10 pilot: actual BP/Python reticle material and lifetime comparison."""

import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.classes import GameplayStatics, KismetSystemLibrary
from unreal_engine.structs import Geometry

from . import weapon_observer
from .ammo_mixin import MAGAZINE_AMMO, MAGAZINE_SIZE
from .weapon_validation_helpers import set_stat


ASSET = "/ShooterCore/UserInterface/HUD/W_Reticle_AmmoBar.W_Reticle_AmmoBar_C"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def material_state(widget):
    material = widget.ProgressBorder.call_function("GetDynamicMaterial")
    return {"segments": float(material.call_function("K2_GetScalarParameterValue", "Segments")),
            "range": str(material.call_function("K2_GetVectorParameterValue", "ActiveRange"))}


class ReticleValidation:
    def __init__(self, result):
        self.path = Path(result)
        self.started = time.monotonic()
        self.phase = "create"
        self.created_at = None
        self.widgets = []
        self.cls = None
        self.report = {"schema_version": 1, "status": "running", "asset": ASSET,
                       "cases": [], "original_bp_compared": True, "network_acceptance": False,
                       "full_acceptance": False}

    def create(self, world, controller):
        self.world, self.controller = world, controller
        self.cls = ue.load_class(ASSET)
        ue.register_declared_mixin(self.cls)
        for index, profile in enumerate(("BlueprintFallback", "Python")):
            widget = controller.create_widget(self.cls)
            if profile == "BlueprintFallback":
                ue.set_mixin_profile(widget, profile)
            widget.AddToViewport(100)
            from unreal_engine.structs import Vector2D
            widget.SetPositionInViewport(Vector2D(X=300.0 + index * 550.0, Y=300.0), False)
            widget.SetDesiredSizeInViewport(Vector2D(X=300.0, Y=300.0))
            self.widgets.append(widget)
        self.items = []
        for maximum in (8, 30):
            item = ue.new_object(ue.find_class("LyraInventoryItemInstance"), controller)
            self.items.append(item)
            set_stat(item, MAGAZINE_SIZE, maximum)
            for widget in self.widgets:
                widget.set_property("InventoryInstance", item)
                widget.call_function("OnWeaponInitialized")
            for current in (0, 1, 5, maximum, maximum + 3):
                set_stat(item, MAGAZINE_AMMO, current)
                for widget in self.widgets:
                    widget.call_function("Tick", Geometry(), 0.016)
                weapon_observer.refresh()
                baseline, candidate = (material_state(widget) for widget in self.widgets)
                check(baseline == candidate, "reticle material differs: " + repr((baseline, candidate)))
                check(candidate["segments"] == maximum * 4 + 1, "reticle segments differ from authored formula")
                self.report["cases"].append({"maximum": maximum, "current": current,
                                              "bp": baseline, "python": candidate})
        candidate = self.widgets[1]
        ue.set_mixin_profile(candidate, "BlueprintFallback")
        check(weapon_observer.snapshot()["active_count"] == 0, "reticle profile teardown retained observation")
        ue.set_mixin_profile(candidate, "Python")
        candidate.call_function("Tick", Geometry(), 0.016)
        check(weapon_observer.snapshot()["active_count"] == 1, "reticle Profile return did not resume")
        self.report["live_profile_round_trip"] = True
        self.report["class_identity_preserved"] = all(widget.get_class() == self.cls for widget in self.widgets)
        self.created_at, self.phase = time.monotonic(), "capture"

    def cleanup(self):
        for widget in self.widgets:
            if weapon_observer.valid(widget):
                widget.RemoveFromParent()
        if self.cls is not None:
            ue.unregister_mixin(self.cls)
        final = weapon_observer.snapshot()
        check(final["active_count"] == 0 and final["active_scopes"] == 0 and not final["ticker_active"] and not final["errors"],
              "reticle retained observer state")
        self.report["observer_cleanup"] = final

    def finish(self, error=None):
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report["status"], self.report["error"] = ("failed" if error else "passed"), error
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_RETICLE_DIFFERENTIAL_" + self.report["status"].upper())
        ue.request_exit()

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 90, "reticle fixture timed out")
            if self.phase == "create":
                for world in ue.all_worlds():
                    if world.get_world_type() not in (1, 3, 5):
                        continue
                    check("/Engine/Maps/Entry" in world.get_path_name(), "reticle fixture requires Entry")
                    controller = GameplayStatics.GetPlayerController(world, 0)
                    if controller is not None:
                        self.create(world, controller)
                        break
            elif self.phase == "capture" and time.monotonic() - self.created_at > 0.3:
                image = self.path.with_suffix(".png")
                KismetSystemLibrary.ExecuteConsoleCommand(self.world, 'Shot SHOWUI -nosuffix filename="' + str(image) + '"', self.controller)
                self.report["image"] = str(image)
                self.phase = "image"
            elif self.phase == "image" and Path(self.report["image"]).exists():
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPReticleAmmoResult="
result = next(arg[len(prefix):] for arg in sys.argv if arg.startswith(prefix))
validation = ReticleValidation(result)
ticker = ue.add_ticker(validation.tick)
