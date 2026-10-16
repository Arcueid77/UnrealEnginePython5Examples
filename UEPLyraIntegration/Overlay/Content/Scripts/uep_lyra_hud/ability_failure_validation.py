"""Opt-in production UI/original-BP comparison using real VM and animations.

The producer is synthetic and its FText is culture-invariant display text.
No fixture directly calls Tick, OnAnimationFinished or original outro events.
Native localized identity, dead-health and native GAS production stay separate.
"""

import atexit
import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraAbilitySimpleFailureMessage, Vector2D

from . import ability_failure_mixin as failure
from .ability_failure_contract import CASES, require, validate_report
from .weapon_observer import valid
from uep_lyra_network_bots import isolate_bots


def state(widget):
    return {"text": str(widget.FailureReasonTextWidget.call_function("GetText")),
            "visibility": int(widget.call_function("GetVisibility"))}


def animations(widget):
    return {name.lower(): bool(widget.call_function("IsAnimationPlaying", getattr(widget, name)))
            for name in ("Intro", "Outro")}


class AbilityFailureValidation:
    def __init__(self, result):
        self.path, self.started = Path(result), time.monotonic()
        self.phase, self.widgets, self.helper, self.foreign = "ready", [], None, None
        self.paused, self.finished = False, False
        self.max_frame_step, self.last_animation, self.last_sample_wall = 0.0, None, None
        self.first_outro = {}
        self.report = {"schema_version": 2, "status": "running", "cases": [], "error": None,
                       "timer_clock": "native-retriggerable-delay",
                       "full_acceptance": False, "network_acceptance": False,
                       "production_reachability_tested": True, "compiled_vm_transport": True,
                       "native_ability_producer_tested": False, "native_localized_text_identity_tested": False,
                       "dead_health_branch_tested": False, "widget_event_invoked_by_fixture": False,
                       "original_oninitialized_replayed": False, "profile_resume_explicit": True,
                       "animation_transitions": [], "different_outro_observed": False}
        atexit.register(self.finalize)

    def write(self):
        self.report["last_phase"] = self.phase
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()
        self.write()

    def broadcast(self, reason, owner=None):
        self.helper.call_function("BroadcastFailure", self.router, GameplayTag(TagName=failure.CHANNEL),
                                  LyraAbilitySimpleFailureMessage(PlayerController=owner or self.controller,
                                                                 UserFacingReason=reason))

    def compare(self, name, text=None, visibility=None):
        actual, original = state(self.candidate), state(self.baseline)
        require(actual == original, "failure BP/Python differs at " + name + ": " + repr((original, actual)))
        require(self.candidate.get_class() == self.baseline.get_class(), "failure widget class changed")
        if text is not None:
            require(actual["text"] == text, "unexpected reason at " + name)
        if visibility is not None:
            require(actual["visibility"] == visibility, "unexpected visibility at " + name)
        self.report["cases"].append({"name": name, "same_class": True, "python": actual, "blueprint": original})
        self.write()

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
            cls = ue.load_class(failure.CLASS)
            existing, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function(
                "GetAllWidgetsOfClass", world, [], cls, False)
            candidates = [widget for widget in existing if widget.call_function("GetOwningPlayer") == controller]
            if len(candidates) != 1:
                continue
            self.world, self.statics, self.controller = world, statics, controller
            self.candidate = candidates[0]
            self.report["production_widget"] = self.candidate.get_path_name()
            self.report["production_default_profile"] = str(ue.get_mixin_profile(self.candidate))
            require(self.report["production_default_profile"] == "Python", "failure CDO did not select Python")
            self.widgets.append(self.candidate)
            self.candidate.add_to_root()
            self.baseline = controller.create_widget(cls)
            self.baseline.add_to_root()
            self.widgets.append(self.baseline)
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.AddToViewport(400)
            self.baseline.SetPositionInViewport(Vector2D(X=650.0, Y=460.0), False)
            self.baseline.call_function(failure.RESUME)
            self.helper = ue.new_object(self.candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetGameInstanceSubsystem", world, ue.find_class("GameplayMessageSubsystem"))
            require(valid(self.router), "native message subsystem missing")
            # The field is PlayerController*, so an arbitrary Actor is not a valid foreign payload.
            self.foreign = world.actor_spawn(ue.find_class("PlayerController"))
            require(valid(self.foreign), "test-owned foreign controller missing")
            self.enter("initial")
            return

    def sample(self):
        clock = failure.game_time(self.candidate)
        now = time.monotonic()
        if self.last_sample_wall is not None and self.phase != "initial":
            self.max_frame_step = max(self.max_frame_step, now - self.last_sample_wall)
        self.last_sample_wall = now
        animation = {"python": animations(self.candidate), "blueprint": animations(self.baseline)}
        if animation != self.last_animation:
            self.report["animation_transitions"].append({"phase": self.phase, "clock": clock,
                "elapsed_since_first_message": now - self.first_message_wall if hasattr(self, "first_message_wall") else None,
                **animation})
            require(len(self.report["animation_transitions"]) <= 200, "unexpected animation loop")
            self.last_animation = animation
        if self.phase in ("owner", "pause-settle", "paused", "expiry"):
            for name in ("python", "blueprint"):
                if animation[name]["outro"] and name not in self.first_outro:
                    self.first_outro[name] = time.monotonic() - self.first_message_wall
                    self.report["first_outro_observations"] = dict(self.first_outro)
        if self.phase == "different" and all(value["outro"] for value in animation.values()):
            self.report["different_outro_observed"] = True
        return animation

    def cleanup(self):
        errors = []
        if self.paused:
            try:
                self.statics.call_function("SetGamePaused", self.world, False)
                self.paused = False
            except Exception:
                errors.append(traceback.format_exc())
        for widget in self.widgets:
            if valid(widget):
                for action in (widget.RemoveFromParent, widget.remove_from_root):
                    try:
                        action()
                    except Exception:
                        errors.append(traceback.format_exc())
        self.widgets = []
        for obj, action in ((self.foreign, "actor_destroy"), (self.helper, "remove_from_root")):
            if valid(obj):
                try:
                    getattr(obj, action)()
                except Exception:
                    errors.append(traceback.format_exc())
        self.foreign = self.helper = None
        if errors:
            raise RuntimeError("\n".join(errors))

    def finish(self, error=None):
        self.finished = True
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic() - self.started, before_exit=failure.snapshot())
        self.write()
        (ue.log_error if error else ue.log)("UEP_ABILITY_FAILURE_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        # The native world has already torn down. Never touch its UObject wrappers here.
        self.report["shutdown"] = failure.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
            try:
                validate_report(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)(
            "UEP_ABILITY_FAILURE_SHUTDOWN_" + self.report["status"].upper())

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic() - self.started < 220, "failure total timeout")
            if self.phase == "ready":
                self.ready()
                return True
            elapsed = time.monotonic() - self.phase_started
            require(elapsed < 20, "failure phase timeout: " + self.phase)
            animation = self.sample()
            if self.phase == "initial" and elapsed > 0.25:
                self.compare("initial-collapsed", visibility=1)
                self.first_message_time = failure.game_time(self.candidate)
                self.first_message_wall = time.monotonic()
                self.owner_before = self.candidate._uep_failure_messages
                self.broadcast("UEP failure A")
                require(self.candidate._uep_failure_messages == self.owner_before + 1, "owner delivery missing or duplicated")
                self.compare("typed-owner-reason", "UEP failure A", 3)
                self.enter("owner")
            elif self.phase == "owner" and elapsed > 0.3:
                before, foreign_before = state(self.candidate), self.candidate._uep_failure_foreign
                self.broadcast("ignored owner", self.foreign)
                require(state(self.candidate) == before and self.candidate._uep_failure_foreign == foreign_before + 1,
                        "foreign controller changed presentation or was not filtered")
                self.compare("foreign-owner-ignored", "UEP failure A", 3)
                pending, intros = self.candidate._uep_failure_delay_pending, failure.snapshot()["intros"]
                self.broadcast("UEP failure A")
                require(self.candidate._uep_failure_delay_pending == pending and failure.snapshot()["intros"] == intros,
                        "same reason restarted Python presentation")
                self.compare("same-reason-no-retrigger", "UEP failure A", 3)
                require(self.statics.call_function("SetGamePaused", self.world, True), "native pause rejected")
                self.paused = True
                self.enter("pause-settle")
            elif self.phase == "pause-settle" and elapsed > 0.2:
                self.frozen_clock = failure.game_time(self.candidate)
                self.frozen = [state(widget) for widget in self.widgets]
                self.outros_before_pause = failure.snapshot()["outros"]
                self.enter("paused")
            elif self.phase == "paused" and elapsed > 1.1 and all(state(widget)["visibility"] == 1 for widget in self.widgets):
                self.report["pause_observed"] = {"frozen_world_clock": self.frozen_clock,
                    "current_world_clock": failure.game_time(self.candidate), "before": self.frozen,
                    "after": [state(widget) for widget in self.widgets], "stats": failure.snapshot()}
                self.report["paused_world_clock_frozen"] = failure.game_time(self.candidate) == self.frozen_clock
                self.report["paused_ui_expired"] = all(state(widget)["visibility"] == 1 for widget in self.widgets)
                require(self.report["paused_world_clock_frozen"] and self.report["paused_ui_expired"] and
                        failure.snapshot()["outros"] == self.outros_before_pause + 1,
                        "UMG delay did not continue naturally while world clock was paused")
                self.compare("paused-world-ui-delay-continues", "UEP failure A", 1)
                self.report["paused_wall_seconds"] = elapsed
                self.statics.call_function("SetGamePaused", self.world, False)
                self.paused = False
                self.enter("expiry")
            elif self.phase == "expiry" and len(self.first_outro) == 2:
                self.report["first_outro_timing"] = {"python_seconds": self.first_outro["python"],
                    "blueprint_seconds": self.first_outro["blueprint"], "max_observed_ui_frame": self.max_frame_step,
                    "tolerance_seconds": max(0.025, 2 * self.max_frame_step)}
                self.compare("one-second-native-outro-boundary", "UEP failure A", 1)
                self.enter("collapsed")
            elif self.phase == "collapsed" and all(state(widget)["visibility"] == 1 for widget in self.widgets):
                self.compare("native-outro-completion-collapses", "UEP failure A", 1)
                retained = state(self.candidate)
                ue.set_mixin_profile(self.candidate, "BlueprintFallback")
                self.candidate.call_function(failure.RESUME)
                require(state(self.candidate) == retained and self.candidate.UEPOriginalFailureProxy.call_function("IsActive"),
                        "hidden original resume reset the display or failed to listen")
                self.compare("hidden-blueprint-resume", "UEP failure A", 1)
                proxy = self.candidate.UEPOriginalFailureProxy
                ue.set_mixin_profile(self.candidate, "Python")
                self.candidate.call_function(failure.RESUME)
                require(state(self.candidate) == retained and not proxy.call_function("IsActive"), "old original proxy survived")
                self.compare("hidden-python-resume", "UEP failure A", 1)
                # Explicitly close the baseline's first animation bindings too;
                # subsequent group compares a clean observation lifetime on both sides.
                ue.set_mixin_profile(self.baseline, "Python")
                ue.set_mixin_profile(self.baseline, "BlueprintFallback")
                self.baseline.call_function(failure.RESUME)
                before = self.candidate._uep_failure_messages
                self.broadcast("UEP resumed")
                require(self.candidate._uep_failure_messages == before + 1, "resumed delivery duplicated")
                self.compare("resumed-message-exact-once", "UEP resumed", 3)
                self.enter("resumed-expiry")
            elif self.phase == "resumed-expiry" and elapsed > 0.35 and "image" not in self.report:
                self.report["image"] = str(self.path.parent / "ability-failure.png")
                self.report["screenshot_state"] = [{"state": state(widget),
                    "opacity": float(widget.call_function("GetRenderOpacity")), "animations": animations(widget)}
                    for widget in self.widgets]
                require(all(value["state"] == {"text": "UEP resumed", "visibility": 3}
                            for value in self.report["screenshot_state"]), "failure screenshot lost visible reason")
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="' + self.report["image"] + '"', self.controller)
            elif self.phase == "resumed-expiry" and elapsed > 0.3 and all(state(widget)["visibility"] == 1 for widget in self.widgets):
                proxy = self.baseline.UEPOriginalFailureProxy
                for widget in self.widgets:
                    widget.RemoveFromParent()
                require(self.candidate._uep_failure_scope is None and not proxy.call_function("IsActive"),
                        "native Destruct left a listener active")
                self.detached, self.detached_messages = [state(widget) for widget in self.widgets], self.candidate._uep_failure_messages
                self.broadcast("must not deliver")
                self.enter("detached")
            elif self.phase == "detached" and elapsed > 0.3:
                require([state(widget) for widget in self.widgets] == self.detached and
                        self.candidate._uep_failure_messages == self.detached_messages, "late delivery after native Destruct")
                self.compare("destruct-no-late-delivery", "UEP resumed", 1)
                for widget in self.widgets:
                    widget.AddToViewport(400)
                require(self.candidate._uep_failure_scope is not None and
                        self.baseline.UEPOriginalFailureProxy.call_function("IsActive"), "native Construct did not rearm")
                before = self.candidate._uep_failure_messages
                self.broadcast("UEP remount")
                require(self.candidate._uep_failure_messages == before + 1, "remount delivery duplicated")
                self.compare("same-widget-native-reconstruct", "UEP remount", 3)
                self.report["reconstruct_entry"] = "test-owned same-widget RemoveFromParent/AddToViewport"
                self.broadcast("UEP replacement")
                self.compare("different-reason-waits-for-outro", "UEP remount", 3)
                self.enter("different")
            elif self.phase == "different" and all(state(widget)["text"] == "UEP replacement" for widget in self.widgets):
                require(self.report["different_outro_observed"], "replacement did not use observed native Outro")
                self.compare("different-reason-after-native-outro", "UEP replacement", 3)
                self.broadcast("pending owner")
                self.broadcast("UEP foreign deferred", self.foreign)
                self.enter("deferred")
            elif self.phase == "deferred" and all(state(widget)["text"] == "UEP foreign deferred" for widget in self.widgets):
                self.compare("deferred-latest-foreign-payload", "UEP foreign deferred", 3)
                self.completions_before = failure.snapshot()["completions"]
                self.enter("persistent")
            elif self.phase == "persistent" and all(state(widget)["visibility"] == 1 for widget in self.widgets):
                require(failure.snapshot()["completions"] >= self.completions_before + 3, "persistent callback model not exercised")
                self.compare("persistent-outro-callback-order", "UEP foreign deferred", 1)
                self.broadcast("pending first")
                self.broadcast("pending second")
                ue.set_mixin_profile(self.candidate, "BlueprintFallback")
                ue.set_mixin_profile(self.baseline, "Python")
                # Do not resume: this case proves teardown cancels pending work.
                self.cancelled = [state(widget) for widget in self.widgets]
                self.cancelled_outros = failure.snapshot()["outros"]
                self.enter("cancelled")
            elif self.phase == "cancelled" and elapsed > 1.25:
                require([state(widget) for widget in self.widgets] == self.cancelled and
                        failure.snapshot()["outros"] == self.cancelled_outros and
                        not any(value["outro"] or value["intro"] for value in animation.values()),
                        "pending animation/delay survived profile teardown")
                self.compare("profile-teardown-cancels-pending-work")
                require([case["name"] for case in self.report["cases"]] == list(CASES), "failure cases incomplete")
                require(Path(self.report["image"]).is_file(), "failure PNG missing")
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPAbilityFailureResult="
result = next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)
if result and "-UEPAbilityFailureNativeProducer" not in sys.argv:
    validation = AbilityFailureValidation(result)
    ticker = ue.add_ticker(validation.tick)
