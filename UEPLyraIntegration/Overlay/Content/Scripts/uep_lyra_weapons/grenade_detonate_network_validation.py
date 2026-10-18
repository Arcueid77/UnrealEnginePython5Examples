"""One real server/two clients: native Actor replication, multicast and GAS.

Files only schedule observations. Actors and Health arrive through Unreal's
network stack. Test-owned projectile movement is deactivated on each peer to
isolate the original fuse/RPC; this is not a flight-physics acceptance lane.
"""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod, ESpawnActorScaleMethod, EObjectTypeQuery, ETraceTypeQuery, EDrawDebugTrace
from unreal_engine.structs import GameplayTag, GameplayEventData
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.auto_respawn_helpers_network_validation import token
from uep_lyra_abilities.jump_network_validation import Server as Playing, arg
from uep_lyra_abilities import network_identity as wire, melee_replica_readiness as readiness
from . import grenade_detonate_mixin as policy
from .grenade_detonate_network_contract import CLASS, PLAN, PEERS, FALSE, require, accept_command

GRANT_CLASS = "/ShooterCore/Input/Abilities/GA_Grenade.GA_Grenade_C"
CONFIG = ("bReplicates", "bReplicateMovement", "bNetLoadOnClient", "bAlwaysRelevant", "bOnlyRelevantToOwner", "NetCullDistanceSquared", "TimeBeforeExplode", "Radius")


def path(value): return value.get_path_name() if valid(value) else None
def destroyed(actor): return not valid(actor) or bool(actor.call_function("IsActorBeingDestroyed"))
def vector(value): return [float(value.x), float(value.y), float(value.z)]
def mode(world):
    bridge = policy.library("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld", world)
    return str(bridge.call_function("CaptureSnapshot").NetMode)
def report(peer, run):
    value = dict(schema_version=1, status="running", error=None, peer=peer, run_id=run, cases=[], observation_errors=[],
                 network_acceptance=True, held_stationary_by_native_component_deactivation=True)
    value.update({key: False for key in FALSE})
    return value


class Witness:
    def init_witness(self):
        self.cls, self.actor, self.armed = None, None, False
        self.events, self.begins, self.actors, self.original_classes = [], [], [], {}
        self.closed = False

    def healths(self):
        pawns, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraCharacter"))
        result = {}
        for pawn in pawns:
            health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if valid(health): result[path(pawn)] = dict(health=float(health.call_function("GetHealth")), death=int(health.call_function("GetDeathState")))
        return result

    def install(self):
        self.cls = ue.load_class(CLASS)
        ue.register_declared_mixin(self.cls)
        self.original_config = {name: self.cls.get_cdo().get_property(name) for name in CONFIG}
        self.original_selector = str(self.cls.get_cdo().get_property("PythonMixinProfile"))
        self.report["original_actor_profile_selector"] = self.original_selector
        self.report["original_actor_configuration"] = self.original_config
        self.rpc_signature = ue.describe_function(self.cls, "Detonate")
        require(self.original_config["bReplicates"] and self.original_config["bReplicateMovement"], "original Actor is not replicated")
        require(self.original_config["TimeBeforeExplode"] == 2., "original fuse changed")
        binding, = [row for row in ue.get_registered_mixins() if row["target_class"] == self.cls]
        self.original_classes = {name: value["python_class"] for name, value in binding["profiles"].items()}
        owner = self
        for name, base in self.original_classes.items():
            def around_begin(handler, profile):
                def invoke(actor):
                    if not owner.armed:
                        return handler(actor)
                    try:
                        require(profile == owner.command["profile"] and str(ue.get_mixin_profile(actor)) == profile,
                                "native spawn did not copy the preselected declared profile")
                        handler(actor)
                        actor.get_property("ProjectileMovement").call_function("Deactivate")
                        owner.actor = actor
                        owner.actors.append(actor)
                        owner.begins.append(dict(profile=profile, actor=path(actor), role=int(actor.call_function("GetLocalRole"))))
                    except Exception:
                        owner.report["observation_errors"].append(traceback.format_exc())
                        raise
                return invoke
            def around_body(handler, profile):
                def invoke(actor):
                    watched = owner.armed and actor == owner.actor
                    counts = policy.evidence(actor)
                    if watched:
                        row = dict(profile=profile, **{"class": path(actor.get_class())}, identity=wire.read(actor),
                            authority=bool(actor.call_function("HasAuthority")), role=int(actor.call_function("GetLocalRole")),
                            age_at_body=float(wire.read(actor)["actor_age_seconds"]), trail_before=valid(actor.get_property("NS_Trail")),
                            held_stationary_by_native_fixture=not actor.get_property("ProjectileMovement").call_function("IsActive"),
                            rpc_flags_preserved=ue.describe_function(owner.cls, "Detonate") == owner.rpc_signature)
                    handler(actor)
                    if watched:
                        row.update(stats=copy.deepcopy(counts), actor_destroyed_after_body=destroyed(actor))
                        if not row["actor_destroyed_after_body"]:
                            row.update(hidden_after=bool(actor.get_property("Mesh").get_property("bHiddenInGame")),
                                movement_active_after=bool(actor.get_property("ProjectileMovement").call_function("IsActive")))
                        owner.events.append(row)
                invoke.override = policy.BODY
                return invoke
            methods = {key: value for key, value in vars(base).items() if not key.startswith("__") and callable(value)}
            methods["ReceiveBeginPlay"] = around_begin(base.ReceiveBeginPlay, name)
            methods["DetonateBody"] = around_body(base.DetonateBody, name)
            ue.register_mixin_profile(self.cls, name, type("ObservedNetworkGrenade"+name, (), methods))

    def arm(self):
        self.events, self.begins, self.actor = [], [], None
        # Existing validation pattern: choose only the declared Actor selector
        # before native spawn. Never change the registry inside a callback.
        # Restore this transient CDO value after the test; never save the asset.
        self.cls.get_cdo().set_property("PythonMixinProfile", self.command["profile"])
        self.armed = True
        self.health_before = self.healths()

    def resolve(self, player_id, identity):
        pawns, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraCharacter"))
        for pawn in pawns:
            state = pawn.get_property("PlayerState")
            if not valid(state) or int(state.PlayerId) != player_id or not wire.same(wire.read(pawn), identity): continue
            health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if not valid(health): continue
            binding = readiness.snapshot(pawn, health)
            self.report.setdefault("pending_bindings", {})[str(player_id)] = binding
            if binding["destroying"] or binding["health"] != 100. or binding["health_set"] is None: continue
            if binding["player_state_pawn"] != binding["actor"] or binding["actor_asc"] is None or binding["health_asc"] is None: continue
            if binding["actor_asc"]["avatar"] != binding["actor"] or binding["health_asc"]["object"] != binding["actor_asc"]["object"]: continue
            return pawn, health
        return None

    def cleanup(self):
        if self.closed: return
        self.armed = False
        self.report["remaining_projectiles"] = sum(not destroyed(actor) for actor in self.actors)
        if self.original_classes:
            self.cls.get_cdo().set_property("PythonMixinProfile", self.original_selector)
            self.report["actor_selector_restored"] = str(self.cls.get_cdo().get_property("PythonMixinProfile")) == self.original_selector
            for name, base in self.original_classes.items(): ue.register_mixin_profile(self.cls, name, base)
            binding, = [row for row in ue.get_registered_mixins() if row["target_class"] == self.cls]
            self.report["observers_restored"] = all(binding["profiles"][name]["python_class"] is base for name, base in self.original_classes.items())
            self.report["actor_configuration_preserved"] = {name: self.cls.get_cdo().get_property(name) for name in CONFIG} == self.original_config
        self.closed = True

    def other_health_unchanged(self):
        before = {name: row for name, row in self.health_before.items() if name != path(self.victim)}
        after = {name: row for name, row in self.healths().items() if name != path(self.victim)}
        return before == after


class Client(Witness, Ready):
    def __init__(self, result, peer, run):
        Ready.__init__(self, result)
        self.peer, self.run, self.root = peer, run, self.path.parent
        self.report = report(peer, run)
        self.require_auto_active, self.require_local_playing_phase = False, False
        self.position, self.completed, self.processed, self.command = -1, -1, None, {}
        self.init_witness()

    def ready(self):
        if token(self.root, "playing-ready.json", self.run) is not None: Ready.ready(self)

    def begin(self):
        self.report.update(native_mode=mode(self.world), player_id=int(self.controller.PlayerState.PlayerId))
        require(self.report["native_mode"] == "Client", "real client world required")
        self.install()
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        self.enter("network")

    def ack(self, stage, row):
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-"+stage+".json"), dict(run_id=self.run, position=self.position, row=row))
        self.processed = self.position, stage

    def prepare(self):
        source = self.resolve(self.command["source_player_id"], self.command["source_identity"])
        target = self.resolve(self.command["victim_player_id"], self.command["victim_identity"])
        if source is None or target is None: return
        self.source, self.source_health = source
        self.victim, self.victim_health = target
        self.arm()
        self.ack("prepare", dict(source_identity=wire.read(self.source), victim_identity=wire.read(self.victim), healthy_bound=True))

    def spawned(self):
        if not valid(self.actor) or not wire.same(wire.read(self.actor), self.command["actor_identity"]): return
        require(len(self.begins) == 1 and not self.events, "unexpected native replicated BeginPlay/early explosion")
        require(self.actor.get_property("Instigator") == self.source, "native replicated Instigator differs")
        self.identity = wire.read(self.actor)
        self.ack("spawn", dict(identity=self.identity, instigator_identity=wire.read(self.actor.get_property("Instigator")), native_begin_count=len(self.begins)))

    def observe(self):
        if not self.events or not destroyed(self.actor): return
        require(len(self.events) == 1, "duplicate native client explosion body")
        health = float(self.victim_health.call_function("GetHealth"))
        if self.command["name"] == "enemy-rpc" and health == 100.: return
        require(health > 0 and self.other_health_unchanged(), "client target died or unrelated Pawn Health changed")
        if health != getattr(self, "last_health", None): self.last_health, self.quiet_ticks = health, 0
        self.quiet_ticks += 1
        if self.quiet_ticks < 8: return
        row = dict(position=self.position, owner=self.command["owner"], name=self.command["name"], profile=self.command["profile"],
            identity=self.identity, source_identity=wire.read(self.source), victim_identity=wire.read(self.victim),
            native_body_count=len(self.events), body=copy.deepcopy(self.events[0]), replicated_actor_destroyed=destroyed(self.actor),
            health_after=health, quiet_ticks=self.quiet_ticks, other_health_unchanged=True, server_values_written_to_gameplay=False)
        self.report["cases"].append(row)
        self.armed, self.completed = False, self.position
        self.ack("done", row)
        self.enter("network")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(not self.report["observation_errors"], "native observer failed: "+str(self.report["observation_errors"]))
            require(time.monotonic()-self.started < 500., "native client explosion total timeout")
            if self.phase == "ready": self.ready()
            elif self.phase == "release":
                if token(self.root, "release.json", self.run) is not None: self.finish()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.phase == "observe": self.observe()
                else:
                    command = token(self.root, "explosion-command.json", self.run)
                    if command is not None and accept_command(command, self.processed, self.completed):
                        self.command, self.position = command, command["position"]
                        stage = command["stage"]
                        if stage == "prepare": self.prepare()
                        elif stage == "spawn": self.spawned()
                        elif stage == "observe":
                            self.last_health, self.quiet_ticks, self.processed = None, 0, (self.position, stage)
                            self.enter("observe")
                        else:
                            self.cleanup()
                            self.ack("complete", dict(cleanup=True))
                            self.enter("release")
            self.report.update(phase=self.phase, pending_begins=self.begins, pending_events=self.events)
            self.write()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write()
        ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_GRENADE_DETONATE_NETWORK_SHUTDOWN_"+self.report["status"].upper())


class Server(Witness, Playing):
    def __init__(self, result, run):
        Playing.__init__(self, result, run)
        self.report = report("server", run)
        self.report["server_waited_for_client_process_exit"] = False
        self.ability_class = GRANT_CLASS
        self.init_witness()
        self.stage, self.command, self.released, self.reset_sent = None, {}, False, set()

    def publish(self, stage):
        self.stage, self.stage_started = stage, time.monotonic()
        atomic_write(self.root/"explosion-command.json", dict(run_id=self.run, position=self.position, stage=stage, **self.command))

    def acks(self, stage):
        rows = {peer: token(self.root, peer+"-"+str(self.position)+"-"+stage+".json", self.run, self.position) for peer in PEERS}
        return rows if all(rows.values()) else None

    def prepare(self):
        owner, name, profile = PLAN[self.position]
        for value in self.owners.values():
            pawn = value["controller"].get_controlled_pawn()
            if not valid(pawn): return
            health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            asc = ability_system(pawn)
            if not valid(health) or not valid(asc) or health.call_function("IsDeadOrDying"): return
            if health.call_function("GetHealth") != 100.:
                if path(pawn) not in self.reset_sent:
                    tag, state = GameplayTag(TagName="GameplayEvent.RequestReset"), value["controller"].PlayerState
                    policy.library("AbilitySystemBlueprintLibrary").call_function("SendGameplayEventToActor", state, tag, GameplayEventData(EventTag=tag, Instigator=state, Target=state))
                    self.reset_sent.add(path(pawn))
                return
            if asc.call_function("GetGameplayTagCount", GameplayTag(TagName="Gameplay.DamageImmunity")): return
            if asc.get_property("AvatarActor") != pawn or value["controller"].PlayerState.call_function("GetPawn") != pawn: return
            value.update(pawn=pawn, health=health)
        source, target = self.owners[owner], self.owners[PEERS[1] if owner == PEERS[0] else PEERS[0]]
        self.source, self.victim, self.victim_health = source["pawn"], target["pawn"], target["health"]
        self.command = dict(owner=owner, name=name, profile=profile, source_player_id=source["player_id"], victim_player_id=target["player_id"],
            source_identity=wire.read(self.source), victim_identity=wire.read(self.victim))
        self.teams = policy.library("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem", self.world, ue.find_class("LyraTeamSubsystem"))
        self.comparison = int(self.teams.call_function("CompareTeams", self.source, self.victim)[0])
        require(self.comparison == 1, "two native owners must be on different original teams")
        self.arm()
        self.publish("prepare")

    def overlap(self, point):
        fields = policy.native_outputs("KismetSystemLibrary", "SphereOverlapActors", policy.library("KismetSystemLibrary").call_function(
            "SphereOverlapActors", WorldContextObject=self.world, SpherePos=point, SphereRadius=self.original_config["Radius"],
            ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery3], ActorClassFilter=ue.find_class("Pawn"), ActorsToIgnore=[]))
        return sorted(path(actor) for actor in fields["OutActors"])

    def choose_position(self):
        if self.command["name"] != "enemy-rpc":
            source = self.source.get_actor_location()
            point = ue.FVector(source.x, source.y, source.z+1200.)
            require(self.overlap(point) == [], "empty native explosion overlaps another Pawn")
            return point
        origin, radius = self.victim.get_actor_location(), self.original_config["Radius"]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (.707, .707), (-.707, .707), (.707, -.707), (-.707, -.707)):
            point = ue.FVector(origin.x+radius*.7*dx, origin.y+radius*.7*dy, origin.z)
            if self.overlap(point) != [path(self.victim)]: continue
            fields = policy.native_outputs("KismetSystemLibrary", "LineTraceSingle", policy.library("KismetSystemLibrary").call_function(
                "LineTraceSingle", WorldContextObject=self.world, Start=point, End=origin, TraceChannel=ETraceTypeQuery.TraceTypeQuery5,
                bTraceComplex=True, ActorsToIgnore=[], DrawDebugType=getattr(EDrawDebugTrace, "None"), bIgnoreSelf=True,
                TraceColor=ue.FLinearColor(1., 0., 0., 1.), TraceHitColor=ue.FLinearColor(0., 1., 0., 1.), DrawTime=0.))
            hit = policy.break_hit(fields["OutHit"])
            if fields["ReturnValue"] and hit["HitActor"] == self.victim and hit["Distance"] > radius*.45:
                return point
        raise RuntimeError("no unobstructed isolated native enemy explosion position")

    def spawn(self):
        point = self.choose_position()
        self.target_overlap = self.overlap(point)
        self.spawn_point = vector(point)
        transform = ue.FTransform(point, ue.FRotator(), ue.FVector(1., 1., 1.))
        scale = ESpawnActorScaleMethod.OverrideRootScale
        actor = self.statics.call_function("BeginDeferredActorSpawnFromClass", self.world, self.cls, transform, ESpawnActorCollisionHandlingMethod.AlwaysSpawn, None, scale)
        actor.set_property("Instigator", self.source)
        ue.set_mixin_profile(actor, self.command["profile"])
        self.actor, self.spawn_time = actor, time.monotonic()
        self.statics.call_function("FinishSpawningActor", actor, transform, scale)
        self.stage, self.stage_started = "identity", time.monotonic()

    def step(self):
        require(time.monotonic()-self.stage_started < 45., "native explosion stage timeout: "+str(self.stage))
        if self.stage == "start": self.prepare()
        elif self.stage == "prepare":
            if self.acks("prepare"): self.spawn()
        elif self.stage == "identity":
            require(not destroyed(self.actor), "projectile destroyed before native wire registration")
            identity = wire.read(self.actor)
            if wire.key(identity) is not None:
                self.identity = identity
                self.command["actor_identity"] = identity
                self.publish("spawn")
        elif self.stage == "spawn":
            require(not self.events, "original fuse expired before both real replicas acknowledged spawn")
            if not self.acks("spawn"): return
            self.health_before = self.healths()
            if self.command["name"] != "empty-fuse": self.actor.call_function("Detonate")
            self.publish("observe")
        elif self.stage == "observe":
            if not self.events: return
            require(len(self.events) == 1 and destroyed(self.actor), "headless body must run once and destroy native Actor")
            done = self.acks("done")
            if done is None: return
            row = dict(position=self.position, owner=self.command["owner"], name=self.command["name"], profile=self.command["profile"],
                identity=self.identity, source_identity=wire.read(self.source), victim_identity=wire.read(self.victim), victim_path=path(self.victim),
                native_body_count=len(self.events), body=copy.deepcopy(self.events[0]), destroyed=destroyed(self.actor),
                native_target_overlap=self.target_overlap, spawn_location=self.spawn_point, team_comparison=self.comparison,
                health_before=self.health_before[path(self.victim)]["health"], health_after=float(self.victim_health.call_function("GetHealth")),
                native_fuse_trigger=self.command["name"] == "empty-fuse", other_health_unchanged=self.other_health_unchanged())
            require(row["other_health_unchanged"], "server explosion changed another Pawn")
            self.report["cases"].append(row)
            ue.log("UEP_GRENADE_DETONATE_NETWORK_CASE_PASSED "+row["owner"]+" "+row["name"]+" "+row["profile"])
            self.position += 1
            self.armed = False
            if self.position == len(PLAN): self.publish("complete")
            else: self.stage, self.stage_started = "start", time.monotonic()
        elif self.stage == "complete":
            if self.acks("complete") is None: return
            if not self.released:
                self.cleanup()
                atomic_write(self.root/"release.json", dict(run_id=self.run))
                self.released = True
            exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
            if all(value is not None and value["exit_code"] == 0 for value in exits):
                self.report["server_waited_for_client_process_exit"] = True
                self.finish()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(not self.report["observation_errors"], "native observer failed: "+str(self.report["observation_errors"]))
            require(time.monotonic()-self.started < 500., "native authority explosion total timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif self.cls is None:
                self.report["native_mode"] = mode(self.world)
                require(self.report["native_mode"] == "DedicatedServer", "real dedicated no-render authority required")
                self.install()
                self.stage, self.stage_started = "start", time.monotonic()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                self.step()
            self.report.update(pending_stage=self.stage, pending_events=self.events, pending_begins=self.begins)
            atomic_write(self.path, self.report)
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_GRENADE_DETONATE_NETWORK_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPGrenadeDetonateNetworkResult=")), None)
if result:
    peer, run = arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
