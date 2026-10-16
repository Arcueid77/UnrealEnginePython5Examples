"""Opt-in paired UI test: real VM messages/game time, never synthetic widget Tick.

The candidate is the existing production HUD widget; the original-BP baseline
is test-owned. The duration producer is synthetic, not a native ability.
"""

import atexit
import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage, Vector2D

from . import ability_progress_mixin as progress
from .weapon_observer import valid
from uep_lyra_network_bots import isolate_bots


CASES = ("initial-collapsed", "typed-owner-duration", "foreign-owner-ignored",
         "repeated-duration-restarts", "paused-game-time-frozen", "last-second-precision",
         "countdown-completed", "hidden-blueprint-resume", "hidden-python-resume",
         "resumed-message-exact-once", "destruct-no-late-delivery", "same-widget-native-reconstruct")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def model(widget):
    return [float(widget.Duration), float(widget.StartTime), int(widget.call_function("GetVisibility"))]


def state(widget):
    material = widget.ProgressBorder.call_function("GetDynamicMaterial")
    color = material.call_function("K2_GetVectorParameterValue", "ActiveRange")
    return {"duration": float(widget.Duration), "start": float(widget.StartTime),
            "visibility": int(widget.call_function("GetVisibility")),
            "text": str(widget.ProgressText.call_function("GetText")),
            "percent": float(material.call_function("K2_GetScalarParameterValue", "Percent")),
            "active_range": [float(getattr(color, name)) for name in ("r", "g", "b", "a")]}


class AbilityProgressValidation:
    def __init__(self, result):
        self.path, self.started = Path(result), time.monotonic()
        self.phase = "ready"
        self.widgets, self.helper, self.foreign = [], None, None
        self.paused = False
        self.report = {"schema_version": 1, "status": "running", "cases": [],
                       "full_acceptance": False, "network_acceptance": False,
                       "test_owned_pair": False, "production_reachability_tested": True,
                       "native_interaction_producer_tested": False, "widget_tick_invoked_by_fixture": False,
                       "compiled_vm_transport": True, "profile_resume_explicit": True}
        atexit.register(self.finalize)

    def write(self):
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()
        self.ticks_at_entry = self.candidate._uep_progress_ticks

    def broadcast(self, duration, instigator=None):
        self.helper.call_function("BroadcastDuration", self.router, GameplayTag(TagName=progress.CHANNEL),
                                  LyraInteractionDurationMessage(Instigator=instigator or self.pawn, Duration=duration))

    def compare(self, name, require_ticks=False):
        actual, original = state(self.candidate), state(self.baseline)
        check(actual.keys() == original.keys(), "progress state shape differs")
        for key in actual:
            if key == "percent":
                check(abs(actual[key] - original[key]) < 0.00001, "material percent differs: " + repr((original, actual)))
            elif key != "start" or name != "initial-collapsed":
                check(actual[key] == original[key], "progress BP/Python differs for " + key + ": " + repr((original, actual)))
        if require_ticks:
            check(self.candidate._uep_progress_ticks > self.ticks_at_entry + 1, "native UMG Tick did not reach Python")
        check(self.candidate.get_class() == self.baseline.get_class(), "progress class changed")
        self.report["cases"].append({"name": name, "python": actual, "blueprint": original,
                                     "automatic_ticks": self.candidate._uep_progress_ticks,
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
            self.world, self.statics = world, statics
            self.controller = statics.call_function("GetPlayerController", world, 0)
            self.pawn = self.controller.get_controlled_pawn()
            cls = ue.load_class(progress.CLASS)
            existing, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function(
                "GetAllWidgetsOfClass", world, [], cls, False)
            candidates = [widget for widget in existing if widget.call_function("GetOwningPlayer") == self.controller]
            if len(candidates) != 1:
                continue
            self.candidate = candidates[0]
            self.report["production_widget"] = self.candidate.get_path_name()
            self.report["production_default_profile"] = str(ue.get_mixin_profile(self.candidate))
            self.baseline = self.controller.create_widget(cls)
            self.widgets = [self.candidate, self.baseline]
            for index, widget in enumerate(self.widgets):
                widget.add_to_root()
                if index == 1:
                    widget.AddToViewport(400)
                    widget.SetPositionInViewport(Vector2D(X=850.0, Y=350.0), False)
                    widget.SetDesiredSizeInViewport(Vector2D(X=160.0, Y=160.0))
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.call_function(progress.RESUME_EVENT)
            check(str(ue.get_mixin_profile(self.candidate)) == "Python", "default progress profile is not Python")
            self.helper = ue.new_object(self.candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetGameInstanceSubsystem", world, ue.find_class("GameplayMessageSubsystem"))
            check(valid(self.router), "native message subsystem missing")
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
        if valid(self.foreign):
            self.foreign.actor_destroy()
            self.foreign = None
        if valid(self.helper):
            self.helper.remove_from_root()
            self.helper = None

    def finish(self, error=None):
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic() - self.started, before_exit=progress.snapshot())
        self.write()
        (ue.log_error if error else ue.log)("UEP_ABILITY_PROGRESS_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        # UObject destruction already happened; inspect copied metadata only.
        final = progress.snapshot()
        self.report["shutdown"] = final
        if final["active_count"] or final["scopes_created"] != final["scopes_closed"] or final["errors"]:
            self.report.update(status="failed", error="progress scopes remained after shutdown")
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_ABILITY_PROGRESS_SHUTDOWN_" + self.report["status"].upper())

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 220, "progress total timeout")
            if self.phase == "ready":
                self.ready()
                return True
            check(time.monotonic() - self.phase_started < 20, "progress phase timeout: " + self.phase)
            elapsed_wall = time.monotonic() - self.phase_started
            if self.phase == "initial" and elapsed_wall > 0.25:
                self.compare("initial-collapsed")
                check(model(self.candidate)[2] == 1, "Construct did not collapse progress")
                self.owner_before = self.candidate._uep_progress_messages
                self.broadcast(5.0)
                check(self.candidate._uep_progress_messages == self.owner_before + 1, "owner message duplicated or missing")
                self.enter("owner")
            elif self.phase == "owner" and elapsed_wall > 0.3:
                self.compare("typed-owner-duration", True)
                check(self.candidate.Duration == 5.0 and model(self.candidate)[2] == 0, "owner duration not visible")
                before = [model(widget) for widget in self.widgets]
                foreign_before = self.candidate._uep_progress_foreign_messages
                self.broadcast(77.0, self.foreign)
                check([model(widget) for widget in self.widgets] == before, "foreign message changed duration")
                check(self.candidate._uep_progress_foreign_messages == foreign_before + 1, "foreign filtering did not run exactly once")
                self.compare("foreign-owner-ignored")
                self.broadcast(3.5)
                self.enter("repeated")
            elif self.phase == "repeated" and elapsed_wall > 0.3:
                self.compare("repeated-duration-restarts", True)
                check(self.candidate.Duration == 3.5, "repeat did not replace native duration")
                check(self.statics.call_function("SetGamePaused", self.world, True), "native game pause rejected")
                self.paused = True
                self.enter("pause-settle")
            elif self.phase == "pause-settle" and elapsed_wall > 0.2:
                self.frozen_clock = progress.game_time(self.candidate)
                self.frozen = [state(widget) for widget in self.widgets]
                self.enter("paused")
            elif self.phase == "paused" and elapsed_wall > 1.1:
                check(progress.game_time(self.candidate) == self.frozen_clock, "native game clock advanced while paused")
                check([state(widget) for widget in self.widgets] == self.frozen, "countdown advanced while paused")
                self.compare("paused-game-time-frozen")
                self.report["paused_wall_seconds"] = elapsed_wall
                self.report["image"] = str(self.path.parent / "ability-progress.png")
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="' + self.report["image"] + '"', self.controller)
                self.statics.call_function("SetGamePaused", self.world, False)
                self.paused = False
                self.enter("last-second")
            elif self.phase == "last-second":
                remaining = float(self.candidate.Duration) - (progress.game_time(self.candidate) - float(self.candidate.StartTime))
                if 0.2 < remaining < 0.8:
                    self.compare("last-second-precision", True)
                    check("." in str(self.candidate.ProgressText.call_function("GetText")), "last second did not use decimal precision")
                    self.enter("expiry")
            elif self.phase == "expiry" and model(self.candidate)[2] == model(self.baseline)[2] == 1:
                self.compare("countdown-completed")
                check(Path(self.report["image"]).is_file(), "progress screenshot missing")
                retained = model(self.candidate)
                ue.set_mixin_profile(self.candidate, "BlueprintFallback")
                self.candidate.call_function(progress.RESUME_EVENT)
                check(model(self.candidate) == retained, "hidden BP resume reset model")
                check(self.candidate.UEPOriginalDurationProxy.call_function("IsActive"), "hidden BP listener not active")
                self.compare("hidden-blueprint-resume")
                original_proxy = self.candidate.UEPOriginalDurationProxy
                ue.set_mixin_profile(self.candidate, "Python")
                self.candidate.call_function(progress.RESUME_EVENT)
                check(model(self.candidate) == retained, "hidden Python resume reset model")
                check(not original_proxy.call_function("IsActive"), "old BP proxy survived Profile teardown")
                check(self.candidate._uep_progress_scope is not None, "hidden Python listener not active")
                self.compare("hidden-python-resume")
                self.owner_before = self.candidate._uep_progress_messages
                self.broadcast(2.0)
                check(self.candidate._uep_progress_messages == self.owner_before + 1, "resumed owner delivery duplicated")
                self.enter("resumed")
            elif self.phase == "resumed" and elapsed_wall > 0.3:
                self.compare("resumed-message-exact-once", True)
                original_proxy = self.baseline.UEPOriginalDurationProxy
                for widget in self.widgets:
                    widget.RemoveFromParent()
                check(self.candidate._uep_progress_scope is None, "native Destruct left Python listener active")
                check(not original_proxy.call_function("IsActive"), "native Destruct left BP proxy active")
                self.detached_models = [model(widget) for widget in self.widgets]
                self.owner_before = self.candidate._uep_progress_messages
                self.broadcast(99.0)
                self.enter("detached")
            elif self.phase == "detached" and elapsed_wall > 0.3:
                check([model(widget) for widget in self.widgets] == self.detached_models, "detached widget received later duration")
                check(self.candidate._uep_progress_messages == self.owner_before, "closed Python listener received delivery")
                self.compare("destruct-no-late-delivery")
                for widget in self.widgets:
                    widget.AddToViewport(400)
                check(self.candidate._uep_progress_scope is not None, "native Construct did not rearm hidden Python widget")
                check(self.baseline.UEPOriginalDurationProxy.call_function("IsActive"), "native Construct did not rearm hidden BP widget")
                self.owner_before = self.candidate._uep_progress_messages
                self.broadcast(2.0)
                check(self.candidate._uep_progress_messages == self.owner_before + 1, "reconstructed owner delivery duplicated")
                self.enter("reconstructed")
            elif self.phase == "reconstructed" and elapsed_wall > 0.3:
                self.compare("same-widget-native-reconstruct", True)
                self.report["reconstruct_entry"] = "native same-widget AddToViewport after RemoveFromParent; test-owned remount"
                check([case["name"] for case in self.report["cases"]] == list(CASES), "progress cases incomplete")
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPAbilityProgressResult="
result = next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))
validation = AbilityProgressValidation(result)
ticker = ue.add_ticker(validation.tick)
