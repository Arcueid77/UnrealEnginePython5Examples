"""Prepared bounded native-nameplate/BP lane; execute only on accepted assets.

Production binding is observed first. UI/configuration cases are explicit
same-class interface calls, not input/team/damage/projection acceptance. An
isolated viewport pair supplies real Destruct/remount, not Indicator pool reuse.
"""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import Vector2D
from . import nameplate_mixin as names
from .weapon_observer import valid
from .nameplate_contract import CASES
from uep_lyra_network_bots import isolate_bots


def check(value, reason):
    if not value:
        raise AssertionError(reason)


def resource(value):
    if not valid(value):
        return ""
    if value.is_a(ue.find_class("MaterialInstanceDynamic")):
        value = value.Parent
    return value.get_path_name() if valid(value) else ""


def visual(widget):
    material = widget.Health.call_function("GetDynamicMaterial")
    return {"name": str(widget.Name.call_function("GetText")),
            "visibility": int(widget.call_function("GetVisibility")),
            "health_resource": resource(widget.Health.Brush.ResourceObject),
            "health_progress": float(material.call_function("K2_GetScalarParameterValue", "Progress")) if valid(material) else 0.0}


class NameplateValidation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.roots, self.case_index = [], 0
        self.report = {"schema_version": 1, "status": "running", "cases": [], "error": None,
            "full_acceptance": False, "packaged_runtime": False, "physical_input_tested": False,
            "native_damage_producer_tested": False, "native_team_reassignment_tested": False,
            "native_projection_parity_tested": False, "actual_production_widget": False,
            "original_bp_baseline": True, "isolated_viewport_lifecycle": True,
            "business_migration_complete": False, "native_unbind_observed": False, "no_late_delivery": False}

    def root(self, value):
        value.add_to_root()
        self.roots.append(value)
        return value

    def descriptor(self, pawn):
        descriptor = self.root(ue.new_object(ue.find_class("IndicatorDescriptor")))
        descriptor.call_function("SetDataObject", pawn)
        descriptor.call_function("SetSceneComponent", pawn.RootComponent)
        descriptor.call_function("SetIndicatorClass", names.CLASS)
        return descriptor

    def create(self, profile, descriptor, visible=False):
        widget = self.root(self.controller.create_widget(self.cls))
        ue.set_mixin_profile(widget, profile)
        widget.AddToViewport(800)
        widget.call_function("SetRenderOpacity", 1.0 if visible else 0.0)
        widget.call_function("BindIndicator", descriptor)
        return widget

    def ready(self):
        statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3):
                continue
            controller = statics.call_function("GetPlayerController", world, 0)
            if not valid(controller) or not valid(controller.call_function("K2_GetPawn")):
                continue
            self.report["bot_isolation"] = isolate_bots(statics, world,
                                                        ue.find_class("LyraPlayerBotController"))
            self.cls = ue.load_class(names.CLASS)
            available, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function(
                "GetAllWidgetsOfClass", world, [], self.cls, False)
            candidates = [value for value in available if valid(value) and
                          value.call_function("GetOwningPlayer") == controller and valid(value.Indicator) and valid(value.Pawn)]
            candidates = [value for value in candidates if ue.get_mixin_profile(value) == "Python" and
                          getattr(value, "_uep_np_live", False) and getattr(value, "_uep_np_init_callbacks", 0) > 0]
            if not candidates:
                continue
            self.world, self.controller = world, controller
            self.candidate = self.root(candidates[0])
            self.original_descriptor, self.pawn = self.candidate.Indicator, self.candidate.Pawn
            self.original_flags = (self.candidate.HideOwnerName, self.candidate.ShowTeamNamesOnly)
            self.baseline = self.create("BlueprintFallback", self.descriptor(self.pawn))
            expected_name = self.pawn.PlayerState.call_function("GetPlayerName")
            self.baseline.call_function("PawnReady")
            self.report["baseline_original_pawnready"] = {
                "expected_pawn": self.pawn.get_path_name(),
                "actual_pawn": self.baseline.Pawn.get_path_name() if valid(self.baseline.Pawn) else None,
                "native_name": str(expected_name), "cached_name": str(self.baseline.NameText),
                "visible_name": str(self.baseline.Name.call_function("GetText"))}
            check(self.baseline.Pawn == self.pawn and str(self.baseline.NameText) == str(expected_name) and
                  str(self.baseline.Name.call_function("GetText")) == str(expected_name),
                  "original BP PawnReady failed: "+repr(self.report["baseline_original_pawnready"]))
            for field in ("HideOwnerName", "ShowTeamNamesOnly"):
                self.baseline.set_property(field, getattr(self.candidate, field))
            self.baseline.call_function("InitializeNameplate", self.pawn, self.pawn.PlayerState.call_function("GetPlayerName"))
            self.pair = (self.candidate, self.baseline)
            self.report.update(actual_production_widget=True, production_widget=self.candidate.get_path_name(),
                original_baseline=self.baseline.get_path_name(), native_immediate_init_callbacks=self.candidate._uep_np_init_callbacks)
            self.enter("initial")
            return

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def compare(self, name, pair=None, expected=None):
        pair = pair or self.pair
        candidate, baseline = map(visual, pair)
        check(candidate == baseline, "nameplate BP difference: "+name+" "+repr((candidate, baseline)))
        check(pair[0].get_class() == pair[1].get_class(), "nameplate class replaced")
        for key, value in (expected or {}).items():
            check(candidate[key] == value, "nameplate expected state differs: "+name+" "+key)
        check(CASES[self.case_index] == name, "nameplate fixture case order differs")
        self.report["cases"].append({"name": name, "passed": True, "class_preserved": True,
                                     "python": candidate, "blueprint": baseline})
        self.case_index += 1
        ue.log("UEP_NAMEPLATE_CASE_PASSED " + name)

    def configure_visible(self):
        for widget in self.pair:
            widget.set_property("HideOwnerName", False)
            widget.set_property("ShowTeamNamesOnly", False)
            widget.call_function("InitializeNameplate", self.pawn, self.pawn.PlayerState.call_function("GetPlayerName"))

    def finish(self, error=None):
        try:
            for widget in getattr(self, "lifecycle", ()):
                widget.RemoveFromParent()
            if valid(getattr(self, "baseline", None)):
                self.baseline.call_function("UnbindIndicator", self.baseline.Indicator)
                self.baseline.RemoveFromParent()
            for value in self.roots:
                if valid(value):
                    value.remove_from_root()
            self.roots.clear()
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic()-self.started)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_NAMEPLATE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["shutdown"] = names.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        try:
            if self.report["status"] == "passed":
                from .nameplate_contract import validate
                validate(self.report)
        except Exception as error:
            self.report.update(status="failed", error=str(error))
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_NAMEPLATE_SHUTDOWN_"+self.report["status"].upper())

    def tick(self, delta):
        try:
            check(time.monotonic()-self.started < 160, "nameplate total timeout")
            if self.phase == "ready":
                self.ready()
                return True
            elapsed = time.monotonic()-self.phase_started
            check(elapsed < 15, "nameplate phase timeout: "+self.phase)
            if elapsed < .7:
                return True
            if self.phase == "initial":
                self.compare(CASES[0])
                self.configure_visible()
                for widget in self.pair:
                    widget.call_function("SetNameText", "UEP NAMEPLATE")
                self.compare(CASES[1], expected={"name": "UEP NAMEPLATE"})
                health = names.health_for(self.pawn)
                check(valid(health), "nameplate native health missing")
                percent = float(health.call_function("GetHealthNormalized"))
                for widget in self.pair:
                    widget.call_function("SetHealthBarPercent", percent)
                self.compare(CASES[2], expected={"health_progress": percent})
                for widget in self.pair:
                    widget.set_property("TeamId", 1)
                    widget.call_function("SetTeamVisuals")
                self.enter("red")
            elif self.phase == "red":
                self.compare(CASES[3])
                check("RedTeam_HealthBar" in visual(self.candidate)["health_resource"], "nameplate red material absent")
                for widget in self.pair:
                    widget.set_property("TeamId", 2)
                    widget.call_function("SetTeamVisuals")
                self.enter("blue")
            elif self.phase == "blue":
                self.compare(CASES[4])
                check("BlueTeam_HealthBar" in visual(self.candidate)["health_resource"], "nameplate blue material absent")
                self.owner_pawn = self.controller.call_function("K2_GetPawn")
                self.enemy = next((pawn for pawn in self.world.all_actors() if pawn.is_a(ue.find_class("Pawn")) and
                    names.compare_teams(self.candidate, pawn, self.controller) == 1 and
                    valid(names.extension_for(pawn)) and valid(pawn.PlayerState)), None)
                check(valid(self.enemy), "native opposing-team pawn absent")
                for widget in self.pair:
                    widget.call_function("BindIndicator", self.descriptor(self.owner_pawn))
                    widget.set_property("HideOwnerName", True)
                    widget.call_function("UpdateVisibility")
                self.compare(CASES[5], expected={"visibility": 1})
                for widget in self.pair:
                    widget.set_property("HideOwnerName", False)
                    widget.set_property("ShowTeamNamesOnly", True)
                    widget.call_function("BindIndicator", self.descriptor(self.enemy))
                self.enter("enemy")
            elif self.phase == "enemy":
                self.compare(CASES[6], expected={"visibility": 1})
                for widget in self.pair:
                    widget.set_property("ShowTeamNamesOnly", False)
                    widget.call_function("UpdateVisibility")
                self.compare(CASES[7], expected={"visibility": 1})
                self.report["image"] = str(self.path.parent/"nameplate.png")
                # A dedicated visible pair displays the native player's label;
                # it is not native indicator projection parity.
                self.lifecycle = [self.create(profile, self.descriptor(self.owner_pawn), True)
                                  for profile in ("Python", "BlueprintFallback")]
                for index, widget in enumerate(self.lifecycle):
                    widget.set_property("HideOwnerName", False)
                    widget.set_property("ShowTeamNamesOnly", False)
                    widget.call_function("InitializeNameplate", self.owner_pawn, "UEP NAMEPLATE")
                    widget.SetPositionInViewport(Vector2D(X=180.0+index*600.0, Y=280.0), False)
                    widget.SetDesiredSizeInViewport(Vector2D(X=300.0, Y=100.0))
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="'+self.report["image"]+'"', self.controller)
                ue.set_mixin_profile(self.candidate, "BlueprintFallback")
                self.candidate.call_function(names.RESUME)
                self.baseline.call_function(names.RESUME)
                self.enter("fallback")
            elif self.phase == "fallback":
                self.compare(CASES[8])
                ue.set_mixin_profile(self.candidate, "Python")
                self.candidate.call_function(names.RESUME)
                self.baseline.call_function(names.RESUME)
                self.enter("python")
            elif self.phase == "python":
                self.compare(CASES[9])
                for widget in self.pair:
                    widget.call_function("BindIndicator", self.original_descriptor if widget is self.candidate else self.descriptor(self.pawn))
                    widget.set_property("HideOwnerName", self.original_flags[0])
                    widget.set_property("ShowTeamNamesOnly", self.original_flags[1])
                    widget.call_function("InitializeNameplate", self.pawn, self.pawn.PlayerState.call_function("GetPlayerName"))
                self.before_health = self.candidate._uep_np_health_callbacks
                health = names.health_for(self.pawn)
                # Explicit synthetic delegate notification, no native Health
                # write and no native damage-producer claim.
                health.broadcast("OnHealthChanged", health, 100.0, 100.0, self.pawn)
                check(self.candidate._uep_np_health_callbacks == self.before_health+1, "repeated nameplate binding is not exact-once")
                self.compare(CASES[10])
                self.original_descriptor.call_function("UnregisterIndicator")
                self.enter("unregister")
            elif self.phase == "unregister":
                if self.candidate.Pawn is not None or self.candidate._uep_np_live:
                    return True
                self.report["native_unbind_observed"] = True
                self.baseline.call_function("UnbindIndicator", self.baseline.Indicator)
                before = [visual(widget) for widget in self.pair]
                health = names.health_for(self.pawn)
                count = self.candidate._uep_np_health_callbacks
                health.broadcast("OnHealthChanged", health, 100.0, 100.0, self.pawn)
                check([visual(widget) for widget in self.pair] == before and self.candidate._uep_np_health_callbacks == count,
                      "unbound nameplate received a late event")
                self.report["no_late_delivery"] = True
                self.compare(CASES[11])
                for widget in self.lifecycle:
                    widget.RemoveFromParent()
                self.enter("destruct")
            elif self.phase == "destruct":
                check(not self.lifecycle[0]._uep_np_live, "viewport Destruct retained nameplate bindings")
                self.compare(CASES[12], self.lifecycle)
                for widget in self.lifecycle:
                    widget.AddToViewport(800)
                    widget.call_function(names.RESUME)
                self.enter("remount")
            elif self.phase == "remount":
                check(self.lifecycle[0]._uep_np_live, "native viewport remount did not resume nameplate")
                self.compare(CASES[13], self.lifecycle)
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


result = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("-UEPNameplateResult=")), None)
if not result:
    raise RuntimeError("explicit nameplate result required")
validation = NameplateValidation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
