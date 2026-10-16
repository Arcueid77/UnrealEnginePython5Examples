"""Physical BP/Python launcher trials on owned native Character fixtures."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_bots import isolate_bots
from .effect_pad_mixin import valid
from . import launcher_mixin as policy
from .launcher_contract import PLAN, equal, require

def vec(value):
    return [float(getattr(value, key)) for key in ("x", "y", "z")]

class Validation:
    def __init__(self, result):
        self.result, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.index = self.profile_index = 0
        self.finished, self.actors, self.scope = False, [], None
        self.report = {"schema_version": 1, "status": "running", "cases": [], "error": None,
            "native_physics_fixture_configured": True, "native_collision_pairs": 0,
            "scopes_created": 0, "scopes_closed": 0, "trial_samples": []}
        for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "collision_handler_called_by_probe",
                     "native_launch_called_by_probe", "velocity_written_after_entry", "player_modified", "cue_visual_parity_tested"):
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
            state = bridge.call_function("CaptureSnapshot")
            if not (state.bExperienceLoaded and state.bHealthReady):
                continue
            require(str(state.NetMode) == "Standalone", "launcher standalone authority required")
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            self.world = world
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):
                continue
            self.origin = controller.get_controlled_pawn().get_actor_location()
            self.classes = [ue.load_class(path) for path in policy.CLASSES]
            self.report["original_replication_flags"] = [bool(cls.get_cdo().get_property("bReplicates")) for cls in self.classes]
            self.report["rpc_signature"] = ue.describe_function(self.classes[0], "Activate VFX")
            self.report["overlap_signatures"] = [ue.describe_function(cls, "Overlap") for cls in self.classes]
            # NetMulticast remains in the existing native BP UFunction flags.
            self.report["rpc_signature_preserved"] = bool(self.report["rpc_signature"]["flags"] & 0x4000)
            require(self.report["rpc_signature_preserved"], "launcher multicast flag missing")
            self.start_trial()
            return

    def own(self, actor):
        require(valid(actor), "launcher fixture native spawn failed")
        self.actors.append(actor)
        return actor

    def start_trial(self):
        self.name, self.kind, self.expected_launch = PLAN[self.index]
        self.profile = ("BlueprintFallback", "Python")[self.profile_index]
        self.before = policy.snapshot()
        offset = (self.index*2+self.profile_index)*1500.0
        self.center = ue.FVector(self.origin.x+6000.0+offset, self.origin.y, self.origin.z+2200.0)
        transform = ue.FTransform();transform.translation = self.center
        self.cls = self.classes[("parent", "push", "up").index(self.kind)]
        self.pad = self.own(self.statics.call_function("BeginDeferredActorSpawnFromClass", self.world, self.cls, transform, 1, None))
        ue.set_mixin_profile(self.pad, self.profile)
        if self.kind == "push":
            self.pad.set_property("Target", ue.FVector(150.0, 200.0, -30.0) if "target" in self.name else ue.FVector(6000.0, -6000.0, 700.0))
            self.pad.set_property("Use Target", "target" in self.name)
        if "fall" in self.name:
            self.pad.set_property("Do Not Activate on Fall Entry", True)
        self.statics.call_function("FinishSpawningActor", self.pad, transform)
        require(self.pad.get_class() == self.cls, "launcher native type changed")
        self.pawn = self.own(self.world.actor_spawn(ue.find_class("Character"),
            ue.FVector(self.center.x+1000.0, self.center.y, self.center.z), ue.FRotator(0.0, 0.0, 35.0)))
        self.ai = None
        if "ai" in self.name:
            self.ai = self.own(self.world.actor_spawn(ue.find_class("AIController")))
            self.ai.call_function("Possess", self.pawn)
        self.movement = self.pawn.CharacterMovement
        # Only fixture Characters: stable zero-gravity native falling lets the
        # first native LaunchCharacter result be read without frame-time drift.
        # The real Lyra player, Health and production movement remain untouched.
        for field, value in (("GravityScale", 0.0), ("BrakingDecelerationFlying", 0.0),
                             ("BrakingDecelerationFalling", 0.0), ("MaxFlySpeed", 10000.0),
                             ("FallingLateralFriction", 0.0), ("AirControl", 0.0), ("bRunPhysicsWithNoController", True)):
            self.movement.set_property(field, value)
        self.movement.call_function("SetMovementMode", 3, 0)
        z = -1500.0 if "fall" in self.name else 90.0
        self.movement.set_property("Velocity", ue.FVector(35.0, 12.0, z))
        self.events = []
        self.scope = SubscriptionScope();self.report["scopes_created"] += 1
        self.scope.bind_event(self.pad.Sphere, "OnComponentBeginOverlap", lambda component, actor, *rest:
            self.events.append("begin") if actor == self.pawn else None)
        self.enter("baseline")

    def construction(self):
        mid = self.pad.LauncherMesh.call_function("GetMaterial", 0)
        color = mid.call_function("K2_GetVectorParameterValue", "Color")
        light = self.pad.PointLight.call_function("GetLightColor")
        result = {"glow": float(mid.call_function("K2_GetScalarParameterValue", "Intensity")),
            "material_color": [float(getattr(color, key)) for key in ("r", "g", "b", "a")],
            "light_color": [float(getattr(light, key)) for key in ("r", "g", "b", "a")],
            "light_intensity": float(self.pad.PointLight.get_property("Intensity")),
            "light_radius": float(self.pad.PointLight.get_property("AttenuationRadius")),
            "sphere_radius": float(self.pad.Sphere.call_function("GetUnscaledSphereRadius"))}
        if self.kind == "push":
            result["target"] = vec(self.pad.Target)
        return result

    def trigger(self):
        self.initial = vec(self.pawn.call_function("GetVelocity"))
        self.last_update = vec(self.movement.call_function("GetLastUpdateVelocity"))
        self.forward = vec(self.pawn.call_function("GetActorForwardVector"))
        self.constructed = self.construction()
        if "fall" in self.name:
            require(self.last_update[2] < float(self.pad.MinimumVerticalVelocityAllowed), "native falling baseline not reached")
        center = self.pad.Sphere.call_function("K2_GetComponentLocation")
        require(self.pawn.set_actor_location(center), "native launcher collision entry rejected")
        require(self.events == ["begin"], "native launcher begin missing/duplicated")
        self.report["native_collision_pairs"] += 1
        self.enter("observe")

    def expected_velocity(self):
        if not self.expected_launch:
            return self.initial
        if self.kind == "up":
            return [self.initial[0]+self.forward[0], self.initial[1]+self.forward[1], float(self.pad.UpOverride)]
        if "target" in self.name:
            target = vec(self.pad.Target);speed = (target[0]**2+target[1]**2)**.5*2.1
            launch = [self.forward[0]*speed, self.forward[1]*speed, max(250.0, min(850.0, target[2]*2.0))]
        else:
            launch = [self.forward[0]*self.pad.Multiplier, self.forward[1]*self.pad.Multiplier, self.pad.UpOverride*self.pad.Multiplier]
        return [a+b for a,b in zip(self.initial, launch)]

    def observe(self):
        require(not policy.snapshot()["errors"], "launcher Python policy error: "+repr(policy.snapshot()["errors"]))
        actual, expected = vec(self.pawn.call_function("GetVelocity")), self.expected_velocity()
        mode = int(self.movement.MovementMode)
        value = {"collision_begins": len(self.events), "pawn_selected": self.pad.OverlappingPawn == self.pawn,
            "class_preserved": self.pad.get_class() == self.cls,
            "launched": max(abs(a-b) for a,b in zip(actual, self.initial)) > .01,
            "movement_mode": mode, "initial_velocity": self.initial, "velocity": actual,
            "velocity_error": max(abs(a-b) for a,b in zip(actual, expected)), "construction": self.constructed,
            "native_ai_controller": valid(self.ai), "fall_condition_observed": "fall" in self.name and
                self.last_update[2] < float(self.pad.MinimumVerticalVelocityAllowed)}
        require(value["launched"] == self.expected_launch and value["velocity_error"] < .01,
                "native launcher velocity/launch differs: "+repr(value))
        after = policy.snapshot()
        counters = {key: after[key]-self.before[key] for key in after if key != "errors"}
        self.report["trial_samples"].append({"name": self.name, "profile": self.profile, "outcome": value,
            "expected_velocity": expected, "native_last_update_velocity": self.last_update, "python_counters": counters})
        self.close_trial()
        if self.profile_index == 0:
            self.original = value
            self.profile_index = 1
            self.start_trial()
        else:
            require(equal(value, self.original), "launcher BP/Python result differs: "+self.name)
            self.report["cases"].append({"name": self.name, "passed": True, "same_class": True,
                "python": value, "blueprint": self.original, "python_counters": counters})
            ue.log("UEP_LAUNCHER_CASE_PASSED "+self.name)
            self.index, self.profile_index = self.index+1, 0
            if self.index == len(PLAN):
                self.finish()
            else:
                self.start_trial()

    def close_trial(self):
        if self.scope is not None and not self.scope.closed:
            self.scope.close();self.report["scopes_closed"] += 1
        for actor in (getattr(self, "pawn", None), getattr(self, "ai", None), getattr(self, "pad", None)):
            if valid(actor):
                actor.actor_destroy()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 220, "launcher timeout: "+self.phase)
            if self.phase == "ready":
                self.ready()
            elif self.phase == "baseline" and time.monotonic()-self.phase_started > .15:
                self.trigger()
            elif self.phase == "observe" and time.monotonic()-self.phase_started > .08:
                self.observe()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.close_trial()
            for actor in self.actors:
                if valid(actor):
                    actor.actor_destroy()
            require(not any(valid(actor) for actor in self.actors), "launcher fixture actor remained")
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
            actors_created=len(self.actors), actors_destroyed=sum(not valid(actor) for actor in self.actors),
            elapsed_seconds=time.monotonic()-self.started)
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_LAUNCHER_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        # Do not call UObject methods from Python shutdown.
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .launcher_contract import validate
                self.report["status"] = "passed";validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_LAUNCHER_SHUTDOWN_"+self.report["status"].upper())

result = next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-UEPLauncherResult="))
validation = Validation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
