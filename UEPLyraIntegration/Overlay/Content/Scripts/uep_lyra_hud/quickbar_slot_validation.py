"""Bounded production slot/BP comparisons; named-output query stays explicit."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraQuickBarSlotsChangedMessage, LyraQuickBarActiveIndexChangedMessage, Geometry, PointerEvent
from . import quickbar_slot_mixin as slots
from .weapon_observer import valid
from uep_lyra_network_bots import isolate_bots

CASES = ("native-production-slots", "typed-owner-slots", "foreign-owner-ignored", "empty-slot-message",
         "repeated-native-slot-restore", "invalid-index-preserves-slot", "external-named-query-python",
         "blueprint-profile-resume", "python-profile-resume", "native-mouse-axis-entry",
         "destruct-no-late-delivery", "same-widget-native-reconstruct")


def check(value, reason):
    if not value:
        raise AssertionError(reason)


def path(value):
    return value.get_path_name() if valid(value) else None


def visual(widget):
    return {"index": int(widget.SlotIndex), "empty": bool(widget.IsEmpty), "selected": bool(widget.IsSelected),
            "numeric": float(widget.WeaponAmmoCount.call_function("GetTargetValue")),
            "text": str(widget.WeaponAmmoCount.call_function("GetText")),
            "icon": path(widget.WeaponCard.call_function("GetDynamicMaterial").call_function("K2_GetTextureParameterValue", "IconTexture")),
            "ammo_icon": path(widget.AmmoIcon.call_function("GetDynamicMaterial").call_function("K2_GetTextureParameterValue", "TextureMask")),
            "animations": [bool(widget.call_function("IsAnimationPlaying", getattr(widget, name))) for name in
                           ("ToEmpty", "InactiveToActive", "ActiveToInactive")]}


class QuickBarValidation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.widgets, self.pairs, self.helper = [], [], None
        self.report = {"schema_version": 1, "status": "running", "cases": [], "full_acceptance": False,
                       "network_acceptance": False, "native_inventory_properties_written": False,
                       "fixture_lifecycle_event_invoked": False, "physical_mouse_tested": False,
                       "external_named_query_migrated": True, "native_weapon_switch_tested": False,
                       "baseline_init_policy": "default Python initialization, then BP Profile and explicit listener resume",
                       "bp_initialization_parity_tested": False}
        atexit.register(self.finalize)

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def broadcast(self, entries=None, owner=None):
        self.helper.call_function("BroadcastQuickBarSlots", self.router, GameplayTag(TagName=slots.ROWS[0][0]),
            LyraQuickBarSlotsChangedMessage(Owner=owner or self.controller, Slots=self.entries if entries is None else entries))

    def compare(self, name, pairs=None, lifecycle=False):
        rows = []
        for candidate, baseline in pairs or self.pairs:
            actual, original = visual(candidate), visual(baseline)
            check(actual == original, "quickbar BP/Python differs: "+repr((name, actual, original)))
            check(candidate.get_class() == baseline.get_class(), "quickbar class changed")
            rows.append({"python": actual, "blueprint": original, "widget": candidate.get_path_name(),
                         "profile": str(ue.get_mixin_profile(candidate))})
        self.report["cases"].append({"name": name, "slots": rows, "test_owned_lifecycle_widget": lifecycle})

    def ready(self):
        statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge):
                continue
            isolate_bots(statics, world, ue.find_class("LyraPlayerBotController"))
            data = bridge.call_function("CaptureSnapshot")
            if not (data.bExperienceLoaded and data.bHealthReady and not data.bDamageImmune):
                continue
            controller = statics.call_function("GetPlayerController", world, 0)
            cls = ue.load_class(slots.CLASS)
            available, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("GetAllWidgetsOfClass", world, [], cls, False)
            candidates = [value for value in available if value.call_function("GetOwningPlayer") == controller]
            if len(candidates) != 3:
                self.report["readiness"] = {"candidate_count": len(candidates)}
                continue
            self.world, self.controller = world, controller
            self.quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
            check(valid(self.quickbar), "native QuickBar missing")
            self.entries = list(self.quickbar.call_function("GetSlots"))
            check(valid(self.entries[0]), "native initial item missing")
            for candidate in sorted(candidates, key=lambda value: int(value.SlotIndex)):
                check(str(ue.get_mixin_profile(candidate)) == "Python", "production quickbar not Python")
                baseline = controller.create_widget(cls)
                baseline.SlotIndex, baseline.SlotInputAction = candidate.SlotIndex, candidate.SlotInputAction
                ue.set_mixin_profile(baseline, "BlueprintFallback")
                baseline.AddToViewport(450)
                baseline.call_function("SetRenderOpacity", 0.0)
                baseline.call_function(slots.RESUME)
                for widget in (candidate, baseline):
                    widget.add_to_root()
                    self.widgets.append(widget)
                self.pairs.append((candidate, baseline))
            self.report["production_widgets"] = [candidate.get_path_name() for candidate, baseline in self.pairs]
            self.helper = ue.new_object(candidates[0].PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetGameInstanceSubsystem", world,
                ue.find_class("GameplayMessageSubsystem"))
            self.enter("initial")
            return

    def finish(self, error=None):
        try:
            for candidate, baseline in self.pairs:
                if valid(baseline):
                    baseline.RemoveFromParent()
            for widget in getattr(self, "lifecycle", []):
                if valid(widget):
                    widget.RemoveFromParent()
            for widget in self.widgets:
                if valid(widget):
                    widget.remove_from_root()
            if valid(self.helper):
                self.helper.remove_from_root()
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic()-self.started)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_QUICKBAR_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        final = slots.snapshot()
        self.report["shutdown"] = final
        pool = final["pool_lifetime"]
        if (final["active_count"] or final["scopes_created"] != final["scopes_closed"] or final["errors"] or
                pool["active_count"] or pool["ticker_active"] or pool["registered"] != pool["unregistered"] or pool["errors"]):
            self.report.update(status="failed", error="quickbar observers survived shutdown")
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_QUICKBAR_SHUTDOWN_"+self.report["status"].upper())

    def tick(self, delta):
        try:
            check(time.monotonic()-self.started < 200, "quickbar total timeout")
            if self.phase == "ready":
                self.ready()
                return True
            elapsed = time.monotonic()-self.phase_started
            check(elapsed < 25, "quickbar phase timeout: "+self.phase)
            if elapsed < 1.8:
                return True  # Settle the retained animations on both sides.
            if self.phase == "initial":
                self.compare("native-production-slots")
                self.before = [candidate._uep_slot_messages for candidate, baseline in self.pairs]
                self.broadcast()
                self.enter("owner")
            elif self.phase == "owner":
                check(all(candidate._uep_slot_messages == before+1 for (candidate, baseline), before in zip(self.pairs, self.before)), "owner quickbar not exact-once")
                self.compare("typed-owner-slots")
                before = [visual(widget) for widget in self.widgets]
                self.broadcast([None], self.controller.PlayerState)
                check([visual(widget) for widget in self.widgets] == before, "foreign quickbar owner changed UI")
                self.compare("foreign-owner-ignored")
                self.broadcast([None, None, None])
                self.enter("empty")
            elif self.phase == "empty":
                self.compare("empty-slot-message")
                check(all(candidate.IsEmpty for candidate, baseline in self.pairs), "typed empty slots not shown")
                self.broadcast()
                self.broadcast()
                self.enter("restore")
            elif self.phase == "restore":
                self.compare("repeated-native-slot-restore")
                self.report["image"] = str(self.path.parent / "quickbar-slots.png")
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="'+self.report["image"]+'"', self.controller)
                pair = self.pairs[0]
                for widget in pair:
                    widget.SlotIndex = 99  # Isolated widget configuration, not native QuickBar Slots.
                before = [visual(widget) for widget in pair]
                self.broadcast([])
                check([visual(widget) for widget in pair] == before, "invalid index altered slot")
                self.compare("invalid-index-preserves-slot", [pair])
                for widget in pair:
                    widget.SlotIndex = 0
                    answer = widget.call_function("IsThisTheActiveQuickbarSlot")
                    check(type(answer) is tuple and len(answer) == 1 and answer[0] is slots.native_active(widget), "retained named query differs")
                check(slots.snapshot()["named_query_calls"] > 0, "external named query did not enter Python")
                self.compare("external-named-query-python")
                for candidate, baseline in self.pairs:
                    ue.set_mixin_profile(candidate, "BlueprintFallback")
                    candidate.call_function(slots.RESUME)
                self.broadcast()
                self.enter("fallback")
            elif self.phase == "fallback":
                self.compare("blueprint-profile-resume")
                for candidate, baseline in self.pairs:
                    ue.set_mixin_profile(candidate, "Python")
                    candidate.call_function(slots.RESUME)
                self.broadcast()
                self.enter("python")
            elif self.phase == "python":
                self.compare("python-profile-resume")
                before_mouse = slots.snapshot()["mouse_calls"]
                for widget in self.pairs[0]:
                    reply = widget.call_function(slots.MOUSE, Geometry(), PointerEvent())
                    check(reply.get_struct().get_name() == "EventReply", "mouse return struct missing")
                check(slots.snapshot()["mouse_calls"] == before_mouse+1, "Python mouse entry failed or ran twice")
                self.report["mouse_reply_observation"] = "native EventReply type; internal handled bit not reflected"
                self.enter("mouse")
            elif self.phase == "mouse":
                self.compare("native-mouse-axis-entry")
                cls = self.pairs[0][0].get_class()
                self.lifecycle = [self.controller.create_widget(cls), self.controller.create_widget(cls)]
                for widget in self.lifecycle:
                    widget.SlotIndex = 0
                    widget.add_to_root()
                    self.widgets.append(widget)
                ue.set_mixin_profile(self.lifecycle[1], "BlueprintFallback")
                for widget in self.lifecycle:
                    widget.AddToViewport(450)
                    widget.call_function("SetRenderOpacity", 0.0)
                self.enter("lifecycle")
            elif self.phase == "lifecycle":
                self.original_proxies = [getattr(self.lifecycle[1], row[3]) for row in slots.ROWS]
                check(all(valid(proxy) and proxy.call_function("IsActive") for proxy in self.original_proxies), "original quickbar proxies missing")
                for widget in self.lifecycle:
                    widget.RemoveFromParent()
                check(self.lifecycle[0]._uep_slot_scope is None and not any(proxy.call_function("IsActive") for proxy in self.original_proxies), "native Destruct did not close quickbar")
                before = self.lifecycle[0]._uep_slot_messages
                self.broadcast([None, None, None])
                check(self.lifecycle[0]._uep_slot_messages == before, "removed quickbar accepted late owner")
                self.compare("destruct-no-late-delivery", [self.lifecycle], True)
                for widget in self.lifecycle:
                    widget.AddToViewport(450)
                self.broadcast()
                self.enter("remount")
            elif self.phase == "remount":
                self.compare("same-widget-native-reconstruct", [self.lifecycle], True)
                check([case["name"] for case in self.report["cases"]] == list(CASES), "quickbar case inventory differs")
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


result = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("-UEPQuickBarSlotResult=")), None)
if result:
    _validation = QuickBarValidation(result)
    _ticker = ue.add_ticker(_validation.tick, 0.0)
