"""One native CommonUI activation per trial; observe existing GAS Jump only."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import Vector2D
from uep_lyra_network_bots import isolate_bots
from . import action_touch_mixin as policy
from .action_touch_click_contract import PLAN, require
from .weapon_observer import valid


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.finished, self.observer_closed, self.widgets, self.events, self.index = False, False, [], [], 0
        self.report = dict(schema_version=1, status="running", error=None, cases=[], synthetic_commonui_activation=True,
            native_input_gas_jump_tested=True, player_restored=False)
        for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_touch_tested",
                      "jump_or_launch_called_by_probe", "velocity_or_gravity_written", "ability_granted_by_probe"):
            self.report[field] = False

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
            if not (snapshot.bExperienceLoaded and snapshot.bHealthReady and snapshot.bHeroInputReady):
                continue
            self.world = world
            self.controller = self.statics.call_function("GetPlayerController", world, 0)
            self.pawn = self.controller.get_controlled_pawn()
            if not valid(self.pawn):
                continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            self.movement = self.pawn.CharacterMovement
            if int(self.movement.MovementMode) != 1:
                continue
            self.original = dict(location=self.pawn.get_actor_location(), rotation=self.pawn.get_actor_rotation(),
                aim=self.controller.call_function("GetControlRotation"), mode=int(self.movement.MovementMode),
                custom=int(self.movement.CustomMovementMode), health=float(snapshot.Health))
            self.jump_action = ue.load_object(ue.find_class("InputAction"), "/Game/Input/Actions/IA_Jump.IA_Jump")
            self.player_class, self.original_jump = self.pawn.get_class(), self.pawn.find_function("OnJumped")
            require(not any(row["target_class"] == self.player_class for row in ue.get_registered_mixins()),
                    "click observer must not replace a production Character router")
            owner = self

            class ObserveJump:
                def OnJumped(self):
                    if self.get_path_name() == owner.pawn.get_path_name():
                        owner.events.append(self.get_path_name())
                    self.call_mixin_original("OnJumped")

            ue.register_mixin_profile(self.player_class, "UEPActionClickObserve", ObserveJump, make_default=True)
            self.report["player_pawn"] = self.pawn.get_path_name()
            self.begin()
            return

    def begin(self):
        self.kind, self.profile = PLAN[self.index]
        cls = ue.load_class(policy.CLASS if self.kind == "base" else policy.MOBILE_CLASS)
        self.widget = self.controller.create_widget(cls)
        self.widget.add_to_root(); self.widgets.append(self.widget)
        ue.set_mixin_profile(self.widget, self.profile)
        self.widget.set_property("AssociatedAction", self.jump_action)
        self.widget.AddToViewport(500)
        self.widget.SetPositionInViewport(Vector2D(X=30., Y=40.), False)
        self.widget.SetDesiredSizeInViewport(Vector2D(X=160., Y=160.))
        self.widget.call_function("SetIsEnabled", True)
        self.cls, self.event_start, self.click_start = cls, len(self.events), policy.snapshot()["clicks"]
        self.enter("settle")

    def activate(self):
        require(int(self.movement.MovementMode) == 1, "native player is not grounded before CommonUI click")
        self.start_z = float(self.pawn.get_actor_location().z)
        # Synthetic activation of the existing native CommonUI entry, NOT a
        # direct BP/Python click, input injection, Jump or ability call.
        self.widget.call_function("HandleButtonClicked")
        self.enter("jump")

    def observe(self):
        rise = float(self.pawn.get_actor_location().z)-self.start_z
        velocity = float(self.pawn.call_function("GetVelocity").z)
        if not (rise > 20. and velocity > 20.):
            require(time.monotonic()-self.phase_started < 4., "CommonUI click did not trigger native Jump: "+
                repr(dict(events=self.events[self.event_start:], rise=rise, velocity=velocity,
                    clicks=policy.snapshot()["clicks"]-self.click_start, mode=int(self.movement.MovementMode))))
            return
        events = self.events[self.event_start:]
        require(len(events) == 1, "native Jump repeated/crossed owner")
        self.report["cases"].append(dict(kind=self.kind, profile=self.profile, native_commonui_activations=1,
            native_jump_events=len(events), jump_event_pawn=events[0], rise=rise, vertical_velocity=velocity,
            movement_mode=int(self.movement.MovementMode), python_clicks=policy.snapshot()["clicks"]-self.click_start,
            native_type_preserved=self.widget.get_class() == self.cls))
        ue.log("UEP_ACTION_TOUCH_CLICK_CASE_PASSED "+self.kind+"/"+self.profile)
        self.widget.RemoveFromParent(); ue.clear_mixin_profile(self.widget); self.widget.remove_from_root()
        self.enter("land")

    def restore_player(self):
        if not hasattr(self, "original"):
            return
        self.movement.call_function("StopMovementImmediately")
        self.pawn.set_actor_location(self.original["location"])
        self.pawn.set_actor_rotation(self.original["rotation"])
        self.controller.call_function("SetControlRotation", self.original["aim"])
        self.movement.call_function("SetMovementMode", self.original["mode"], self.original["custom"])
        current, expected = self.pawn.get_actor_location(), self.original["location"]
        health = self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        require(max(abs(getattr(current, k)-getattr(expected, k)) for k in ("x", "y", "z")) < .01 and
                abs(health.call_function("GetHealth")-self.original["health"]) < .01,
                "native click player restore/Health differs")
        self.report["player_restored"] = True

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 220., "action-touch click timeout: "+self.phase)
            if self.phase == "ready":
                self.ready()
            elif self.phase == "settle" and time.monotonic()-self.phase_started > .3:
                self.activate()
            elif self.phase == "jump":
                self.observe()
            elif self.phase == "land":
                # Let the existing ability release and normal gravity land.
                require(time.monotonic()-self.phase_started < 10., "native Jump did not finish/land")
                if int(self.movement.MovementMode) == 1 and time.monotonic()-self.phase_started > .3:
                    self.restore_player(); self.index += 1
                    if self.index == len(PLAN):
                        self.finish()
                    else:
                        self.begin()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finish(self, failure=None):
        if self.finished:
            return
        self.finished = True
        try:
            for widget in self.widgets:
                widget.RemoveFromParent(); ue.clear_mixin_profile(widget)
                if widget.is_rooted():
                    widget.remove_from_root()
            self.restore_player()
            if hasattr(self, "original_jump"):
                require(ue.unregister_mixin(self.player_class) and self.pawn.find_function("OnJumped") == self.original_jump,
                        "native OnJumped observer not restored")
            self.observer_closed = True
        except Exception:
            failure = (failure or "")+traceback.format_exc()
        self.report.update(status="failed" if failure else "awaiting_shutdown", error=failure,
            widgets_created=len(self.widgets), widget_roots_released=sum(not w.is_rooted() for w in self.widgets),
            jump_observer_closed=self.observer_closed, elapsed_seconds=time.monotonic()-self.started)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if failure else ue.log)("UEP_ACTION_TOUCH_CLICK_DIFFERENTIAL_"+("FAILED "+failure if failure else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .action_touch_click_contract import validate
                self.report["status"] = "passed"; validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_ACTION_TOUCH_CLICK_SHUTDOWN_"+self.report["status"].upper())


result = next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-UEPActionTouchClickResult="))
validation = Validation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
