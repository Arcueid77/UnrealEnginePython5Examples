"""Opt-in rendered UMG fixture, NOT a GAS/delegate/network acceptance claim.

Run only in /Engine/Maps/Entry with GameModeBase. Deterministic health values
drive the real Python presenter and the real W_Healthbar animations/materials.
Normal Lyra startup never imports this module.
"""

import atexit
import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.classes import GameplayStatics, KismetSystemLibrary
from unreal_engine.structs import Vector2D

from . import bootstrap, state


def check(condition, message):
    if not condition:
        raise AssertionError(message)


class FixtureHealth:
    """Test-only input source; never attached to a Lyra Pawn or ASC."""

    health = 100.0
    maximum = 100.0

    def is_valid(self):
        return True

    def call_function(self, name):
        if name == "GetHealth":
            return self.health
        if name == "GetMaxHealth":
            return self.maximum
        raise AssertionError(name)


class VisualValidation:
    def __init__(self, result_path):
        self.path = Path(result_path)
        check(not self.path.exists(), "refusing to overwrite visual evidence")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.started = time.monotonic()
        self.phase_started = self.started
        self.phase = "create"
        self.widget = None
        self.world = None
        self.controller = None
        self.health = FixtureHealth()
        self.pending_capture = None
        self.switch_during_animation = "-UEPLyraHUDSwitchDuringAnimation" in sys.argv
        self.report = {
            "schema_version": 1,
            "status": "running",
            "scope": "isolated real UMG rendering with deterministic presenter inputs",
            "full_acceptance": False,
            "gas_delegate_network_acceptance": False,
            "engine_version": [ue.ENGINE_MAJOR_VERSION, ue.ENGINE_MINOR_VERSION],
            "python_version": sys.version.split()[0],
            "frames": [],
            "switch_during_animation": self.switch_during_animation,
        }

    def write(self):
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def goto(self, phase):
        self.phase = phase
        self.phase_started = time.monotonic()

    def change_health(self, health):
        old = self.health.health
        self.health.health = health
        self.widget._on_health_changed(self.health, old, health, None)

    def capture(self, name, next_phase):
        path = self.path.with_name(self.path.stem + "-" + name + ".png")
        check(not path.exists(), "refusing to overwrite screenshot")
        # CommonUI exposes the target but not its private current float. Read
        # the actual rendered numeric text (the lane pins culture=en).
        current = float(str(self.widget.HealthNumber.call_function("GetText")).replace(",", ""))
        target = float(self.widget.HealthNumber.call_function("GetTargetValue"))
        if "interpolating" in name:
            check(min(self.previous_health, self.health.health) < current < max(self.previous_health, self.health.health),
                  name + " did not capture a real intermediate number: " + str(current))
        else:
            check(abs(current - self.health.health) < 0.01, name + " number did not settle")
        check(abs(target - self.health.health) < 0.01, name + " target mismatch")
        self.report["frames"].append({
            "name": name, "image": str(path), "current": current, "target": target,
            "normalized": float(self.widget.NormalizedHealth),
            "pending_elimination": bool(self.widget._uep_hud_pending_elimination),
            "animations": state.snapshot()["animation_events"],
        })
        KismetSystemLibrary.ExecuteConsoleCommand(self.world, 'Shot SHOWUI -nosuffix filename="' + str(path) + '"', self.controller)
        self.pending_capture = (path, next_phase)
        self.goto("capture_wait")

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 120.0, "visual validation timed out in " + self.phase)
            check(not state.snapshot()["errors"], "presenter errors: " + repr(state.snapshot()["errors"]))
            elapsed = time.monotonic() - self.phase_started
            if self.phase == "create":
                for world in ue.all_worlds():
                    if world.get_world_type() not in (1, 3, 5):
                        continue
                    check("/Engine/Maps/Entry" in world.get_path_name(), "visual fixture requires the isolated Entry map")
                    controller = GameplayStatics.GetPlayerController(world, 0)
                    if controller is None:
                        continue
                    self.world, self.controller = world, controller
                    self.widget = controller.create_widget(ue.load_class(bootstrap.HEALTHBAR_CLASS_PATH))
                    self.widget.AddToViewport(50)
                    self.widget.SetPositionInViewport(Vector2D(X=100.0, Y=260.0), False)
                    self.widget.SetDesiredSizeInViewport(Vector2D(X=1080.0, Y=180.0))
                    self.widget._cleanup_bindings("isolated_visual_fixture")
                    self.widget._uep_hud_health = self.health
                    self.health.health = self.health.maximum = 0.0
                    self.widget._update_visuals("fixture_pre_asc")
                    self.health.health = self.health.maximum = 100.0
                    self.widget._on_health_changed(self.health, 100.0, 100.0, None)
                    check(float(self.widget.HealthNumber.call_function("GetTargetValue")) == 100.0,
                          "first identical positive ASC notification left the UI at zero")
                    check(state.snapshot()["animation_events"][-1]["animation"] == "OnSpawned",
                          "first ready ASC notification did not clear eliminated presentation")
                    self.report["delayed_asc_bootstrap_recovered"] = True
                    self.widget._update_visuals("fixture_initial")
                    check(state.snapshot()["active_widget_count"] == 1, "fixture must own exactly one presenter")
                    self.goto("initial")
                    break
            elif self.phase == "capture_wait":
                path, next_phase = self.pending_capture
                if path.exists() and path.stat().st_size > 0:
                    self.write()
                    self.goto(next_phase)
            elif self.phase in ("initial", "respawn") and elapsed > 2.0:
                self.capture(self.phase, "damage_start" if self.phase == "initial" else "cleanup")
            elif self.phase in ("damage_start", "heal_start", "death_start"):
                self.previous_health = self.health.health
                self.change_health({"damage_start": 60.0, "heal_start": 100.0, "death_start": 0.0}[self.phase])
                self.goto(self.phase.replace("_start", "_interpolating"))
            elif self.phase in ("damage_interpolating", "heal_interpolating", "death_interpolating") and elapsed > 0.12:
                self.capture(self.phase, self.phase.replace("_interpolating", "_settled"))
            elif self.phase in ("damage_settled", "heal_settled", "death_settled") and elapsed > 2.0:
                if self.phase == "death_settled":
                    check(not self.widget._uep_hud_pending_elimination, "OnAnimationFinished did not finish the death chain")
                    check(state.snapshot()["animation_events"][-1]["animation"] == "OnEliminated", "death animation was not selected")
                self.capture(self.phase, {"damage_settled": "heal_start", "heal_settled": "death_start", "death_settled": "respawn_start"}[self.phase])
            elif self.phase == "respawn_start":
                self.change_health(100.0)
                self.goto("respawn")
            elif self.phase == "cleanup":
                self.report["hud_before_exit"] = state.snapshot()
                if self.switch_during_animation:
                    # No animation update has happened yet: stopping now may
                    # synchronously emit OnAnimationFinished during teardown.
                    self.change_health(0.0)
                    ue.set_mixin_profile(self.widget, "BlueprintFallback")
                    check(ue.get_mixin_profile(self.widget) == "BlueprintFallback", "profile switch failed")
                    check(not self.widget.call_function("IsAnimationPlaying", self.widget.OnDamaged), "old animation is still playing")
                    check(not self.widget._uep_hud_pending_elimination, "old death completion is still armed")
                self.widget.RemoveFromParent()
                # Do not synthesize Destruct/teardown. Observe real engine exit.
                self.widget = None
                self.report["status"] = "awaiting_shutdown"
                self.write()
                ue.request_exit()
                return False
            return True
        except Exception:
            self.report["status"] = "failed"
            self.report["error"] = traceback.format_exc()
            self.write()
            ue.log_error("UEP_LYRA_HUD_VISUAL_FAILED " + self.report["error"])
            ue.request_exit()
            return False

    def finalize(self):
        self.report["shutdown"] = state.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                final = self.report["shutdown"]
                check(not final["errors"], "shutdown reported presenter errors")
                check(final["active_widget_count"] == final["live_widget_reference_count"] == 0, "widget references leaked")
                check(final["controller_bind_count"] == final["controller_unbind_count"], "controller callback leaked")
                check(final["health_bind_count"] == final["health_unbind_count"], "health callback leaked")
                check(len(self.report["frames"]) == 8, "missing visual frames")
                check(final["public_entry_counts"]["EventOnEliminated"] >= 1,
                      "native animation completion did not traverse public Python elimination entry")
                self.report["status"] = "passed"
                ue.log("UEP_LYRA_HUD_VISUAL_PASSED")
            except Exception:
                self.report["status"] = "failed"
                self.report["error"] = traceback.format_exc()
                ue.log_error("UEP_LYRA_HUD_VISUAL_FAILED " + self.report["error"])
        self.write()


result_path = next(argument.split("=", 1)[1].strip('"') for argument in sys.argv if argument.startswith("-UEPLyraHUDVisualResult="))
validation = VisualValidation(result_path)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
