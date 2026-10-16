"""Real native live-table text across culture changes, no rebroadcast/string seed."""

import atexit
import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.structs import GameplayTag, Vector2D

from . import ability_failure_mixin as failure
from .ability_failure_contract import require, validate_culture_report
from .weapon_observer import valid
from uep_lyra_network_bots import isolate_bots


def visible(widget):
    return {"text": str(widget.FailureReasonTextWidget.call_function("GetText")),
            "visibility": int(widget.call_function("GetVisibility"))}


class CultureValidation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.widgets, self.helper, self.seed, self.culture = [], None, None, None
        self.report = {"schema_version": 1, "status": "running", "error": None, "cases": [],
                       "full_acceptance": False, "network_acceptance": False,
                       "native_ability_producer_tested": False, "native_localized_text_identity_tested": True,
                       "seed": {"namespace": "InputKeys", "key": "LeftMouseButton", "native_live_table": True},
                       "rebroadcast_on_culture_change": False, "test_owned_timer_cancel_to_hold_text": True,
                       "fixture_event_invoked": False, "images": []}
        atexit.register(self.finalize)

    def write(self):
        self.report["last_phase"] = self.phase
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()
        self.write()

    def record(self, culture):
        actual, original = visible(self.candidate), visible(self.baseline)
        require(actual == original and actual["visibility"] == 3, "native localized UI differs or is hidden")
        require(self.culture.call_function("GetCurrentCulture") == culture, "native culture did not change")
        self.report["cases"].append({"culture": culture, "python": actual, "blueprint": original})
        self.write()

    def screenshot(self, suffix):
        image = str(self.path.parent / ("ability-failure-native-" + suffix + ".png"))
        ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
            'Shot SHOWUI -nosuffix filename="' + image + '"', self.controller)
        self.report["images"].append(image)

    def ready(self):
        statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge):
                continue
            isolate_bots(statics, world, ue.find_class("LyraPlayerBotController"))
            model = bridge.call_function("CaptureSnapshot")
            if not (model.bExperienceLoaded and model.bHealthReady and not model.bDamageImmune):
                continue
            controller = statics.call_function("GetPlayerController", world, 0)
            cls = ue.load_class(failure.CLASS)
            found, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("GetAllWidgetsOfClass", world, [], cls, False)
            owned = [widget for widget in found if widget.call_function("GetOwningPlayer") == controller]
            if len(owned) != 1:
                continue
            self.world, self.controller, self.candidate = world, controller, owned[0]
            require(str(ue.get_mixin_profile(self.candidate)) == "Python", "production failure profile differs")
            self.report["production_widget"] = self.candidate.get_path_name()
            self.candidate.add_to_root()
            self.widgets.append(self.candidate)
            self.baseline = controller.create_widget(cls)
            self.baseline.add_to_root()
            self.widgets.append(self.baseline)
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.AddToViewport(400)
            self.baseline.SetPositionInViewport(Vector2D(X=650, Y=460), False)
            self.baseline.call_function(failure.RESUME)
            self.helper = ue.new_object(self.candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.seed = ue.new_object(ue.load_class("/Game/UEPValidation/BP_UEPFailureTextFixture.BP_UEPFailureTextFixture_C"))
            self.seed.add_to_root()
            self.culture = ue.find_class("KismetInternationalizationLibrary").get_cdo()
            require(self.culture.call_function("GetCurrentCulture") == "en", "start with -culture=en")
            payload, found = self.seed.call_function("MakeLiveTextFailure", controller, "InputKeys", "LeftMouseButton")
            require(found is True, "native InputKeys live-table seed was not found")
            router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetGameInstanceSubsystem", world, ue.find_class("GameplayMessageSubsystem"))
            self.helper.call_function("BroadcastFailure", router, GameplayTag(TagName=failure.CHANNEL), payload)
            # Hold the already received native text. This is explicit fixture
            # setup, not a timer equivalence claim or another text assignment.
            for widget in self.widgets:
                widget.call_function("CancelLatentActions")
            self.messages_after_seed = self.candidate._uep_failure_messages
            self.record("en")
            self.enter("english")
            return

    def cleanup(self):
        if self.culture is not None:
            require(self.culture.call_function("SetCurrentCulture", "en", False), "failed to restore process culture")
        for widget in self.widgets:
            if valid(widget):
                widget.RemoveFromParent()
                widget.remove_from_root()
        self.widgets = []
        for obj in (self.helper, self.seed):
            if valid(obj):
                obj.remove_from_root()
        self.helper = self.seed = None

    def finish(self, error=None):
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic() - self.started)
        self.write()
        (ue.log_error if error else ue.log)("UEP_FAILURE_CULTURE_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["shutdown"] = failure.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
            try:
                validate_culture_report(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_FAILURE_CULTURE_SHUTDOWN_" + self.report["status"].upper())

    def tick(self, delta):
        try:
            require(time.monotonic() - self.started < 160, "native culture total timeout")
            if self.phase == "ready":
                self.ready()
                return True
            elapsed = time.monotonic() - self.phase_started
            require(elapsed < 20, "native culture phase timeout")
            require(self.candidate._uep_failure_messages == self.messages_after_seed, "unexpected rebroadcast during culture test")
            if self.phase == "english" and elapsed > 0.4:
                self.screenshot("en")
                self.enter("english-shot")
            elif self.phase == "english-shot" and elapsed > 0.4:
                require(self.culture.call_function("SetCurrentCulture", "zh-Hans", False), "native Chinese culture switch rejected")
                self.enter("chinese")
            elif self.phase == "chinese" and elapsed > 0.5:
                self.record("zh-Hans")
                require(self.report["cases"][-1]["python"]["text"] != self.report["cases"][0]["python"]["text"], "native text did not localize")
                self.screenshot("zh-Hans")
                self.enter("chinese-shot")
            elif self.phase == "chinese-shot" and elapsed > 0.4:
                require(self.culture.call_function("SetCurrentCulture", "en", False), "native English restore rejected")
                self.enter("restored")
            elif self.phase == "restored" and elapsed > 0.5:
                self.record("en")
                require(all(Path(path).is_file() for path in self.report["images"]), "native culture PNG missing")
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPAbilityFailureResult="
validation = CultureValidation(next(value[len(prefix):] for value in sys.argv if value.startswith(prefix)))
ticker = ue.add_ticker(validation.tick)
