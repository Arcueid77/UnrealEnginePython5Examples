"""Production Dash UI vs original BP, with natural UMG/message/lifetime events."""

import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage, Vector2D
from . import dash_cooldown_mixin as dash
from .weapon_observer import valid
from uep_lyra_network_bots import isolate_bots

CASES = ("initial-ready", "typed-owner-duration", "foreign-owner-ignored",
         "repeated-duration-restarts", "paused-game-time-frozen", "native-countdown-completed",
         "blueprint-profile-resume", "python-profile-resume", "resumed-owner-exact-once",
         "destruct-no-late-delivery", "same-widget-native-reconstruct")


def check(value, message):
    if not value:
        raise AssertionError(message)


def model(widget):
    return [float(widget.Duration), float(widget.StartTime), bool(widget.Charging)]


def state(widget):
    return {"duration": float(widget.Duration), "start": float(widget.StartTime), "charging": bool(widget.Charging),
            "visibility": int(widget.CenteringOvr.call_function("GetVisibility")),
            "glow": float(widget.BarGlow.call_function("GetDynamicMaterial").call_function("K2_GetScalarParameterValue", "AnimateArcFill")),
            "fill": float(widget.BarFill.call_function("GetDynamicMaterial").call_function("K2_GetScalarParameterValue", "AnimateArcFill")),
            "active_animation": bool(widget.call_function("IsAnimationPlaying", widget.InactiveToActive)),
            "inactive_animation": bool(widget.call_function("IsAnimationPlaying", widget.ActiveToInactive))}


class DashValidation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.widgets, self.helper, self.foreign, self.paused = [], None, None, False
        self.lifecycle_pair = False
        self.report = {"schema_version": 1, "status": "running", "cases": [], "full_acceptance": False,
                       "network_acceptance": False, "native_dash_producer_tested": False,
                       "dead_health_tested": False, "widget_tick_invoked_by_fixture": False,
                       "lifecycle_event_invoked_by_fixture": False, "production_widget": None,
                       "material_absolute_tolerance": 0.00001, "compiled_vm_transport": True}
        atexit.register(self.finalize)

    def write(self):
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()
        self.ticks_at_entry = self.candidate._uep_dash_ticks

    def broadcast(self, duration, instigator=None):
        self.helper.call_function("BroadcastDuration", self.router, GameplayTag(TagName=dash.CHANNEL),
                                  LyraInteractionDurationMessage(Instigator=instigator or self.pawn, Duration=duration))

    def compare(self, name, ticks=False):
        actual, original = state(self.candidate), state(self.baseline)
        for key in actual:
            if key in ("glow", "fill"):
                check(abs(actual[key] - original[key]) <= self.report["material_absolute_tolerance"],
                      "Dash material mismatch " + key + ": " + repr((actual, original)))
            else:
                check(actual[key] == original[key], "Dash BP/Python mismatch " + key + ": " + repr((actual, original)))
        if ticks:
            check(self.candidate._uep_dash_ticks > self.ticks_at_entry + 1, "automatic UMG Tick did not reach Dash Python")
        check(self.candidate.get_class() == self.baseline.get_class(), "Dash class replaced")
        self.report["cases"].append({"name": name, "python": actual, "blueprint": original,
                                     "automatic_ticks": self.candidate._uep_dash_ticks,
                                     "widget": self.candidate.get_path_name(),
                                     "test_owned_lifecycle_widget": self.lifecycle_pair,
                                     "profile": str(ue.get_mixin_profile(self.candidate))})

    def ready(self):
        statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge):
                continue
            isolate_bots(statics, world, ue.find_class("LyraPlayerBotController"))
            snapshot = bridge.call_function("CaptureSnapshot")
            if not (snapshot.bExperienceLoaded and snapshot.bHealthReady and not snapshot.bDamageImmune):
                continue
            controller = statics.call_function("GetPlayerController", world, 0)
            cls = ue.load_class(dash.CLASS)
            widgets, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("GetAllWidgetsOfClass", world, [], cls, False)
            candidates = [widget for widget in widgets if widget.call_function("GetOwningPlayer") == controller]
            if len(candidates) != 1:
                self.report["readiness"] = {"candidate_count": len(candidates), "world": world.get_path_name()}
                continue
            self.world, self.statics, self.controller = world, statics, controller
            self.pawn = controller.get_controlled_pawn()
            self.candidate = candidates[0]
            check(str(ue.get_mixin_profile(self.candidate)) == "Python", "production Dash default not Python")
            self.report["production_widget"] = self.candidate.get_path_name()
            self.baseline = controller.create_widget(cls)
            self.widgets = [self.candidate, self.baseline]
            for widget in self.widgets:
                widget.add_to_root()
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.AddToViewport(450)
            self.baseline.SetPositionInViewport(Vector2D(X=800.0, Y=550.0), False)
            self.baseline.SetDesiredSizeInViewport(Vector2D(X=160.0, Y=100.0))
            self.baseline.call_function(dash.RESUME)
            self.helper = ue.new_object(self.candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetGameInstanceSubsystem", world, ue.find_class("GameplayMessageSubsystem"))
            check(valid(self.router), "Dash native message subsystem missing")
            self.foreign = world.actor_spawn(ue.find_class("Actor"))
            self.enter("initial")
            return

    def cleanup(self):
        if self.paused:
            self.statics.call_function("SetGamePaused", self.world, False)
            self.paused = False
        for widget in self.widgets:
            if valid(widget):
                widget.RemoveFromParent()
                widget.remove_from_root()
        self.widgets = []
        if valid(self.helper):
            self.helper.remove_from_root()
            self.helper = None
        if valid(self.foreign):
            self.foreign.actor_destroy()
            self.foreign = None

    def finish(self, error=None):
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic() - self.started)
        self.write()
        (ue.log_error if error else ue.log)("UEP_DASH_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        final = dash.snapshot()
        self.report["shutdown"] = final
        if final["active_count"] or final["scopes_created"] != final["scopes_closed"] or final["errors"]:
            self.report.update(status="failed", error="Dash scopes remained after shutdown")
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_SHUTDOWN_" + self.report["status"].upper())

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 200, "Dash total timeout")
            if self.phase == "ready":
                self.ready()
                return True
            elapsed = time.monotonic() - self.phase_started
            check(elapsed < 20, "Dash phase timeout: " + self.phase)
            if self.phase == "initial" and elapsed > 1.0:
                self.compare("initial-ready", True)
                check(not self.candidate.Charging and state(self.candidate)["fill"] == 1.0, "Dash not initially ready")
                before = self.candidate._uep_dash_messages
                self.broadcast(4.0)
                check(self.candidate._uep_dash_messages == before + 1, "Dash owner delivery not exact-once")
                self.enter("owner")
            elif self.phase == "owner" and elapsed > 0.4:
                self.compare("typed-owner-duration", True)
                before = [model(widget) for widget in self.widgets]
                foreign = self.candidate._uep_dash_foreign
                self.broadcast(77.0, self.foreign)
                check([model(widget) for widget in self.widgets] == before, "foreign Dash changed model")
                check(self.candidate._uep_dash_foreign == foreign + 1, "Dash foreign filter missing")
                self.compare("foreign-owner-ignored")
                self.broadcast(2.5)
                self.enter("repeat")
            elif self.phase == "repeat" and elapsed > 0.4:
                self.compare("repeated-duration-restarts", True)
                check(self.statics.call_function("SetGamePaused", self.world, True), "Dash pause rejected")
                self.paused = True
                self.enter("pause-settle")
            elif self.phase == "pause-settle" and elapsed > 0.2:
                self.frozen_clock = dash.game_time(self.candidate)
                self.frozen = [state(widget) for widget in self.widgets]
                self.enter("paused")
            elif self.phase == "paused" and elapsed > 1.1:
                check(dash.game_time(self.candidate) == self.frozen_clock, "Dash game time advanced while paused")
                check([state(widget) for widget in self.widgets] == self.frozen, "Dash countdown changed while paused")
                self.compare("paused-game-time-frozen")
                self.report["paused_wall_seconds"] = elapsed
                self.report["image"] = str(self.path.parent / "dash-cooldown.png")
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="' + self.report["image"] + '"', self.controller)
                self.enter("paused-shot")
            elif self.phase == "paused-shot" and elapsed > 0.4:
                self.statics.call_function("SetGamePaused", self.world, False)
                self.paused = False
                self.enter("expiry")
            elif self.phase == "expiry" and not any(widget.Charging for widget in self.widgets) and elapsed > 0.5:
                self.compare("native-countdown-completed", True)
                ue.set_mixin_profile(self.candidate, "BlueprintFallback")
                self.candidate.call_function(dash.RESUME)
                self.enter("fallback")
            elif self.phase == "fallback" and elapsed > 0.25:
                self.compare("blueprint-profile-resume")
                ue.set_mixin_profile(self.candidate, "Python")
                self.candidate.call_function(dash.RESUME)
                self.enter("python")
            elif self.phase == "python" and elapsed > 0.25:
                self.compare("python-profile-resume", True)
                before = self.candidate._uep_dash_messages
                self.broadcast(0.6)
                check(self.candidate._uep_dash_messages == before + 1, "Dash resumed owner duplicated")
                self.enter("resumed")
            elif self.phase == "resumed" and elapsed > 0.25:
                self.compare("resumed-owner-exact-once", True)
                # Production Dash is a UIExtension/DynamicEntryBox pooled Slate
                # entry, NOT a Panel/viewport child. RemoveFromParent cannot
                # dismantle that native owner's retained Slate cache. Exercise
                # actual Destruct/remount separately on a same-class viewport
                # pair; do not fabricate a production-remount result.
                cls = self.candidate.get_class()
                self.candidate = self.controller.create_widget(cls)
                self.baseline = self.controller.create_widget(cls)
                self.lifecycle_widgets = [self.candidate, self.baseline]
                for widget in self.lifecycle_widgets:
                    widget.add_to_root()
                    widget.AddToViewport(450)
                ue.set_mixin_profile(self.baseline, "BlueprintFallback")
                self.baseline.call_function(dash.RESUME)
                self.widgets.extend(self.lifecycle_widgets)
                self.lifecycle_pair = True
                self.report["lifecycle_entry"] = "test-owned same-class viewport pair; production mount uses UIExtension pool"
                self.enter("lifecycle-ready")
            elif self.phase == "lifecycle-ready" and elapsed > 0.3:
                original_proxy = getattr(self.baseline, dash.PROXY)
                check(valid(original_proxy) and original_proxy.call_function("IsActive"), "original Dash listener not armed before Destruct")
                for widget in self.lifecycle_widgets:
                    widget.RemoveFromParent()
                check(self.candidate._uep_dash_scope is None, "native Destruct did not close Dash listener")
                check(getattr(self.baseline, dash.PROXY) is None and not original_proxy.call_function("IsActive"), "native Destruct did not cancel BP Dash listener")
                self.enter("removed")
            elif self.phase == "removed" and elapsed > 0.25:
                before = self.candidate._uep_dash_messages
                self.broadcast(0.8)
                check(self.candidate._uep_dash_messages == before, "Destruct Dash accepted late delivery")
                self.report["cases"].append({"name": "destruct-no-late-delivery", "messages_before": before,
                                             "messages_after": self.candidate._uep_dash_messages})
                for widget in self.lifecycle_widgets:
                    widget.AddToViewport(450)
                check(self.candidate._uep_dash_scope is not None, "native remount did not rearm Dash")
                check(getattr(self.baseline, dash.PROXY).call_function("IsActive"), "native remount did not rearm original Dash")
                self.report["reconstruct_entry"] = "native same-widget AddToViewport after RemoveFromParent; test-owned remount"
                self.enter("remount")
            elif self.phase == "remount" and elapsed > 0.3:
                # Native Construct resets its displayed arc, but retains model;
                # rebroadcast same owner to establish a shared comparison epoch.
                before = self.candidate._uep_dash_messages
                self.broadcast(1.0)
                check(self.candidate._uep_dash_messages == before + 1, "remounted Dash listener missing")
                self.enter("remount-compare")
            elif self.phase == "remount-compare" and elapsed > 0.3:
                self.compare("same-widget-native-reconstruct", True)
                check([case["name"] for case in self.report["cases"]] == list(CASES), "Dash case inventory differs")
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


result = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("-UEPDashResult=")), None)
if result:
    _validation = DashValidation(result)
    _ticker = ue.add_ticker(_validation.tick, 0.0)
