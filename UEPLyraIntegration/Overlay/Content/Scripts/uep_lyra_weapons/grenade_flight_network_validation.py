"""Actual owning-client GAS request and unmodified native grenade flight."""
import atexit
import copy
import json
import math
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayEventData
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready, instances
from uep_lyra_abilities.auto_respawn_helpers_network_validation import token
from uep_lyra_abilities.jump_network_validation import Server as Playing, arg
from uep_lyra_abilities.dash_local_direction_validation import restore_control
from uep_lyra_abilities.grenade_activation_validation import counts as activation_counts
from uep_lyra_abilities import network_identity as wire
from . import grenade_detonate_mixin as policy
from .grenade_detonate_network_validation import Witness as ActorWitness, GRANT_CLASS, path, destroyed, vector, mode
from .grenade_flight_network_contract import CLASS, PLAN, PEERS, FALSE, require, accept_command, reset_peers


def rotation(value): return dict(roll=float(value.roll), pitch=float(value.pitch), yaw=float(value.yaw))
def angle_distance(left, right): return abs((float(left)-float(right)+180.) % 360.-180.)
def make_report(peer, run):
    value = dict(schema_version=1, status="running", error=None, peer=peer, run_id=run, cases=[], observation_errors=[],
                 network_acceptance=True, request_entry="owning ASC.TryActivateAbilityByClass", native_control_rotation_used=True)
    value.update({name: False for name in FALSE})
    return value


class Witness(ActorWitness):
    def init_witness(self):
        ActorWitness.init_witness(self)
        self.ability_classes, self.saved_abilities, self.players = {}, [], {}
        self.activation_events, self.samples, self.hits = [], [], []
        self.in_hit, self.activation_requests, self.identity = False, 0, None

    def install(self):
        ActorWitness.install(self)
        # Reuse the read-only body observation, replacing only the stationary
        # fixture's BeginPlay observer. No native movement/timer/pose writes.
        binding, = [row for row in ue.get_registered_mixins() if row["target_class"] == self.cls]
        observed = {name: row["python_class"] for name, row in binding["profiles"].items()}
        owner = self
        for name, base in self.original_classes.items():
            def around_begin(handler, profile):
                def invoke(actor):
                    if not owner.armed: return handler(actor)
                    try:
                        require(profile == owner.command["profile"] and str(ue.get_mixin_profile(actor)) == profile, "natural Actor profile differs")
                        handler(actor)
                        movement = actor.get_property("ProjectileMovement")
                        owner.actor = actor
                        owner.actors.append(actor)
                        owner.begins.append(dict(profile=profile, actor=path(actor), role=int(actor.call_function("GetLocalRole")),
                            location=vector(actor.get_actor_location()), movement_active=bool(movement.call_function("IsActive")),
                            initial_speed=float(movement.get_property("InitialSpeed")), gravity_scale=float(movement.get_property("ProjectileGravityScale"))))
                        owner.sample()
                    except Exception:
                        owner.report["observation_errors"].append(traceback.format_exc()); raise
                return invoke
            def around_body(handler):
                def invoke(actor):
                    watched = owner.armed and actor == owner.actor
                    if watched:
                        owner.sample()
                        system, timer = policy.library("KismetSystemLibrary"), actor.get_property("Timer")
                        authority = bool(actor.call_function("HasAuthority"))
                        remaining = float(system.call_function("K2_GetTimerRemainingTimeHandle", owner.world, timer))
                        extra = dict(fixture_held_stationary=False, location_at_body=vector(actor.get_actor_location()),
                            instigator_identity=wire.read(actor.get_property("Instigator")),
                            fuse_exists_before=bool(system.call_function("K2_TimerExistsHandle", owner.world, timer)),
                            fuse_remaining_before=remaining,
                            trigger="native-enemy-hit" if owner.in_hit else "native-fuse" if authority else "client-pending-fuse" if remaining > 0. else "client-fuse-due",
                            hit_comparison=owner.hits[-1]["comparison"] if owner.in_hit else None)
                        identity = wire.read(actor)
                        ue.log("UEP_GRENADE_FLIGHT_BODY "+json.dumps(dict(peer=owner.report["peer"], position=owner.position,
                            actor=identity["object_path"], wire_id=identity["wire_id"], fuse_remaining=remaining, trigger=extra["trigger"]), sort_keys=True))
                    handler(actor)
                    if watched:
                        event = owner.events[-1]
                        event["movement_active_before_body"] = not event.pop("held_stationary_by_native_fixture")
                        event.update(extra)
                invoke.override = policy.BODY
                return invoke
            def around_hit(handler):
                def invoke(actor, MyComp, Other, OtherComp, bSelfMoved, HitLocation, HitNormal, NormalImpulse, Hit):
                    watched = owner.armed and actor == owner.actor
                    if watched:
                        teams = policy.library("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem", owner.world, ue.find_class("LyraTeamSubsystem"))
                        comparison = teams.call_function("CompareTeams", Other, actor.get_property("Instigator"))
                        owner.hits.append(dict(other=path(Other), comparison=int(comparison[0]), location=vector(HitLocation)))
                        require(len(owner.hits) <= 128, "bounded native collision history exhausted")
                        owner.in_hit = True
                    try: return handler(actor, MyComp, Other, OtherComp, bSelfMoved, HitLocation, HitNormal, NormalImpulse, Hit)
                    finally:
                        if watched: owner.in_hit = False
                return invoke
            methods = {key: value for key, value in vars(base).items() if not key.startswith("__") and callable(value)}
            methods.update(ReceiveBeginPlay=around_begin(base.ReceiveBeginPlay, name),
                DetonateBody=around_body(observed[name].DetonateBody), ReceiveHit=around_hit(base.ReceiveHit))
            ue.register_mixin_profile(self.cls, name, type("ObservedNaturalGrenade"+name, (), methods))
        self.ability_cls = ue.load_class(GRANT_CLASS)
        ue.register_declared_mixin(self.ability_cls)
        binding, = [row for row in ue.get_registered_mixins() if row["target_class"] == self.ability_cls]
        self.ability_classes = {name: row["python_class"] for name, row in binding["profiles"].items()}
        for name, base in self.ability_classes.items():
            def around_activation(handler, profile):
                def invoke(ability):
                    watched = owner.armed
                    if watched:
                        counts, births = activation_counts(ability), len(owner.begins)
                        pawn = ability.call_function("GetLyraCharacterFromActorInfo")
                        row = dict(profile=profile, authority=bool(ability.call_function("K2_HasAuthority")),
                            mode=int(ability.get_property("CurrentActivationInfo").ActivationMode),
                            source_identity=wire.read(pawn), source_role=int(pawn.call_function("GetLocalRole")))
                    handler(ability)
                    if watched:
                        after = activation_counts(ability)
                        row.update(native_begin_delta=len(owner.begins)-births, active_after=bool(ability.get_property("bIsActive")),
                            stats={key: value-counts[key] for key, value in after.items()}, direction=rotation(ability.get_property("Direction")),
                            location=vector(ability.get_property("Location")))
                        owner.activation_events.append(row)
                return invoke
            methods = {key: value for key, value in vars(base).items() if not key.startswith("__") and callable(value)}
            methods["K2_ActivateAbility"] = around_activation(base.K2_ActivateAbility, name)
            ue.register_mixin_profile(self.ability_cls, name, type("ObservedNaturalThrow"+name, (), methods))

    def select_ability(self, ability, profile):
        if not any(item[0] == ability for item in self.saved_abilities): self.saved_abilities.append((ability, str(ue.get_mixin_profile(ability))))
        ue.set_mixin_profile(ability, profile)

    def arm(self):
        ActorWitness.arm(self)
        self.activation_events, self.samples, self.hits = [], [], []
        self.identity, self.activation_requests, self.native_request_accepted = None, 0, False
        self.player_health_cache = {}
        self.capture_health()

    def sample(self):
        if not self.armed or self.actor is None or destroyed(self.actor): return
        movement, point = self.actor.get_property("ProjectileMovement"), self.actor.get_actor_location()
        row = dict(time=float(self.statics.call_function("GetTimeSeconds", self.world)), location=vector(point),
                   velocity=vector(movement.get_property("Velocity")), active=bool(movement.call_function("IsActive")))
        if not self.samples or row["time"] != self.samples[-1]["time"]:
            require(len(self.samples) < 512, "bounded native trajectory exhausted")
            self.samples.append(row)
        identity = wire.read(self.actor)
        if wire.key(identity) is not None: self.identity = identity

    def capture_health(self):
        for peer, value in self.players.items():
            if valid(value["health"]):
                self.player_health_cache[peer] = dict(identity=value["identity"], health=float(value["health"].call_function("GetHealth")),
                    death=int(value["health"].call_function("GetDeathState")))
        return copy.deepcopy(self.player_health_cache)

    def trajectory(self):
        require(self.samples, "native trajectory missing")
        first = self.samples[0]["location"]
        return dict(samples=len(self.samples), distinct_positions=len({tuple(row["location"]) for row in self.samples}),
            active_movement_samples=sum(row["active"] for row in self.samples),
            max_displacement=max(math.dist(first, row["location"]) for row in self.samples),
            points=copy.deepcopy(self.samples))

    def case_row(self):
        require(len(self.events) == 1 and len(self.begins) == 1, "natural native Actor birth/body count differs")
        return dict(position=self.position, owner=self.command["owner"], profile=self.command["profile"], identity=self.events[0]["identity"],
            source_identity=self.source_identity, native_begin_count=len(self.begins), native_body_count=len(self.events),
            begin=copy.deepcopy(self.begins[0]), body=copy.deepcopy(self.events[0]), trajectory=self.trajectory(),
            collisions=copy.deepcopy(self.hits), destroyed=destroyed(self.actor), quiet_ticks=self.quiet_ticks,
            activations=copy.deepcopy(self.activation_events), activation_requests=self.activation_requests,
            native_request_accepted=self.native_request_accepted, player_health_after=self.capture_health())

    def cleanup(self):
        if self.closed: return
        profiles = True
        for ability, profile in self.saved_abilities:
            require(valid(ability), "persistent original Grenade ability disappeared")
            ue.set_mixin_profile(ability, profile)
            profiles &= str(ue.get_mixin_profile(ability)) == profile
        self.report["ability_profiles_restored"] = profiles
        if self.ability_classes:
            for name, base in self.ability_classes.items(): ue.register_mixin_profile(self.ability_cls, name, base)
            binding, = [row for row in ue.get_registered_mixins() if row["target_class"] == self.ability_cls]
            self.report["ability_observers_restored"] = all(binding["profiles"][name]["python_class"] is base for name, base in self.ability_classes.items())
        ActorWitness.cleanup(self)


class Client(Witness, Ready):
    def __init__(self, result, peer, run):
        Ready.__init__(self, result)
        self.peer, self.run, self.root = peer, run, self.path.parent
        self.report = make_report(peer, run)
        self.require_auto_active, self.require_local_playing_phase = False, False
        self.position, self.completed, self.processed, self.command = -1, -1, None, {}
        self.preparing, self.original_control = None, None
        self.init_witness()

    def ready(self):
        if token(self.root, "playing-ready.json", self.run) is not None: Ready.ready(self)

    def begin(self):
        self.report.update(native_mode=mode(self.world), player_id=int(self.controller.PlayerState.PlayerId))
        require(self.report["native_mode"] == "Client", "real native owning client required")
        self.original_control = self.controller.call_function("GetControlRotation")
        self.install()
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        self.enter("network")

    def ack(self, stage, row):
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-"+stage+".json"), dict(run_id=self.run, position=self.position, row=row))
        self.processed = self.position, stage

    def prepare(self):
        if self.preparing != self.position:
            players = {}
            for peer, item in self.command["players"].items():
                found = self.resolve(item["player_id"], item["identity"])
                if found is None: return
                pawn, health = found
                players[peer] = dict(pawn=pawn, health=health, identity=wire.read(pawn))
            if not Ready.attach(self, self.world, self.controller): return
            self.players, self.source = players, players[self.command["owner"]]["pawn"]
            self.source_identity = wire.read(self.source)
            self.own = self.command["owner"] == self.peer
            if self.own:
                values = instances(self.asc, self.ability_cls)
                require(len(values) == 1, "actual granted owning Grenade instance required")
                self.grenade = values[0]
                if self.grenade.call_function("GetCooldownTimeRemaining") > 0: return
                require(self.grenade.call_function("K2_CheckAbilityCost"), "native Grenade cost not ready after normal reset")
                self.select_ability(self.grenade, self.command["profile"])
                current = self.controller.call_function("GetControlRotation")
                self.controller.call_function("SetControlRotation", ue.FRotator(float(current.roll), 65., float(current.yaw)))
            self.arm()
            self.preparing, self.aim_started = self.position, time.monotonic()
        if self.own and time.monotonic()-self.aim_started < .25: return
        self.ack("prepare", dict(source_identity=self.source_identity,
            control=rotation(self.controller.call_function("GetControlRotation")) if self.own else None,
            healthy_bound=True, native_cost_ready=bool(self.grenade.call_function("K2_CheckAbilityCost")) if self.own else None))

    def activate(self):
        if self.own:
            self.activation_requests += 1
            self.native_request_accepted = bool(self.asc.call_function("TryActivateAbilityByClass", self.ability_cls, False))
            require(self.native_request_accepted and len(self.activation_events) == 1, "actual predicted owning GAS request failed")
        self.quiet_ticks, self.last_health = 0, None
        self.processed = self.position, "activate"
        self.enter("observe")

    def observe(self):
        require(time.monotonic()-self.phase_started < 25., "native flight/multicast/destruction timeout")
        if not self.events or self.actor is None or not destroyed(self.actor): return
        require(len(self.events) == 1, "duplicate native natural explosion")
        health = self.capture_health()
        if health != self.last_health: self.last_health, self.quiet_ticks = health, 0
        self.quiet_ticks += 1
        if self.quiet_ticks < 8: return
        if self.own and valid(self.source) and self.source.call_function("GetCurrentMontage") == self.grenade.get_property("GrenadeThrowMontage"): return
        row = self.case_row()
        self.report["cases"].append(row)
        self.completed, self.armed = self.position, False
        self.ack("done", row)
        self.enter("network")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(not self.report["observation_errors"], "native natural-throw observer failed: "+str(self.report["observation_errors"]))
            require(time.monotonic()-self.started < 500., "native natural-throw client total timeout")
            if self.phase == "ready": self.ready()
            elif self.phase == "release":
                if token(self.root, "release.json", self.run) is not None: self.finish()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                self.sample()
                if self.armed: self.capture_health()
                if self.phase == "observe": self.observe()
                else:
                    command = token(self.root, "flight-command.json", self.run)
                    if command is not None and accept_command(command, self.processed, self.completed):
                        self.command, self.position = command, command["position"]
                        if command["stage"] == "prepare": self.prepare()
                        elif command["stage"] == "activate": self.activate()
                        else:
                            self.cleanup(); self.ack("complete", dict(cleanup=True)); self.enter("release")
            self.report.update(phase=self.phase, pending_begins=self.begins, pending_events=self.events,
                pending_activations=self.activation_events, pending_samples=len(self.samples))
            self.write()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def cleanup(self):
        if self.closed: return
        if self.original_control is not None:
            self.report["control_rotation_restored"] = restore_control(self.controller, self.original_control)["control_rotation"]
        Witness.cleanup(self)

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write(); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_GRENADE_FLIGHT_NETWORK_SHUTDOWN_"+self.report["status"].upper())


class Server(Witness, Playing):
    def __init__(self, result, run):
        Playing.__init__(self, result, run)
        self.report = make_report("server", run)
        self.report["server_waited_for_client_process_exit"] = False
        self.ability_class = GRANT_CLASS
        self.init_witness()
        self.stage, self.command, self.released = None, {}, False

    def publish(self, stage):
        self.stage, self.stage_started = stage, time.monotonic()
        atomic_write(self.root/"flight-command.json", dict(run_id=self.run, position=self.position, stage=stage, **self.command))

    def acks(self, stage):
        rows = {peer: token(self.root, peer+"-"+str(self.position)+"-"+stage+".json", self.run, self.position) for peer in PEERS}
        return rows if all(rows.values()) else None

    def start(self):
        owner, profile = PLAN[self.position]
        selected = self.owners[owner]
        if selected["ability"].call_function("GetCooldownTimeRemaining") > 0: return
        health_values = {}
        for peer, value in self.owners.items():
            pawn = value["controller"].get_controlled_pawn()
            if not valid(pawn): return
            health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if not valid(health) or health.call_function("IsDeadOrDying"): return
            health_values[peer] = float(health.call_function("GetHealth"))
        self.command = dict(owner=owner, profile=profile)
        self.source_controller = selected["controller"]
        self.reset_pawns = {peer: path(self.owners[peer]["controller"].get_controlled_pawn()) for peer in reset_peers(owner, health_values)}
        self.report["pending_reset_preparation"] = dict(owner=owner, native_health=health_values, reset_pawns=self.reset_pawns)
        self.armed = False
        for peer in self.reset_pawns:
            state, tag = self.owners[peer]["controller"].PlayerState, GameplayTag(TagName="GameplayEvent.RequestReset")
            policy.library("AbilitySystemBlueprintLibrary").call_function("SendGameplayEventToActor", state, tag, GameplayEventData(EventTag=tag, Instigator=state, Target=state))
        self.stage, self.stage_started = "respawn", time.monotonic()

    def respawn(self):
        players = {}
        for peer, value in self.owners.items():
            pawn = value["controller"].get_controlled_pawn()
            if not valid(pawn) or (peer in self.reset_pawns and path(pawn) == self.reset_pawns[peer]): return
            health, asc = pawn.get_component_by_type(ue.find_class("LyraHealthComponent")), ability_system(pawn)
            self.report.setdefault("pending_respawn_readiness", {})[peer] = dict(pawn=path(pawn), health=float(health.call_function("GetHealth")) if valid(health) else None,
                asc_avatar=path(asc.get_property("AvatarActor")) if valid(asc) else None, player_state_pawn=path(value["controller"].PlayerState.call_function("GetPawn")))
            if not valid(health) or not valid(asc) or health.call_function("GetHealth") != 100.: return
            if asc.get_property("AvatarActor") != pawn or value["controller"].PlayerState.call_function("GetPawn") != pawn: return
            if asc.call_function("GetGameplayTagCount", GameplayTag(TagName="Gameplay.DamageImmunity")): return
            identity = wire.read(pawn)
            if wire.key(identity) is None: return
            players[peer] = dict(pawn=pawn, health=health, asc=asc, identity=identity)
            value["pawn"] = pawn
        selected = self.owners[self.command["owner"]]
        self.players, self.source = players, selected["pawn"]
        self.source_identity = wire.read(self.source)
        require(instances(players[self.command["owner"]]["asc"], self.ability_cls) == [selected["ability"]], "normal reset replaced persistent granted Grenade instance")
        self.select_ability(selected["ability"], self.command["profile"])
        self.command["players"] = {peer: dict(player_id=self.owners[peer]["player_id"], identity=value["identity"]) for peer, value in players.items()}
        self.arm()
        self.publish("prepare")

    def step(self):
        require(time.monotonic()-self.stage_started < 60., "native natural-throw stage timeout: "+str(self.stage))
        if self.stage == "start": self.start()
        elif self.stage == "respawn": self.respawn()
        elif self.stage == "prepare":
            ready = self.acks("prepare")
            if ready is None: return
            expected = ready[self.command["owner"]]["row"]["control"]
            actual = rotation(self.source_controller.call_function("GetControlRotation"))
            self.report["pending_aim_sync"] = dict(owner=expected, authority=actual)
            if any(angle_distance(actual[name], expected[name]) > 1. for name in ("pitch", "yaw")): return
            self.native_aim_sync = True
            self.quiet_ticks = 0
            self.publish("activate")
        elif self.stage == "activate":
            if not self.events or self.actor is None or not destroyed(self.actor): return
            require(len(self.activation_events) == len(self.events) == len(self.begins) == 1, "natural authority GAS/Actor chain duplicated or absent")
            self.quiet_ticks += 1
            done = self.acks("done")
            if done is None or self.quiet_ticks < 8: return
            row = self.case_row()
            row["native_aim_sync"] = self.native_aim_sync
            row["native_reset_peers"] = sorted(self.reset_pawns)
            self.report["cases"].append(row)
            ue.log("UEP_GRENADE_FLIGHT_NETWORK_CASE_PASSED "+row["owner"]+" "+row["profile"])
            self.position += 1
            self.armed = False
            if self.position == len(PLAN): self.publish("complete")
            else: self.stage, self.stage_started = "start", time.monotonic()
        elif self.stage == "complete":
            if self.acks("complete") is None: return
            if not self.released:
                self.cleanup(); atomic_write(self.root/"release.json", dict(run_id=self.run)); self.released = True
            exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
            if all(value is not None and value["exit_code"] == 0 for value in exits):
                self.report["server_waited_for_client_process_exit"] = True; self.finish()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(not self.report["observation_errors"], "native natural-throw observer failed: "+str(self.report["observation_errors"]))
            require(time.monotonic()-self.started < 500., "native natural-throw authority total timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif self.cls is None:
                self.report["native_mode"] = mode(self.world)
                require(self.report["native_mode"] == "DedicatedServer", "real native dedicated authority required")
                self.install(); self.stage, self.stage_started = "start", time.monotonic()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                self.sample()
                if self.armed: self.capture_health()
                self.step()
            self.report.update(pending_stage=self.stage, pending_begins=self.begins, pending_events=self.events,
                pending_activations=self.activation_events, pending_samples=len(self.samples))
            atomic_write(self.path, self.report)
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_GRENADE_FLIGHT_NETWORK_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPGrenadeFlightNetworkResult=")), None)
if result:
    peer, run = arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
