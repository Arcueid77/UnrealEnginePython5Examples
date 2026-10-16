"""Mounted native UMG BP/Python pairs; typed synthetic messages, no manual Tick."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage, Vector2D
from uep_lyra_network_bots import isolate_bots
from . import action_touch_mixin as policy
from .action_touch_contract import cases_for, equal, require
from .weapon_observer import valid

CHANNEL = "Ability.Interaction.Duration.Message"


def margin(value):
    return [float(getattr(value, name)) for name in ("Left", "Top", "Right", "Bottom")]


def state(widget):
    layout = ue.find_class("WidgetLayoutLibrary").get_cdo()
    return dict(charging=bool(widget.Charging), duration=float(widget.Duration), started=float(widget.StartTime),
        disabled=bool(widget.get_property("isDisabled")),
        visibility={name: int(getattr(widget, name).call_function("GetVisibility")) for name in
            ("BackingBorder", "Shadow", "BackgroundBlur", "ItemGlow", "DisableGlowBoostOvr")},
        padding={name: margin(layout.call_function("SlotAsOverlaySlot", getattr(widget, name)).get_property("Padding"))
                 for name in ("MainSBWithPadding", "ItemGlow", "ItemGlow_Boost", "BackgroundBlur")},
        materials={name: {key: float(policy.material(widget, name).call_function("K2_GetScalarParameterValue", key)) for key in
            ("Animate_Cooldown", "Animate_ActiveToInactive", "Animate_FromEmpty")} for name in ("WeaponCard", "ItemGlow")})


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.widgets, self.index, self.kind_index, self.finished, self.paused = [], 0, 0, False, False
        self.report = dict(schema_version=1, status="running", cases=[], error=None,
            test_owned_mounted_pairs=True, direct_bp_functions_called_by_probe=True, native_commonui_state_changes=True,
            synthetic_typed_duration_producer=True, native_widget_reconstruction_tested=False)
        for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_touch_tested",
                     "native_input_action_effect_tested", "widget_tick_called_by_probe", "production_placement_tested"):
            self.report[flag] = False

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def ready(self):
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge):
                continue
            snapshot = bridge.call_function("CaptureSnapshot")
            if not (snapshot.bExperienceLoaded and snapshot.bHealthReady):
                continue
            self.world = world
            self.controller = self.statics.call_function("GetPlayerController", world, 0)
            if not valid(self.controller) or not valid(self.controller.get_controlled_pawn()):
                continue
            self.pawn = self.controller.get_controlled_pawn()
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetGameInstanceSubsystem", world, ue.find_class("GameplayMessageSubsystem"))
            self.foreign = world.actor_spawn(ue.find_class("Actor"))
            self.begin_kind()
            return

    def begin_kind(self):
        self.kind = ("base", "mobile")[self.kind_index]
        self.cases = cases_for(self.kind)
        self.cls = ue.load_class((policy.CLASS, policy.MOBILE_CLASS)[self.kind_index])
        self.pair = []
        for index, profile in enumerate(("Python", "BlueprintFallback")):
            widget = self.controller.create_widget(self.cls)
            widget.add_to_root(); self.widgets.append(widget); self.pair.append(widget)
            ue.set_mixin_profile(widget, profile)
            widget.set_property("DurationMessageTag", GameplayTag(TagName=CHANNEL))
            widget.call_function("SetIsSelectable", True)
            widget.AddToViewport(500)
            widget.SetPositionInViewport(Vector2D(X=30.+index*220., Y=40.), False)
            widget.SetDesiredSizeInViewport(Vector2D(X=160., Y=160.))
            widget.call_function(policy.RESUME)
        self.report.setdefault("native_widget_scheduling", []).append(dict(kind=self.kind,
            cdo={field: self.cls.get_cdo().get_property(field) for field in ("TickFrequency", "bHasScriptImplementedTick", "Visibility")},
            widgets=[{field: widget.get_property(field) for field in ("TickFrequency", "bHasScriptImplementedTick", "Visibility")} for widget in self.pair]))
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        self.candidate, self.baseline = self.pair
        self.index = 0
        self.enter("settle")

    def broadcast(self, duration, foreign=False):
        def diagnostic(widget):
            return dict(state=state(widget), playing=widget.call_function("IsAnimationPlaying", widget.CooldownInactiveToActive),
                typed_playing=ue.call_function_by_class(widget, ue.find_class("UserWidget"), "IsAnimationPlaying",
                    {"InAnimation": widget.CooldownInactiveToActive}),
                animation_time=widget.call_function("GetAnimationCurrentTime", widget.CooldownInactiveToActive))
        before = [diagnostic(widget) for widget in self.pair]
        self.candidate.call_function("BroadcastActionDuration", self.router, GameplayTag(TagName=CHANNEL),
            LyraInteractionDurationMessage(Instigator=self.foreign if foreign else self.pawn, Duration=duration))
        self.report.setdefault("message_diagnostics", []).append(dict(duration=duration, foreign=foreign,
            before=before, after=[diagnostic(widget) for widget in self.pair],
            python_callback_playing=getattr(self.candidate, "_uep_action_message_playing", None)))

    def compare(self, name):
        actual, baseline = state(self.candidate), state(self.baseline)
        self.report["last_comparison"] = dict(kind=self.kind, name=name, python=actual, blueprint=baseline)
        require(equal(actual, baseline), "native action-touch BP/Python differs: "+repr(self.report["last_comparison"]))
        self.report["cases"].append(dict(kind=self.kind, name=name, same_class=self.candidate.get_class() == self.baseline.get_class(),
            python=actual, blueprint=baseline, automatic_ticks=self.candidate._uep_action_ticks))
        ue.log("UEP_ACTION_TOUCH_CASE_PASSED "+self.kind+"/"+name)

    def act(self):
        name = self.cases[self.index]
        if name == "style-flags":
            for widget in self.pair:
                widget.set_property("UseBacking", False); widget.set_property("UseGlowBoost", False)
                widget.set_property("BlurCornerRadius", 18.)
                widget.call_function("SetButtonStyle")
        elif name == "primed-reset":
            for widget in self.pair:
                for image, value in (("WeaponCard", .2), ("ItemGlow", .4)):
                    policy.material(widget, image).call_function("SetScalarParameterValue", "Animate_ActiveToInactive", value)
                widget.call_function("ResetMaterials")
        elif name in ("disabled", "enabled"):
            for widget in self.pair:
                widget.call_function("SetIsEnabled", name == "enabled")
        elif name in ("selected", "deselected"):
            for widget in self.pair:
                widget.call_function("SetIsSelected", name == "selected", False)
        elif name == "owner-duration":
            self.broadcast(1.5)
        elif name == "foreign-owner-ignored":
            self.before_foreign = [(widget.Duration, widget.StartTime) for widget in self.pair]
            self.broadcast(5., True)
            require(self.before_foreign == [(widget.Duration, widget.StartTime) for widget in self.pair], "foreign duration changed model")
        elif name == "restart-duration":
            self.broadcast(.8)
        elif name == "paused-game-time":
            self.pause_state = [state(widget) for widget in self.pair]
            require(self.statics.call_function("SetGamePaused", self.world, True), "native pause failed")
            self.paused = True
        elif name == "destruct-no-delivery":
            for widget in self.pair:
                widget.RemoveFromParent()
            self.enter("unmounted")
            return
        elif name == "native-reconstruct":
            for widget in self.pair:
                widget.AddToViewport(500)
            self.report["native_widget_reconstruction_tested"] = True
            self.broadcast(.5)
        elif name == "live-profile-roundtrip":
            ue.set_mixin_profile(self.candidate, "BlueprintFallback")
            self.candidate.call_function(policy.RESUME)
            ue.set_mixin_profile(self.candidate, "Python")
            self.candidate.call_function(policy.RESUME)
            self.broadcast(.5)
            # Tick counters restart for a fresh Profile. Wait native ticks again.
        self.enter("wait")

    def advance(self):
        name = self.cases[self.index]
        if name == "paused-game-time":
            require(all(equal(value, state(widget)) for value, widget in zip(self.pause_state, self.pair)), "paused UMG model changed")
            image = str(self.path.parent/("action-touch-"+self.kind+".png"))
            ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                'Shot SHOWUI -nosuffix filename="'+image+'"', self.controller)
            self.report.setdefault("images", []).append(image)
            require(self.statics.call_function("SetGamePaused", self.world, False), "native unpause failed")
            self.paused = False
        if name == "completed":
            require(not self.candidate.Charging and not self.baseline.Charging, "native cooldown did not complete")
        elif name == "original-child-no-tick":
            require(self.candidate._uep_action_ticks == 0 and self.candidate.Charging and self.baseline.Charging,
                    "original MobileOnly no-Tick behavior changed")
        self.compare(name)
        self.index += 1
        if self.index == len(self.cases):
            for widget in self.pair:
                widget.RemoveFromParent()
            self.kind_index += 1
            if self.kind_index == 2:
                self.finish()
            else:
                self.begin_kind()
        else:
            self.act()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 220., "action-touch timeout: "+self.phase)
            age = time.monotonic()-getattr(self, "phase_started", self.started)
            if self.phase == "ready":
                self.ready()
            elif self.phase == "settle" and age > .6:
                self.act()
            elif self.phase == "wait":
                delay = 1.1 if self.cases[self.index] in ("completed", "original-child-no-tick") else (.25 if self.cases[self.index] == "paused-game-time" else .12)
                if age > delay:
                    self.advance()
            elif self.phase == "unmounted" and age > .12:
                require(self.candidate._uep_action_scope is None, "action-touch Destruct kept scope")
                before = [(w.Duration, w.StartTime) for w in self.pair]
                self.broadcast(9.)
                require(before == [(w.Duration, w.StartTime) for w in self.pair], "unmounted action-touch received duration")
                self.advance()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finish(self, failure=None):
        if self.finished:
            return
        self.finished = True
        try:
            if self.paused:
                self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            for widget in self.widgets:
                widget.RemoveFromParent()
                # Native removal handles Destruct. Unbind also verifies the
                # Profile teardown path and disarms any retained native proxy.
                ue.clear_mixin_profile(widget)
                widget.remove_from_root()
            if valid(getattr(self, "foreign", None)):
                self.foreign.actor_destroy()
            self.report.update(widgets_created=len(self.widgets), widgets_removed=len(self.widgets),
                widget_roots_released=sum(not w.is_rooted() for w in self.widgets),
                owned_listeners_closed=not any(w.get_path_name() in policy.snapshot()["active_widgets"] for w in self.widgets))
            if failure is None:
                require(len(self.report.get("images", [])) == 2 and all(Path(p).is_file() for p in self.report["images"]),
                        "native action-touch comparison screenshot missing")
        except Exception:
            failure = (failure or "")+traceback.format_exc()
        self.report.update(status="failed" if failure else "awaiting_shutdown", error=failure,
            elapsed_seconds=time.monotonic()-self.started)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if failure else ue.log)("UEP_ACTION_TOUCH_DIFFERENTIAL_"+("FAILED "+failure if failure else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .action_touch_contract import validate
                self.report["status"] = "passed"; validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_ACTION_TOUCH_SHUTDOWN_"+self.report["status"].upper())


result = next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-UEPActionTouchResult="))
validation = Validation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
