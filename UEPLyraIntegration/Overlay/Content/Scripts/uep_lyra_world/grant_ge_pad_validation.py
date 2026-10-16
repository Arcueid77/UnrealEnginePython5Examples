"""Real Pawn collision/GAS; native Timeline callbacks, never replayed events."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_bots import isolate_bots
from . import grant_ge_pad_mixin as policy
from .grant_ge_pad_contract import CASES, equal

def check(value, message):
    if not value:
        raise AssertionError(message)

def path(value):
    return value.get_path_name() if valid(value) else None

class Validation:
    def __init__(self, result):
        self.result, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.index, self.finished, self.actors, self.values = 0, False, [], []
        self.pawn = self.pad = None
        self.scope = SubscriptionScope()
        self.report = {"schema_version": 1, "status": "running", "error": None, "cases": [], "timeline_samples": {},
            "fixture_duration": 15.0, "original_default_duration": 15.0, "native_player_restored": False,
            "native_baseline_health": 75.0, "cooldown_seconds": {}}
        for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "manual_lifecycle_event", "handler_called_by_probe",
                     "timeline_driven_by_probe", "attributes_written_by_probe", "full_default_duration_tested", "culture_switch_tested"):
            self.report[flag] = False

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def state(self, percent=False):
        result = {"active": bool(self.pad.bActive), "text": str(self.pad.Text.get_property("Text")),
            "tick": bool(self.pad.call_function("IsActorTickEnabled")), "light": bool(self.pad.PointLight.get_property("bVisible")),
            "mesh_hidden": bool(self.pad.ItemMesh.get_property("bHiddenInGame"))}
        if percent:
            result["percent"] = float(self.pad.MID_TimerIndicator.call_function("K2_GetScalarParameterValue", "Percent"))
        return result

    def record(self, name, value):
        check(name == CASES[len(self.values)], "grant-GE case order differs")
        self.values.append(value)

    def ready(self):
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge):
                continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            state = bridge.call_function("CaptureSnapshot")
            if not (state.bExperienceLoaded and state.bHealthReady and state.bAbilitySystemReady and not state.bDamageImmune):
                continue
            check(str(state.NetMode) == "Standalone", "grant-GE standalone authority required")
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):
                continue
            self.world, self.bridge, self.pawn = world, bridge, controller.get_controlled_pawn()
            self.health = self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            self.movement = self.pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
            self.original_location, self.original_health = self.pawn.get_actor_location(), float(self.health.call_function("GetHealth"))
            self.original_mode, self.original_custom = int(self.movement.MovementMode), int(self.movement.CustomMovementMode)
            self.movement.call_function("StopMovementImmediately")
            self.movement.call_function("DisableMovement")
            self.cls = ue.load_class(policy.CLASS)
            self.report["original_default_duration"] = float(self.cls.get_cdo().Duration)
            check(self.report["original_default_duration"] == 15.0, "default cooldown changed")
            self.report["full_default_duration_tested"] = True
            self.report["effect_duration_policy"] = int(self.cls.get_cdo().GameplayEffectToApply.get_cdo().DurationPolicy)
            check(self.report["effect_duration_policy"] == 0, "fixture only certifies original instant GE")
            bp = ue.load_object(ue.find_class("Blueprint"), policy.CLASS[:-2])
            self.curve = bp.Timelines[0].FloatTracks[0].CurveFloat
            self.start_profile()
            return

    def set_health(self, value, command):
        current = float(self.health.call_function("GetHealth"))
        if abs(current-value) < .001:
            return
        result = self.bridge.call_function("ApplyAuthorityHealthDelta", command, value-current, False)
        check(result.bApplied and abs(float(result.HealthAfter)-value) < .001, "native GAS baseline/restore rejected: "+str(result.Status))

    def start_profile(self):
        self.set_health(75.0, "grant-ge.baseline."+str(self.index))
        self.center = ue.FVector(self.original_location.x+6000.0+self.index*1500.0, self.original_location.y, self.original_location.z+500.0)
        transform = ue.FTransform()
        transform.translation = self.center
        self.pad = self.statics.call_function("BeginDeferredActorSpawnFromClass", self.world, self.cls, transform, 1, None)
        check(valid(self.pad), "native grant-GE pad spawn failed")
        self.actors.append(self.pad)
        ue.set_mixin_profile(self.pad, ("Python", "BlueprintFallback")[self.index])
        self.statics.call_function("FinishSpawningActor", self.pad, transform)
        check(float(self.pad.Duration) == 15.0, "native instance default cooldown differs")
        check(self.pad.get_class() == self.cls, "grant-GE class identity changed")
        self.values, self.events = [], []
        self.scope = SubscriptionScope()
        self.scope.bind_event(self.pad.Volume, "OnComponentBeginOverlap", lambda component, actor, *rest:
                              self.events.append("begin") if actor == self.pawn else None)
        self.scope.bind_event(self.pad.Volume, "OnComponentEndOverlap", lambda component, actor, *rest:
                              self.events.append("end") if actor == self.pawn else None)
        self.enter("construction")

    def profile_done(self):
        self.scope.close()
        self.pad.actor_destroy()
        if self.index == 0:
            self.first_values = self.values
            self.index = 1
            self.start_profile()
        else:
            for name, left, right in zip(CASES, self.first_values, self.values):
                check(equal(left, right), "grant-GE BP/Python differs: "+name+" "+repr((left, right)))
                self.report["cases"].append({"name": name, "passed": True, "same_class": True, "python": left, "blueprint": right})
            self.finish()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            check(time.monotonic()-self.started < 230, "grant-GE timeout: "+self.phase)
            if self.phase == "ready":
                self.ready()
            elif self.phase == "construction" and time.monotonic()-self.phase_started > .25:
                value = self.state(True)
                value["mesh"] = path(self.pad.ItemMesh.get_property("StaticMesh"))
                light = self.pad.PointLight.call_function("GetLightColor")
                value["light_color"] = [float(getattr(light, field)) for field in ("r", "g", "b", "a")]
                self.record(CASES[0], value)
                self.yaw = float(self.pad.Scene.get_property("RelativeRotation").yaw)
                self.world_time = float(self.statics.call_function("GetTimeSeconds", self.world))
                self.enter("tick")
            elif self.phase == "tick" and time.monotonic()-self.phase_started > .35:
                yaw = float(self.pad.Scene.get_property("RelativeRotation").yaw)
                seconds = float(self.statics.call_function("GetTimeSeconds", self.world))-self.world_time
                change = (yaw-self.yaw+180.0)%360.0-180.0
                self.record(CASES[1], {"yaw_rate": change/seconds})
                check(self.pawn.set_actor_location(self.pad.Volume.call_function("K2_GetComponentLocation")), "native grant-GE enter rejected")
                self.enter("inside")
            elif self.phase == "inside" and time.monotonic()-self.phase_started > .12:
                check(self.events == ["begin"], "physical grant-GE begin missing/duplicated")
                self.record(CASES[2], {"health": float(self.health.call_function("GetHealth")),
                    "mesh_hidden": bool(self.pad.ItemMesh.get_property("bHiddenInGame"))})
                check(self.pawn.set_actor_location(ue.FVector(self.center.x+500.0, self.center.y, self.center.z)), "native grant-GE leave rejected")
                check(self.events == ["begin", "end"], "physical grant-GE end missing/duplicated")
                self.record(CASES[3], self.state())
                self.charge_started = float(self.statics.call_function("GetTimeSeconds", self.world))
                self.enter("progress")
            elif self.phase == "progress":
                position = float(self.pad.TL_Charge.call_function("GetPlaybackPosition"))
                actual = float(self.pad.MID_TimerIndicator.call_function("K2_GetScalarParameterValue", "Percent"))
                expected = float(self.curve.call_function("GetFloatValue", position))
                check(not self.pad.bActive, "native Timeline completed before intermediate sample")
                if .15 < actual < .85:
                    paused = not self.pad.call_function("IsActorTickEnabled")
                    self.record(CASES[4], {"curve_matches": abs(actual-expected) < .002, "actor_tick_paused": paused,
                        "timeline_playing": bool(self.pad.TL_Charge.call_function("IsPlaying"))})
                    self.report["timeline_samples"][("python", "blueprint")[self.index]] = {"position": position, "actual": actual, "native_expected": expected}
                    self.enter("finish")
            elif self.phase == "finish" and self.pad.bActive and not self.pad.TL_Charge.call_function("IsPlaying"):
                self.report["cooldown_seconds"][("python", "blueprint")[self.index]] = float(self.statics.call_function("GetTimeSeconds", self.world))-self.charge_started
                self.record(CASES[5], self.state(True))
                self.profile_done()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.scope.close()
            for pad in self.actors:
                if valid(pad):
                    pad.actor_destroy()
            check(not any(valid(pad) for pad in self.actors), "grant-GE fixture pad retained")
            if valid(self.pawn):
                self.set_health(self.original_health, "grant-ge.restore")
                check(self.pawn.set_actor_location(self.original_location), "native grant-GE player restore rejected")
                self.movement.call_function("StopMovementImmediately")
                self.movement.call_function("SetMovementMode", self.original_mode, self.original_custom)
                location = self.pawn.get_actor_location()
                self.report["player_restore"] = {"health": float(self.health.call_function("GetHealth")), "expected_health": self.original_health,
                    "position_max_error": max(abs(getattr(location, key)-getattr(self.original_location, key)) for key in ("x", "y", "z")),
                    "movement": [int(self.movement.MovementMode), int(self.movement.CustomMovementMode)],
                    "expected_movement": [self.original_mode, self.original_custom]}
                restore = self.report["player_restore"]
                self.report["native_player_restored"] = (abs(restore["health"]-self.original_health) < .001 and
                    restore["position_max_error"] < .01 and restore["movement"] == restore["expected_movement"])
                check(self.report["native_player_restored"], "native grant-GE player restore observation differs")
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error, actors_created=len(self.actors),
            actors_destroyed=sum(not valid(pad) for pad in self.actors), fixture_scope_closed=self.scope.closed,
            elapsed_seconds=time.monotonic()-self.started)
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_GRANT_GE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .grant_ge_pad_contract import validate
                self.report["status"] = "passed"
                validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_GRANT_GE_SHUTDOWN_"+self.report["status"].upper())


result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPGrantGEResult="))
validation = Validation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
