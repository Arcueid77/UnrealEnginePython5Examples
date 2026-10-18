"""Native grenade RPC, actual fuse and swept enemy contact, with live GAS."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod, ESpawnActorScaleMethod
from unreal_engine.structs import GameplayTag, GameplayEventData
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Activation
from . import grenade_detonate_mixin as policy
from .grenade_detonate_contract import CLASS, PLAN, require, validate


def path(obj):
    return obj.get_path_name() if valid(obj) else None


class Validation(Ready):
    healths = Activation.healths

    def __init__(self, result):
        super().__init__(result)
        self.require_auto_active = False
        self.actors, self.events, self.hits, self.poses, self.controllers = [], [], [], {}, {}
        self.finish_events = []
        self.target, self.installed, self.cleaned = None, False, False
        self.report = dict(schema_version=1, status="running", error=None, cases=[], observation_errors=[], full_acceptance=False,
            network_acceptance=False, packaged_runtime=False, physical_input_tested=False, health_properties_written=False,
            rpc_function_overridden=False, body_callback_replayed=False, particle_completion_replayed=False,
            audio_playback_tested=False, quantitative_flight_tested=False, natural_particle_completion_accepted=False)

    def box(self, label, location, extent):
        actor = self.world.actor_spawn(ue.find_class("Actor"), location)
        self.actors.append(actor)
        box = actor.add_actor_root_component(ue.find_class("BoxComponent"), label)
        box.call_function("SetBoxExtent", extent, False)
        box.call_function("SetCollisionObjectType", 0)
        box.call_function("SetCollisionResponseToAllChannels", 2)
        box.call_function("SetCollisionEnabled", 1)
        require(actor.call_function("K2_TeleportTo", location, ue.FRotator()), "native fixture pose refused")
        return actor, box

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report["native_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"] == "Standalone", "isolated explosion fixture requires Standalone")
        self.cls = ue.load_class(CLASS)
        ue.register_declared_mixin(self.cls)
        self.rpc_signature = ue.describe_function(self.cls, "Detonate")
        self.radius = float(self.cls.get_cdo().get_property("Radius"))
        require(100. < self.radius < 2000., "unexpected original blast radius")
        self.teams = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem", self.world, ue.find_class("LyraTeamSubsystem"))
        self.floor, _ = self.box("UEPDetonateFloor", ue.FVector(200000., 200000., 1980.), ue.FVector(5000., 5000., 20.))
        self.wall, self.wall_box = self.box("UEPDetonateWall", ue.FVector(200000.+self.radius*.2, 200000., 2100.), ue.FVector(8., 150., 150.))
        self.wall_box.call_function("SetCollisionEnabled", 0)
        self.original_view = self.controller.call_function("GetViewTarget")
        self.camera = self.world.actor_spawn(ue.find_class("CameraActor"))
        self.actors.append(self.camera)
        require(self.camera.call_function("K2_TeleportTo", ue.FVector(199700., 200000., 2250.), ue.FRotator(-26., 0., 0.)), "native fixture camera pose refused")
        self.controller.call_function("SetViewTargetWithBlend", self.camera, 0., 0, 0., False)
        binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == self.cls]
        self.original_classes = {name: value["python_class"] for name, value in binding["profiles"].items()}
        owner = self
        for name, base in self.original_classes.items():
            def around_body(handler, profile):
                def invoke(actor):
                    watched = actor == owner.target
                    counts = policy.evidence(actor)
                    handler(actor)
                    if watched:
                        owner.events.append(dict(profile=profile, elapsed=owner.game_time()-owner.spawn_time, stats=copy.deepcopy(counts)))
                invoke.override = policy.BODY
                return invoke
            def around_hit(handler):
                def invoke(actor, MyComp, Other, OtherComp, bSelfMoved, HitLocation, HitNormal, NormalImpulse, Hit):
                    watched = actor == owner.target
                    if watched:
                        row = dict(other=path(Other), fuse_before=owner.fuse(actor))
                    handler(actor, MyComp, Other, OtherComp, bSelfMoved, HitLocation, HitNormal, NormalImpulse, Hit)
                    if watched:
                        row["fuse_after"] = owner.fuse(actor)
                        owner.hits.append(row)
                return invoke
            def around_destroy(handler):
                def invoke(actor, PSystem):
                    watched, component = actor == owner.target, path(PSystem)
                    handler(actor, PSystem)
                    if watched:
                        owner.finish_events.append(component)
                invoke.override = "Destroy Grenade"
                return invoke
            methods = {key: value for key, value in vars(base).items() if not key.startswith("__") and callable(value)}
            methods["DetonateBody"] = around_body(base.DetonateBody, name)
            methods["ReceiveHit"] = around_hit(base.ReceiveHit)
            methods["DestroyGrenade"] = around_destroy(base.DestroyGrenade)
            ue.register_mixin_profile(self.cls, name, type("ObservedGrenadeDetonate"+name, (), methods))
        self.installed = True
        self.reset_sent = set()
        self.enter("source")

    def fuse(self, actor):
        return bool(ue.find_class("KismetSystemLibrary").get_cdo().call_function("K2_TimerExistsHandle", self.world, actor.get_property("Timer")))

    def source(self):
        require(time.monotonic()-self.phase_started < 45., "native healthy bot source/reset timeout")
        self.name, self.profile = PLAN[self.index]
        wanted = 0 if self.name == "friendly-rpc" else 1
        bots, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraPlayerBotController"))
        for controller in bots:
            if wanted in self.controllers and controller != self.controllers[wanted]:
                continue
            pawn = controller.get_controlled_pawn()
            if not valid(pawn) or int(self.teams.call_function("CompareTeams", pawn, self.pawn)[0]) != wanted:
                continue
            self.controllers[wanted] = controller
            health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            asc = ability_system(pawn)
            if not valid(health) or not valid(asc) or health.call_function("IsDeadOrDying"):
                continue
            if health.call_function("GetHealth") != 100.:
                if path(pawn) not in self.reset_sent:
                    tag = GameplayTag(TagName="GameplayEvent.RequestReset")
                    owner = controller.PlayerState
                    ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor", owner, tag, GameplayEventData(EventTag=tag, Instigator=owner, Target=owner))
                    self.reset_sent.add(path(pawn))
                continue
            if asc.call_function("GetGameplayTagCount", GameplayTag(TagName="Gameplay.DamageImmunity")):
                continue
            if path(pawn) not in self.poses:
                self.poses[path(pawn)] = (pawn, pawn.get_actor_location(), pawn.get_actor_rotation())
            self.victim, self.victim_health = pawn, health
            destination = ue.FVector(202500. if self.name.startswith("empty") else 200000.+self.radius*.6, 200000., 2100.)
            require(pawn.call_function("K2_TeleportTo", destination, ue.FRotator()), "native target pose refused")
            pawn.call_function("GetMovementComponent").call_function("StopMovementImmediately")
            self.wall_box.call_function("SetCollisionEnabled", 1 if self.name == "occluded-rpc" else 0)
            self.enter("settle")
            return

    def spawn(self):
        blast_origin = ue.FVector(200000., 200000., 2100.)
        from unreal_engine.enums import EObjectTypeQuery
        overlap = policy.native_outputs("KismetSystemLibrary", "SphereOverlapActors", policy.library("KismetSystemLibrary").call_function(
            "SphereOverlapActors", WorldContextObject=self.world, SpherePos=blast_origin, SphereRadius=self.radius,
            ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery3], ActorClassFilter=ue.find_class("Pawn"), ActorsToIgnore=[]))
        actual_pawns = sorted(path(pawn) for pawn in overlap["OutActors"])
        expected_pawns = [] if self.name.startswith("empty") else [path(self.victim)]
        require(actual_pawns == expected_pawns, "native explosion fixture contains unintended Pawn targets: "+str(actual_pawns))
        transform = ue.FTransform(ue.FVector(200000., 200000., 2100.), ue.FRotator(), ue.FVector(1., 1., 1.))
        scale = ESpawnActorScaleMethod.OverrideRootScale
        actor = self.statics.call_function("BeginDeferredActorSpawnFromClass", self.world, self.cls, transform, ESpawnActorCollisionHandlingMethod.AlwaysSpawn, None, scale)
        require(valid(actor), "native grenade spawn failed")
        self.actors.append(actor)
        actor.set_property("Instigator", self.pawn)
        ue.set_mixin_profile(actor, self.profile)
        self.events, self.hits, self.finish_events, self.target = [], [], [], actor
        self.spawn_time = self.game_time()
        self.health_before = self.healths()
        self.row = dict(name=self.name, profile=self.profile, **{"class": path(actor.get_class())},
            health_before=float(self.victim_health.call_function("GetHealth")), victim=path(self.victim),
            native_role=int(actor.call_function("GetLocalRole")),
            team_comparison=int(self.teams.call_function("CompareTeams", self.victim, self.pawn)[0]),
            fuse_seconds=float(actor.get_property("TimeBeforeExplode")), rpc_requested_by_fixture=self.name not in ("empty-fuse", "enemy-hit"),
            native_overlap_pawns_before=actual_pawns)
        self.statics.call_function("FinishSpawningActor", actor, transform, scale)
        self.row["native_trail_valid"] = valid(actor.get_property("NS_Trail"))
        require(self.row["native_trail_valid"], "native rendered trail missing")
        if self.name == "empty-rpc":
            # A newly returned Niagara component may not have activated yet.
            # Wait for real rendered activation before testing its completion.
            actor.get_property("ProjectileMovement").call_function("Deactivate")
            self.enter("visual_ready")
            return
        if self.name == "empty-fuse":
            # Isolate the existing world-time fuse; this lane makes no flight claim.
            actor.get_property("ProjectileMovement").call_function("Deactivate")
            self.row["trigger"] = "native-actor-timer"
            self.row["rpc_requested_by_fixture"] = False
        elif self.name == "enemy-hit":
            actor.get_property("Mesh").call_function("SetNotifyRigidBodyCollision", True)
            self.row["trigger"] = "native-blocking-sweep"
            actor.call_function("K2_SetActorLocation", NewLocation=ue.FVector(200000.+self.radius*.9, 200000., 2100.), bSweep=True, bTeleport=False)
        else:
            self.row["trigger"] = "original-reliable-rpc"
            actor.call_function("Detonate")
        self.enter("observe")

    def visual_ready(self):
        require(self.game_time()-self.spawn_time < 1.5, "native Niagara did not activate before original fuse deadline")
        trail = self.target.get_property("NS_Trail")
        active = bool(trail.call_function("IsActive"))
        self.report["pending_trail_active"] = active
        if not active or self.game_time()-self.spawn_time < .15:
            return
        require(not self.events, "native fuse fired before explicit RPC scenario")
        self.row["native_trail_active_before_rpc"] = active
        self.row["trigger"] = "original-reliable-rpc"
        self.target.call_function("Detonate")
        self.enter("observe")

    def observe(self):
        require(time.monotonic()-self.phase_started < 8., "native explosion body did not complete")
        if not self.events:
            return
        actor = self.target
        require(valid(actor) and not actor.call_function("IsActorBeingDestroyed"), "grenade destroyed before result capture")
        self.row.update(body_calls=len(self.events), body_elapsed=self.events[0]["elapsed"], stats=copy.deepcopy(self.events[0]["stats"]),
            hidden=bool(actor.get_property("Mesh").get_property("bHiddenInGame")),
            movement_active=bool(actor.get_property("ProjectileMovement").call_function("IsActive")),
            health_after=float(self.victim_health.call_function("GetHealth")), all_health_unchanged=self.healths() == self.health_before,
            rpc_flags_preserved=ue.describe_function(self.cls, "Detonate") == self.rpc_signature)
        after_health = self.healths()
        other_before = {name: state for name, state in self.health_before.items() if name != path(self.victim)}
        other_after = {name: state for name, state in after_health.items() if name != path(self.victim)}
        self.row["other_pawn_health_unchanged"] = other_before == other_after
        self.row["native_health_before"], self.row["native_health_after"] = self.health_before, after_health
        if not self.name.startswith("empty"):
            context = actor.get_property(policy.CONTEXT)
            hit = policy.library("AbilitySystemBlueprintLibrary").call_function("EffectContextGetHitResult", context)
            fields = policy.break_hit(hit)
            self.row["context_hit"] = dict(actor=path(fields["HitActor"]), distance=float(fields["Distance"]))
            self.row["expected_hit_actor"] = path(self.wall) if self.name == "occluded-rpc" else path(self.victim)
        actor.call_function("Detonate")
        self.row["repeat_body_calls"] = len(self.events)
        if self.name == "enemy-hit":
            self.row.update(native_hits=len(self.hits), hit_other_is_target=bool(self.hits and self.hits[0]["other"] == path(self.victim)),
                fuse_before_hit=bool(self.hits and self.hits[0]["fuse_before"]), fuse_after_hit=bool(self.hits and self.hits[0]["fuse_after"]))
        if self.name == "empty-rpc":
            trail = actor.get_property("NS_Trail")
            self.row["finished_component"] = path(trail)
            # Exercise the native delegate transport through Niagara itself;
            # this is controlled completion, not authored particle expiry.
            trail.call_function("Deactivate")
            self.row["controlled_native_niagara_completion"] = True
            self.enter("finish_wait")
            return
        self.complete_case()

    def finish_wait(self):
        require(time.monotonic()-self.phase_started < 8., "native Niagara completion/destroy delegate timeout")
        if not self.finish_events:
            return
        self.row["native_finish_callbacks"] = list(self.finish_events)
        require(not valid(self.target) or self.target.call_function("IsActorBeingDestroyed"), "native Niagara completion did not destroy grenade through its bound Actor event")
        self.complete_case(native_finished=True)

    def complete_case(self, native_finished=False):
        actor = self.target
        if not native_finished:
            actor.call_function("K2_DestroyActor")
        self.row["actor_destroyed"] = not valid(actor) or bool(actor.call_function("IsActorBeingDestroyed"))
        self.target = None
        if valid(self.victim) and not self.victim.call_function("IsActorBeingDestroyed"):
            _, location, rotation = self.poses[path(self.victim)]
            require(self.victim.call_function("K2_TeleportTo", location, rotation), "native per-trial target pose restore failed")
        self.poses.pop(path(self.victim), None)
        self.report["cases"].append(copy.deepcopy(self.row))
        ue.log("UEP_GRENADE_DETONATE_CASE_CAPTURED "+self.name+" "+self.profile)
        self.index += 1
        if self.index == len(PLAN):
            self.finish()
        else:
            self.enter("source")

    def cleanup(self):
        if self.cleaned:
            return
        self.target = None
        if hasattr(self, "original_view"):
            self.controller.call_function("SetViewTargetWithBlend", self.original_view, 0., 0, 0., False)
            self.report["view_target_restored"] = self.controller.call_function("GetViewTarget") == self.original_view
        for actor in self.actors:
            if valid(actor) and not actor.call_function("IsActorBeingDestroyed"):
                actor.call_function("K2_DestroyActor")
        for pawn, location, rotation in self.poses.values():
            if valid(pawn) and not pawn.call_function("IsActorBeingDestroyed"):
                require(pawn.call_function("K2_TeleportTo", location, rotation), "native surviving bot pose restore failed")
        if self.installed:
            for name, base in self.original_classes.items():
                ue.register_mixin_profile(self.cls, name, base)
            binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == self.cls]
            self.report["production_classes_restored"] = all(binding["profiles"][name]["python_class"] is base for name, base in self.original_classes.items())
        self.report["test_actors_destroyed"] = all(not valid(actor) or actor.call_function("IsActorBeingDestroyed") for actor in self.actors)
        self.cleaned = True

    def tick(self, seconds):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 240., "native explosion total timeout")
            if self.phase == "ready":
                self.ready()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.phase == "source": self.source()
                elif self.phase == "settle" and time.monotonic()-self.phase_started > .1: self.spawn()
                elif self.phase == "observe": self.observe()
                elif self.phase == "finish_wait": self.finish_wait()
                elif self.phase == "visual_ready": self.visual_ready()
            self.report["phase"] = self.phase
            self.write()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        self.report["pending_events"], self.report["pending_hits"] = copy.deepcopy(self.events), copy.deepcopy(self.hits)
        self.report["pending_case"] = copy.deepcopy(getattr(self, "row", None))
        try:
            self.cleanup()
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write()
        (ue.log_error if error else ue.log)("UEP_GRENADE_DETONATE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"
                validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_GRENADE_DETONATE_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPGrenadeDetonateResult=")), None)
if result:
    validation = Validation(result)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
