"""Native CommonUI async push/pop from retained BP/Python click profiles."""

import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue

from .weapon_observer import valid
from .open_menu_mixin import CLICK_EVENT, MENU_CLASS
from uep_lyra_network_bots import isolate_bots


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def find_menu_class():
    try:
        return ue.find_object(MENU_CLASS)
    except Exception as error:
        check("unable to find object" in str(error), "unexpected class lookup failure")
        return None


class OpenMenuValidation:
    def __init__(self, result):
        self.path = Path(result)
        self.started = time.monotonic()
        self.state = "ready"
        self.index = 0
        self.widgets = []
        self.active_menu = None
        self.report = {"schema_version": 1, "status": "running", "cases": [], "full_acceptance": False,
                       "physical_touch_tested": False, "class_preloaded_by_probe": False}

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
            self.world, self.controller = world, statics.call_function("GetPlayerController", world, 0)
            cls = ue.load_class("/Game/UI/Hud/W_OpenMenuTouchButton.W_OpenMenuTouchButton_C")
            ue.register_declared_mixin(cls)
            self.button = self.controller.create_widget(cls)
            self.button.add_to_root()
            self.widgets.append(self.button)
            self.report["menu_class_loaded_before"] = find_menu_class() is not None
            self.click()
            return

    def click(self):
        profile = ("Python", "BlueprintFallback", "Python")[self.index]
        ue.set_mixin_profile(self.button, profile)
        self.button.call_function(CLICK_EVENT, self.button.OpenButton)
        self.profile = profile
        self.phase_started = time.monotonic()
        self.state = "opening"

    def active_menus(self):
        cls = find_menu_class()
        if cls is None:
            return []
        # FoundWidgets is an out-array in the second reflected position. UEP's
        # generic call preserves parameter positions rather than skipping it.
        widgets, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("GetAllWidgetsOfClass", self.world, [], cls, False)
        return [widget for widget in widgets if widget.call_function("IsActivated")
                and widget.call_function("GetOwningPlayer") == self.controller]

    def finish(self, error=None):
        try:
            if valid(self.active_menu):
                self.active_menu.call_function("DeactivateWidget")
            for widget in self.widgets:
                if valid(widget):
                    widget.RemoveFromParent()
                    widget.remove_from_root()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "passed", error=error,
                           elapsed_seconds=time.monotonic() - self.started)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_OPEN_MENU_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 180, "menu fixture total timeout")
            if self.state == "ready":
                self.ready()
                return True
            check(time.monotonic() - self.phase_started < 20, "native menu async push/pop timed out: " + self.state)
            active = self.active_menus()
            if self.state == "opening":
                check(len(active) <= 1, "menu click opened duplicate active widgets")
                if not active:
                    return True
                self.active_menu = active[0]
                self.report["cases"].append({"profile": self.profile, "menu_class": self.active_menu.get_class().get_name(),
                                              "same_button_class": self.button.get_class().get_name(),
                                              "active": True, "native_async_layer_push": True})
                if self.index == 0:
                    self.report["image"] = str(self.path.parent / "open-menu.png")
                    self.capture_not_before = time.monotonic() + 1.0
                    self.state, self.phase_started = "capture_wait", time.monotonic()
                else:
                    self.active_menu.call_function("DeactivateWidget")
                    self.state = "closing"
            elif self.state == "capture_wait" and time.monotonic() >= self.capture_not_before:
                check(len(active) == 1 and self.active_menu.call_function("IsVisible"), "activated menu is not visible")
                self.report["cases"][-1]["visible_after_transition"] = True
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="' + self.report["image"] + '"', self.controller)
                self.state, self.phase_started = "capture", time.monotonic()
            elif self.state == "capture" and Path(self.report["image"]).is_file():
                self.active_menu.call_function("DeactivateWidget")
                self.state = "closing"
            elif self.state == "closing" and not active:
                self.report["cases"][-1]["native_deactivated"] = True
                self.index += 1
                if self.index == 3:
                    self.report["python_clicks"] = getattr(self.button, "_uep_open_menu_clicks", 0)
                    self.finish()
                    return False
                self.click()
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPOpenMenuResult="
result = next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))
validation = OpenMenuValidation(result)
ticker = ue.add_ticker(validation.tick)
