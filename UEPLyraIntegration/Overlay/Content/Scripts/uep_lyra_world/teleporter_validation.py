"""Real native overlap -> BP/Python teleport trials; never replay handlers."""
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
from . import teleporter_mixin as policy
from .teleporter_contract import PLAN, UNSUPPORTED, equal, require


def vec(value):
    return [float(getattr(value, k)) for k in ("x", "y", "z")]


def rotation(value):
    return [float(getattr(value, k)) for k in ("pitch", "yaw", "roll")]


def error(a, b):
    return max(abs(x-y) for x, y in zip(a, b))


class Validation:
    def __init__(self, result):
        self.result, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.index = self.profile_index = 0
        self.finished, self.actors, self.scope = False, [], None
        self.report = dict(schema_version=1, status="running", cases=[], error=None, trial_samples=[],
            native_physics_fixture_configured=True, native_collision_pairs=0, scopes_created=0, scopes_closed=0)
        self.report.update({flag: False for flag in UNSUPPORTED})

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
            require(str(snapshot.NetMode) == "Standalone", "standalone teleporter authority required")
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):
                continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            self.world, self.origin = world, controller.get_controlled_pawn().get_actor_location()
            self.cls = ue.load_class(policy.CLASS)
            self.report["original_replication_flag"] = bool(self.cls.get_cdo().get_property("bReplicates"))
            self.signatures = {n: ue.describe_function(self.cls, n) for n in
                ("Set Teleporter Destination", "Teleport Audio for Pawn", "Teleport Audio for Grenade", "UserConstructionScript")}
            require(all(not (signature["flags"] & 0x40) for signature in self.signatures.values()), "unexpected teleporter RPC")
            self.start_trial()
            return

    def own(self, actor):
        require(valid(actor), "teleporter native fixture spawn failed")
        self.actors.append(actor)
        return actor

    def spawn_portal(self, position, receiver):
        transform = ue.FTransform(); transform.translation = position
        actor = self.own(self.statics.call_function("BeginDeferredActorSpawnFromClass", self.world, self.cls, transform, 1, None))
        ue.set_mixin_profile(actor, self.profile)
        actor.set_property("ReceiverOnly", receiver)
        actor.set_property("LaunchOnTeleport", self.name != "no-launch")
        actor.set_property("bForceDirection", self.name != "free-direction")
        actor.set_property("KeepReleativeEntryUponExit", self.name.startswith("relative-"))
        self.statics.call_function("FinishSpawningActor", actor, transform)
        actor.set_actor_rotation(self.yaw(90.0 if receiver else 25.0))
        return actor

    @staticmethod
    def yaw(value):
        result = ue.FRotator(); result.yaw = value
        return result

    def start_trial(self):
        self.name, self.profile = PLAN[self.index], ("BlueprintFallback", "Python")[self.profile_index]
        self.before = policy.snapshot()
        # Same coordinates for both lanes; fixture actors are destroyed between.
        self.center = ue.FVector(self.origin.x+7000.+self.index*3000., self.origin.y, self.origin.z+2500.)
        self.target = self.spawn_portal(ue.FVector(self.center.x, self.center.y+1600., self.center.z), True)
        self.source = self.spawn_portal(self.center, False)
        self.source.set_property("TeleportingTarget", [self.target])
        self.pawn = self.own(self.world.actor_spawn(ue.find_class("Character"),
            ue.FVector(self.center.x+900., self.center.y, self.center.z), self.yaw(13.0)))
        self.pawn.set_property("bUseControllerRotationYaw", False)
        self.controller = None
        if self.name != "no-controller":
            self.controller = self.own(self.world.actor_spawn(ue.find_class("AIController")))
            self.controller.call_function("Possess", self.pawn)
            self.controller.call_function("SetControlRotation", self.yaw(13.0))
        self.movement = self.pawn.CharacterMovement
        for field, value in (("GravityScale", 0.0), ("BrakingDecelerationFalling", 0.0),
                             ("FallingLateralFriction", 0.0), ("AirControl", 0.0), ("bRunPhysicsWithNoController", True)):
            self.movement.set_property(field, value)
        self.movement.call_function("SetMovementMode", 3, 0)
        self.movement.set_property("Velocity", ue.FVector(0., 0., 0.))
        mesh_z = 900. if self.name == "relative-upper" else (-900. if self.name == "relative-lower" else 50.)
        self.pawn.Mesh.call_function("K2_SetRelativeLocation", ue.FVector(30., 40., mesh_z), False, bTeleport=False)
        self.events = []
        self.scope = SubscriptionScope(); self.report["scopes_created"] += 1
        self.scope.bind_event(self.source.Box, "OnComponentBeginOverlap", lambda component, actor, *rest:
            self.events.append("begin") if actor == self.pawn else None)
        self.scope.bind_event(self.source.Box, "OnComponentEndOverlap", lambda component, actor, *rest:
            self.events.append("end") if actor == self.pawn else None)
        self.enter("baseline")

    def niagara(self, actor):
        result = {}
        for name, kind in (("EdgeWidth", "Float"), ("PortalWidth", "Float"), ("PortalHeight", "Float"),
            ("Spread", "Float"), ("Phase", "Float"), ("Brightness", "Float"), ("NumPlanes", "Int"),
            ("SystemEntered", "Int"), ("Inward", "Bool")):
            output = ue.call_function_by_class(actor.Niagara, ue.find_class("NiagaraComponent"),
                "GetVariable"+kind, {"InVariableName": name})
            require(output["bIsValid"] is True, "missing native teleporter Niagara variable: "+name)
            result[name] = output["ReturnValue"]
        return result

    def trigger(self):
        # Construction can replace the deferred SCS component. Query the live
        # component list, not a stale pre-FinishSpawning wrapper/property.
        require(valid(self.source.Box) and not valid(self.target.get_component_by_type(ue.find_class("BoxComponent"))),
                "receiver-only native Box destruction differs")
        self.construction = dict(source=self.niagara(self.source), target=self.niagara(self.target))
        entry = self.source.Box.call_function("K2_GetComponentLocation")
        # Compute expected offset independently through the native BP math library.
        local_mesh = self.pawn.Mesh.call_function("K2_GetComponentLocation")
        pawn_before = self.pawn.get_actor_location()
        mesh_at_entry = ue.FVector(*(getattr(local_mesh, k)-getattr(pawn_before, k)+getattr(entry, k) for k in ("x", "y", "z")))
        exit_component = self.target.get_property("Exit Direction")
        self.exit_location = exit_component.call_function("K2_GetComponentLocation")
        self.expected_location = vec(self.exit_location)
        math = ue.find_class("KismetMathLibrary").get_cdo()
        if self.name.startswith("relative-"):
            base = self.source.DefaultSceneRoot1.call_function("K2_GetComponentLocation")
            normal = self.source.DefaultSceneRoot1.call_function("GetForwardVector")
            point = math.call_function("ProjectPointOnToPlane", mesh_at_entry, base, normal)
            delta = [getattr(point, k)-getattr(base, k) for k in ("x", "y", "z")]
            delta[2] = math.call_function("FClamp", delta[2], 0., self.source.TeleporterHeight-100.)
            self.expected_location = [a+b for a, b in zip(self.expected_location, delta)]
        forward = exit_component.call_function("GetForwardVector")
        self.expected_rotation = rotation(math.call_function("Conv_VectorToRotator", forward))
        self.expected_control = self.expected_rotation if self.name not in ("free-direction", "no-controller") else [0., 13., 0.]
        self.expected_velocity = [v*self.source.LaunchMultiplier for v in vec(forward)] if self.name != "no-launch" else [0., 0., 0.]
        self.pawn.set_actor_location(entry)  # Native collision; no handler/teleport/launch replay.
        self.immediate_location = vec(self.pawn.get_actor_location())
        self.immediate_rotation = rotation(self.pawn.get_actor_rotation())
        # AIController may copy Pawn orientation on its next tick even with the
        # teleporter force-direction branch disabled. Observe that branch at its
        # actual synchronous boundary, not after a different native system runs.
        self.immediate_control = rotation(self.controller.call_function("GetControlRotation")) if valid(self.controller) else [0., 13., 0.]
        self.report["native_collision_pairs"] += 1
        self.enter("observe")

    def observe(self):
        require(not policy.snapshot()["errors"], "teleporter policy errors: "+repr(policy.snapshot()["errors"]))
        velocity = vec(self.pawn.call_function("GetVelocity"))
        control = self.immediate_control
        value = dict(events=list(self.events), destination_selected=self.source.TeleporterDestination == self.target,
            receiving_pawn=self.target.ReceivingPawn == self.pawn,
            class_preserved=self.source.get_class() == self.cls and self.target.get_class() == self.cls,
            receiver_box_destroyed=not valid(self.target.get_component_by_type(ue.find_class("BoxComponent"))),
            position_error=error(self.immediate_location, self.expected_location),
            rotation_error=error(self.immediate_rotation, self.expected_rotation),
            control_error=error(control, self.expected_control), velocity_error=error(velocity, self.expected_velocity),
            launched=any(abs(v) > .1 for v in velocity), velocity=velocity,
            exit_offset=[a-b for a, b in zip(self.immediate_location, vec(self.exit_location))], construction=self.construction)
        self.report["trial_samples"].append(dict(name=self.name, profile=self.profile, outcome=value,
            actual_location=self.immediate_location, expected_location=self.expected_location,
            actual_rotation=self.immediate_rotation, expected_rotation=self.expected_rotation,
            actual_control=control, expected_control=self.expected_control, expected_velocity=self.expected_velocity))
        require(all(value[key] < .01 for key in ("position_error", "rotation_error", "control_error", "velocity_error")),
                "native teleporter transform/control/launch differs: "+repr(value))
        after = policy.snapshot()
        counts = {key: after[key]-self.before[key] for key in after if key != "errors"}
        self.close_trial()
        if self.profile_index == 0:
            self.original, self.profile_index = value, 1
            self.start_trial()
        else:
            require(equal(value, self.original), "native teleporter BP/Python differs: "+self.name)
            self.report["cases"].append(dict(name=self.name, passed=True, same_class=True,
                python=value, blueprint=self.original, python_counters=counts))
            ue.log("UEP_TELEPORTER_CASE_PASSED "+self.name)
            self.index, self.profile_index = self.index+1, 0
            if self.index == len(PLAN):
                self.finish()
            else:
                self.start_trial()

    def close_trial(self):
        if self.scope is not None and not self.scope.closed:
            self.scope.close(); self.report["scopes_closed"] += 1
        for name in ("pawn", "controller", "source", "target"):
            actor = getattr(self, name, None)
            if valid(actor):
                actor.actor_destroy()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 220, "teleporter timeout: "+self.phase)
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

    def finish(self, failure=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.close_trial()
            for actor in self.actors:
                if valid(actor):
                    actor.actor_destroy()
            require(not any(valid(actor) for actor in self.actors), "native teleporter fixture remained")
            self.report["original_signatures_preserved"] = all(ue.describe_function(self.cls, n) == signature
                for n, signature in self.signatures.items())
        except Exception:
            failure = (failure or "")+traceback.format_exc()
        self.report.update(status="failed" if failure else "awaiting_shutdown", error=failure,
            actors_created=len(self.actors), actors_destroyed=sum(not valid(a) for a in self.actors),
            elapsed_seconds=time.monotonic()-self.started)
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if failure else ue.log)("UEP_TELEPORTER_DIFFERENTIAL_"+("FAILED "+failure if failure else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()  # No UObject calls at shutdown.
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .teleporter_contract import validate
                self.report["status"] = "passed"; validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_TELEPORTER_SHUTDOWN_"+self.report["status"].upper())


result = next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-UEPTeleporterResult="))
validation = Validation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
