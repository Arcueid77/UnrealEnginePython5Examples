"""Production respawn UI vs original BP using native timer/UMG/audio callbacks."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage, LyraVerbMessage, Vector2D
from . import respawn_timer_mixin as respawn
from .weapon_observer import valid
from uep_lyra_network_bots import isolate_bots

CASES = ("initial-collapsed", "typed-playerstate-duration", "foreign-pawn-ignored", "repeated-duration-restarts",
         "paused-game-time-frozen", "native-timer-completed", "completion-message-preserves-flag",
         "blueprint-profile-resume", "python-profile-resume", "resumed-message-exact-once",
         "destruct-no-late-delivery", "same-widget-native-reconstruct")


def check(value, reason):
    if not value:
        raise AssertionError(reason)


def state(widget):
    audio = respawn.countdown_audio(widget)
    return {"duration": float(widget.Duration), "start": float(widget.StartTime),
            "remaining": float(widget.StartTime)+float(widget.Duration)-respawn.game_time(widget),
            "respawning": bool(widget.Respawning), "visibility": int(widget.call_function("GetVisibility")),
            "numeric": float(widget.Time.call_function("GetTargetValue")), "text": str(widget.Time.call_function("GetText")),
            "glow": float(widget.FillGlow.call_function("GetDynamicMaterial").call_function("K2_GetScalarParameterValue", "AnimateArcFill")),
            "fill": float(widget.Fill.call_function("GetDynamicMaterial").call_function("K2_GetScalarParameterValue", "AnimateArcFill")),
            "audio_valid": valid(audio), "audio_playing": bool(audio.call_function("IsPlaying")) if valid(audio) else False,
            "timer_active": bool(respawn.systems().call_function("K2_IsTimerActive", widget, "UpdateRespawnText"))}


class RespawnValidation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.widgets, self.helper, self.paused = [], None, False
        self.lifecycle_pair = False
        self.report = {"schema_version": 1, "status": "running", "cases": [], "full_acceptance": False, "network_acceptance": False,
                       "native_respawn_producer_tested": False, "synthetic_local_messages": True,
                       "fixture_widget_event_invoked": False, "audio_component_tested": True, "acoustic_parity_tested": False,
                       "material_absolute_tolerance": 0.00001, "production_widget": None,
                       "remaining_observation": "derived native deadline, not BP function-local storage"}
        atexit.register(self.finalize)

    def write(self):
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def broadcast(self, duration, instigator=None):
        self.helper.call_function("BroadcastDuration", self.router, GameplayTag(TagName=respawn.DURATION_CHANNEL),
                                  LyraInteractionDurationMessage(Instigator=instigator or self.player_state, Duration=duration))

    def compare(self, name):
        actual, original = state(self.candidate), state(self.baseline)
        for key in actual:
            if key in ("glow", "fill", "remaining"):
                check(abs(actual[key]-original[key]) <= 0.00001, "respawn material/time differs " + key + ": " + repr((actual, original)))
            else:
                check(actual[key] == original[key], "respawn BP/Python differs " + key + ": " + repr((actual, original)))
        check(self.candidate.get_class() == self.baseline.get_class(), "respawn class changed")
        self.report["cases"].append({"name": name, "python": actual, "blueprint": original,
                                     "profile": str(ue.get_mixin_profile(self.candidate)),
                                     "test_owned_lifecycle_widget": self.lifecycle_pair})

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
            cls = ue.load_class(respawn.CLASS)
            widgets, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("GetAllWidgetsOfClass", world, [], cls, False)
            candidates = [widget for widget in widgets if widget.call_function("GetOwningPlayer") == controller]
            if len(candidates) != 1:
                self.report["readiness"] = {"candidate_count": len(candidates)}
                continue
            self.world, self.statics, self.controller = world, statics, controller
            self.player_state, self.pawn = controller.PlayerState, controller.get_controlled_pawn()
            self.candidate = candidates[0]
            check(str(ue.get_mixin_profile(self.candidate)) == "Python", "production respawn not Python")
            self.report["production_widget"] = self.candidate.get_path_name()
            self.baseline = controller.create_widget(cls)
            self.widgets = [self.candidate, self.baseline]
            for widget in self.widgets:
                widget.add_to_root()
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.AddToViewport(450)
            self.baseline.SetPositionInViewport(Vector2D(X=850.0, Y=400.0), False)
            self.baseline.SetDesiredSizeInViewport(Vector2D(X=180.0, Y=180.0))
            self.baseline.call_function(respawn.RESUME)
            self.helper = ue.new_object(self.candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetGameInstanceSubsystem", world, ue.find_class("GameplayMessageSubsystem"))
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

    def finish(self, error=None):
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error, elapsed_seconds=time.monotonic()-self.started)
        self.write()
        (ue.log_error if error else ue.log)("UEP_RESPAWN_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        final = respawn.snapshot()
        self.report["shutdown"] = final
        if final["active_count"] or final["scopes_created"] != final["scopes_closed"] or final["errors"]:
            self.report.update(status="failed", error="respawn scope survived exit")
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_RESPAWN_SHUTDOWN_"+self.report["status"].upper())

    def tick(self, delta):
        try:
            check(time.monotonic()-self.started < 200, "respawn total timeout")
            if self.phase == "ready":
                self.ready()
                return True
            elapsed = time.monotonic()-self.phase_started
            check(elapsed < 25, "respawn phase timeout: " + self.phase)
            if self.phase == "initial" and elapsed > 0.5:
                self.compare("initial-collapsed")
                check(state(self.candidate)["visibility"] == 1, "Construct did not collapse respawn")
                before = self.candidate._uep_respawn_duration_messages
                self.broadcast(4.0)
                check(self.candidate._uep_respawn_duration_messages == before+1, "owner duration not exact-once")
                self.enter("owner")
            elif self.phase == "owner" and elapsed > 0.4:
                self.compare("typed-playerstate-duration")
                check(state(self.candidate)["timer_active"] and state(self.candidate)["audio_valid"], "native timer/audio did not start")
                before = [state(widget) for widget in self.widgets]
                self.broadcast(77.0, self.pawn)
                check([state(widget) for widget in self.widgets] == before, "foreign Pawn duration changed UI")
                self.compare("foreign-pawn-ignored")
                self.broadcast(2.5)
                self.enter("repeat")
            elif self.phase == "repeat" and elapsed > 0.35:
                self.compare("repeated-duration-restarts")
                check(self.statics.call_function("SetGamePaused", self.world, True), "respawn pause rejected")
                self.paused = True
                self.enter("pause-settle")
            elif self.phase == "pause-settle" and elapsed > 0.2:
                self.frozen = [state(widget) for widget in self.widgets]
                self.frozen_time = respawn.game_time(self.candidate)
                self.enter("paused")
            elif self.phase == "paused" and elapsed > 1.1:
                check(respawn.game_time(self.candidate) == self.frozen_time, "paused respawn game time advanced")
                check([state(widget) for widget in self.widgets] == self.frozen, "paused native timer/audio UI changed")
                self.compare("paused-game-time-frozen")
                self.report["paused_wall_seconds"] = elapsed
                self.report["image"] = str(self.path.parent / "respawn-timer.png")
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="'+self.report["image"]+'"', self.controller)
                self.enter("shot-wait")
            elif self.phase == "shot-wait" and elapsed > 0.4:
                self.statics.call_function("SetGamePaused", self.world, False)
                self.paused = False
                self.enter("expiry")
            elif self.phase == "expiry" and all(state(widget)["visibility"] == 1 for widget in self.widgets) and elapsed > 0.5:
                self.compare("native-timer-completed")
                check(not self.candidate.Respawning and not state(self.candidate)["timer_active"], "respawn timer not closed by native Outro")
                self.broadcast(3.0)
                self.enter("completed")
            elif self.phase == "completed" and elapsed > 0.3:
                self.helper.call_function("BroadcastVerb", self.router, GameplayTag(TagName=respawn.COMPLETED_CHANNEL),
                                          LyraVerbMessage(Instigator=self.player_state))
                self.compare("completion-message-preserves-flag")
                check(self.candidate.Respawning and state(self.candidate)["visibility"] == 1, "completion altered authored flag")
                self.enter("completion-audio-settle")
            elif self.phase == "completion-audio-settle" and elapsed > 0.65:
                ue.set_mixin_profile(self.candidate, "BlueprintFallback")
                self.candidate.call_function(respawn.RESUME)
                self.enter("fallback")
            elif self.phase == "fallback" and elapsed > 0.3:
                self.compare("blueprint-profile-resume")
                ue.set_mixin_profile(self.candidate, "Python")
                self.candidate.call_function(respawn.RESUME)
                self.enter("python")
            elif self.phase == "python" and elapsed > 0.3:
                self.compare("python-profile-resume")
                before = self.candidate._uep_respawn_duration_messages
                self.broadcast(1.0)
                check(self.candidate._uep_respawn_duration_messages == before+1, "resumed duration not exact-once")
                self.enter("resumed")
            elif self.phase == "resumed" and elapsed > 0.3:
                self.compare("resumed-message-exact-once")
                # Production UIExtension entries retain Slate on native pool
                # release, so RemoveFromParent is not their Destruct. Test the
                # real native lifecycle on explicitly viewport-owned widgets.
                cls = self.candidate.get_class()
                self.candidate = self.controller.create_widget(cls)
                self.baseline = self.controller.create_widget(cls)
                self.lifecycle_widgets = [self.candidate, self.baseline]
                for widget in self.lifecycle_widgets:
                    widget.add_to_root()
                ue.set_mixin_profile(self.baseline, "BlueprintFallback")
                for widget in self.lifecycle_widgets:
                    widget.AddToViewport(450)
                self.widgets.extend(self.lifecycle_widgets)
                self.lifecycle_pair = True
                self.report["lifecycle_entry"] = "test-owned same-class viewport pair; production mount uses UIExtension pool"
                self.broadcast(2.5)
                self.enter("lifecycle-ready")
            elif self.phase == "lifecycle-ready" and elapsed > 0.3:
                self.held_original_proxies = [getattr(self.baseline, name) for name in
                                             ("RespawnDurationAsyncAction", "RespawnCompletedAsyncAction")]
                check(all(valid(proxy) and proxy.call_function("IsActive") for proxy in self.held_original_proxies),
                      "original respawn proxies missing before native Destruct")
                self.before_removed = self.candidate._uep_respawn_duration_messages
                for widget in self.lifecycle_widgets:
                    widget.RemoveFromParent()
                check(self.candidate._uep_respawn_scope is None and
                      not any(state(widget)["timer_active"] for widget in self.lifecycle_widgets),
                      "native Destruct did not close respawn scope/timers")
                check(not any(proxy.call_function("IsActive") for proxy in self.held_original_proxies) and
                      self.baseline.RespawnDurationAsyncAction is None and self.baseline.RespawnCompletedAsyncAction is None,
                      "native Destruct did not cancel original respawn proxies")
                self.enter("removed")
            elif self.phase == "removed" and elapsed > 0.25:
                before = [state(widget) for widget in self.lifecycle_widgets]
                self.broadcast(77.0)
                check([state(widget) for widget in self.lifecycle_widgets] == before and
                      self.candidate._uep_respawn_duration_messages == self.before_removed, "Destruct respawn accepted late delivery")
                self.compare("destruct-no-late-delivery")
                for widget in self.lifecycle_widgets:
                    widget.AddToViewport(450)
                check(self.candidate._uep_respawn_scope is not None and
                      self.baseline.RespawnDurationAsyncAction.call_function("IsActive") and
                      self.baseline.RespawnCompletedAsyncAction.call_function("IsActive"), "native remount didn't rearm respawn")
                self.report["reconstruct_entry"] = "native same-widget AddToViewport after RemoveFromParent; test-owned remount"
                before = self.candidate._uep_respawn_duration_messages
                self.broadcast(1.0)
                check(self.candidate._uep_respawn_duration_messages == before+1, "remounted respawn duration not exact-once")
                self.enter("remount")
            elif self.phase == "remount" and elapsed > 0.3:
                self.compare("same-widget-native-reconstruct")
                check([case["name"] for case in self.report["cases"]] == list(CASES), "respawn case inventory incomplete")
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


result = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("-UEPRespawnResult=")), None)
if result:
    _validation = RespawnValidation(result)
    _ticker = ue.add_ticker(_validation.tick, 0.0)
