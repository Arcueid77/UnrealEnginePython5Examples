"""Two real native owners, original/Python authority trace, two passive viewers."""
import atexit
import copy
import json
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from .auto_respawn_helpers_network_validation import token
from .auto_respawn_helpers_validation import Validation as Ready, specs
from .jump_network_validation import Server as Playing, arg
from .melee_activation_validation import Validation as Activation, path, vector, config
from .melee_trace_validation import Validation as Trace, CUE
from .melee_activation_network_validation import equipment, tasks
from .melee_trace_contract import PLAN, require
from .melee_trace_network_contract import PEERS, TOTAL, client
from .death_observation import cue as cue_values
from .dash_local_direction_validation import restore_control
from .melee_hit_montage_mixin import CLASS
from . import melee_trace_mixin as policy, melee_activation_mixin as activation, melee_trace_network_observation as observation
from . import melee_replica_readiness as readiness


def player_id(pawn):
    state = pawn.get_property("PlayerState") if valid(pawn) else None
    return int(state.PlayerId) if valid(state) else None


def player_name(pawn):
    state = pawn.get_property("PlayerState") if valid(pawn) else None
    return str(state.call_function("GetPlayerName")) if valid(state) else None


def native_immunity_count(asc):
    return int(asc.call_function("GetGameplayTagCount", GameplayTag(TagName="Gameplay.DamageImmunity")))


def named_pawn(world, statics, name):
    actors, = statics.call_function("GetAllActorsOfClass", world, ue.find_class("Pawn"))
    values = [pawn for pawn in actors if player_name(pawn) == name and valid(pawn.get_component_by_type(ue.find_class("LyraHealthComponent")))]
    return values[0] if len(values) == 1 else None


def pawn_for(world, statics, identifier):
    actors, = statics.call_function("GetAllActorsOfClass", world, ue.find_class("Pawn"))
    return next((pawn for pawn in actors if player_id(pawn) == identifier and valid(pawn.get_component_by_type(ue.find_class("LyraHealthComponent")))) , None)


def floor_state(world, statics):
    actors, = statics.call_function("GetAllActorsOfClass", world, ue.load_class(observation.FLOOR))
    if len(actors) != 1: return None
    box = actors[0].get_component_by_type(ue.find_class("BoxComponent"))
    if not valid(box): return None
    return dict(extent=vector(box.call_function("GetUnscaledBoxExtent")), object_type=int(box.call_function("GetCollisionObjectType")),
        collision=int(box.call_function("GetCollisionEnabled")), location=vector(actors[0].get_actor_location()))


def delta(before, after): return {key: after[key]-before[key] for key in after}


class Client(Activation):
    def __init__(self, result, peer, run):
        super().__init__(result); self.peer, self.run, self.root = peer, run, self.path.parent
        self.require_local_playing_phase = False; self.position = 0; self.command = None; self.observer = None
        self.events = []; self.cues = []; self.observation_errors = []; self.installed = False
        self.early_watch=readiness.EarlyWatch(self.root,peer,run)
        self.report.update(peer=peer, run_id=run, requests=[], views=[], activation_event_replayed=False, callback_replay=False,
            health_properties_written=False, ability_granted_by_fixture=False, packet_loss_tested=False, travel_rejoin_tested=False,
            observation_errors=self.observation_errors)
    def ready(self):
        if token(self.root, "playing-ready.json", self.run) is not None: Ready.ready(self)
    def begin(self):
        super().begin(); self.report.update(player_id=player_id(self.pawn),post_warmup_pawn=path(self.pawn), native_net_mode=str(ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world).call_function("CaptureSnapshot").NetMode))
        observation.install(self); self.installed = True; self.cue_class = ue.load_class(CUE)
        cue_bindings=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cue_class]
        owner = self
        def record(Target,Parameters):
            try:
                if owner.command is not None and player_id(Target)==owner.command["source_player_id"]:
                    value=cue_values(Target,Parameters);value["source_player_id"]=player_id(Target);owner.cues.append(value)
            except Exception:owner.observation_errors.append(traceback.format_exc())
        class ObserveCue:
            def OnBurst(self, Target, Parameters, SpawnResults):
                record(Target,Parameters)
                return self.call_mixin_original("OnBurst", Target, Parameters, SpawnResults)
        if cue_bindings:
            from .melee_cue_observation import ExistingCueObservation
            self.current_cue_observation=ExistingCueObservation(ue,self.cue_class,cue_bindings[0],record)
            self.report['production_cue_profiles_observed']=sorted(self.current_cue_observation.originals)
        else:
            self.original_cue=self.cue_class.get_cdo().find_function('OnBurst')
            ue.register_mixin_profile(self.cue_class,"UEPMeleeTraceNetworkObserve",ObserveCue,make_default=True)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"])); self.enter("idle")
    def before_activation(self, instance): pass
    def after_activation(self, instance):
        if instance != self.melee: return
        require(self.command is not None and self.command["source_peer"] == self.peer, "unrequested owner Melee activation")
        self.witness = dict(native_activation_observed=bool(instance.get_property("bIsActive")), native_montage_observed=tasks(instance)["montage"],
            native_ability_authority=bool(instance.call_function("K2_HasAuthority")), native_activation_mode=int(instance.get_property("CurrentActivationInfo").ActivationMode))
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-activation.json"), dict(run_id=self.run, position=self.position, witness=self.witness))
    def arm(self, command):
        floor = floor_state(self.world, self.statics)
        state = dict(position=self.position, target_player_name=command["target_player_name"], floor=floor, waiting="native-floor")
        self.report["pending_arm"] = state
        if floor is None or floor["extent"] != [5000., 5000., 20.] or floor["object_type"] != 0 or floor["collision"] != 3: return
        source = pawn_for(self.world, self.statics, command["source_player_id"])
        state.update(waiting="source-pawn", source=path(source))
        if not valid(source): return
        if command["source_peer"] == self.peer: self.controller.call_function("SetControlRotation", ue.FRotator())
        point = vector(source.get_actor_location())
        state.update(waiting="replicated-source-pose", source_location=point, expected_source_location=command["source_location"])
        if sum((value-target)**2 for value,target in zip(point, command["source_location"])) > 400.: return
        target = named_pawn(self.world, self.statics, command["target_player_name"]) if command["target_player_name"] is not None else None
        health = target.get_component_by_type(ue.find_class("LyraHealthComponent")) if valid(target) else None
        state.update(waiting="unique-replicated-target-and-health", target=path(target), target_health=float(health.call_function("GetHealth")) if valid(health) else None, expected_target_health=command["target_health"])
        if valid(target) and valid(health):
            state["native_target_binding"] = dict(health_set=path(health.get_property("HealthSet")),
                health_asc=path(health.get_property("AbilitySystemComponent")), actor_asc=path(ability_system(target)),
                player_state_pawn=path(target.get_property("PlayerState").call_function("GetPawn")),
                death_state=int(health.call_function("GetDeathState")), max_health=float(health.call_function("GetMaxHealth")))
            binding = readiness.snapshot(target, health)
            state["native_replica_state"] = binding
            fingerprint = json.dumps(dict(position=self.position, binding=binding), sort_keys=True)
            if fingerprint != getattr(self,"_last_replica_fingerprint",None):
                self._last_replica_fingerprint = fingerprint
                files = self.report.setdefault("replica_binding_event_files",[])
                require(len(files) < 256, "bounded native replica diagnostic history exhausted")
                name = self.peer+"-replica-binding-"+str(len(files))+".json"
                atomic_write(self.root/name, dict(run_id=self.run, position=self.position, binding=binding, view=readiness.view_state(self.controller)))
                files.append(name)
        if command["target_player_name"] is not None and not valid(target):
            actors, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("Pawn"))
            state["native_pawn_names"] = [dict(path=path(pawn), player_name=player_name(pawn), player_id=player_id(pawn)) for pawn in actors]
        if command["target_player_name"] is not None and (not valid(health) or health.call_function("GetHealth") != command["target_health"]): return
        state["waiting"] = "ready"
        self.report["native_floor_archetype_observed"] = True; self.command = command; self.target_health = health
        self.events = []; self.cues = []; self.observer = SubscriptionScope(); self.witness = None; self.requested = False
        self.own_health_before = float(self.health.call_function("GetHealth")); self.target_health_before = float(health.call_function("GetHealth")) if valid(health) else 0.
        if valid(health): self.observer.bind_event(health, "OnHealthChanged", lambda component, old, new, instigator: self.events.append(dict(old=float(old), new=float(new))))
        self.before_trace = policy.snapshot()
        if command["source_peer"] == self.peer: ue.set_mixin_profile(self.melee, command["profile"])
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-armed.json"), dict(run_id=self.run, position=self.position)); self.enter("observe")
    def observe(self):
        require(time.monotonic()-self.phase_started < 25., "native viewer/owner authority trace timeout")
        command = self.command
        if command["source_peer"] == self.peer and not self.requested:
            permission = token(self.root, "permit.json", self.run)
            if permission is not None and permission["position"] == self.position:
                self.requested = True
                self.request = dict(index=command["index"], scenario=command["scenario"], profile=command["profile"],
                    native_request_accepted=bool(self.asc.call_function("TryActivateAbilityByClass", ue.load_class(CLASS), False)))
                require(self.request["native_request_accepted"] and self.witness is not None, "real owning native Melee activation/witness missing")
                self.request.update(self.witness)
        ended = token(self.root, "authority-ended.json", self.run)
        if ended is None or ended["position"] != self.position or self.melee.get_property("bIsActive"): return
        expected_health = int(command["scenario"] == "hostile")
        # Preserve the original GAS local-prediction-key echo filter: this
        # authority-only BP Cue reaches the other viewer, not its predictor.
        expected_cue = int(command["scenario"] == "hostile" and command["source_peer"] != self.peer)
        if len(self.cues) < expected_cue or len(self.events) < expected_health: return
        self.quiet_fingerprint = (len(self.events), len(self.cues)); self.quiet_ticks = 0; self.enter("quiet")
    def quiet(self):
        require((len(self.events), len(self.cues)) == self.quiet_fingerprint, "late replicated Health/Cue during quiet")
        self.quiet_ticks += 1
        if self.quiet_ticks < 20: return
        command = self.command; after = policy.snapshot()
        if command["source_peer"] == self.peer:
            self.request.update(native_ended=not bool(self.melee.get_property("bIsActive")), native_tasks_after=tasks(self.melee)["count"],
                trace_queries=after["queries"]-self.before_trace["queries"], trace_fallbacks=after["fallback_queries"]-self.before_trace["fallback_queries"])
            self.report["requests"].append(copy.deepcopy(self.request))
        value = dict(position=self.position, source_peer=command["source_peer"], source_player_id=command["source_player_id"], index=command["index"],
            scenario=command["scenario"], profile=command["profile"], native_health_delta=sum(item["old"]-item["new"] for item in self.events),
            target_player_name=command["target_player_name"], target_identity_unique=True,
            health_events=copy.deepcopy(self.events), cues=copy.deepcopy(self.cues), quiet_ticks=self.quiet_ticks,
            own_health_unchanged=float(self.health.call_function("GetHealth")) == self.own_health_before, foreign_ability_idle=not bool(self.melee.get_property("bIsActive")))
        self.observer.close(); self.observer = None; value["observer_scope_closed"] = True
        self.report["views"].append(value)
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-ack.json"), dict(run_id=self.run, position=self.position, row=value)); self.enter("accepted")
    def cleanup(self):
        if self.cleaned: return
        if getattr(self,"warmup_join_control",None) is not None: self.warmup_join_control.close()
        if getattr(self,"character_default_control",None) is not None: self.character_default_control.restore()
        self.early_watch.close(); self.report["early_readiness_event_files"]=list(self.early_watch.files)
        if self.observer is not None: self.observer.close(); self.observer = None
        self.report["observer_scope_closed"] = self.observer is None
        if getattr(self,'current_cue_observation',None) is not None:
            self.report['cue_observer_restored']=self.current_cue_observation.restore()
        elif hasattr(self, "original_cue"):
            self.report["cue_observer_restored"] = bool(ue.unregister_mixin(self.cue_class)) and self.cue_class.get_cdo().find_function("OnBurst") == self.original_cue
        if self.installed: self.report["activation_observers_restored"] = observation.restore()
        if hasattr(self, "original"):
            ue.set_mixin_profile(self.melee, self.original["profile"])
            self.report.update(profile_restored=str(ue.get_mixin_profile(self.melee)) == self.original["profile"],
                specs_config_unchanged=specs(self.asc) == self.original["specs"] and config(self.melee) == self.original["config"],
                native_control_restoration=restore_control(self.controller, self.original["control"]), shutdown=activation.snapshot())
        self.cleaned = True
    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 500., "native trace owner/viewer total timeout")
            if getattr(self,"warmup_join_control",None) is not None: self.warmup_join_control.client_poll()
            if getattr(self,"character_default_control",None) is not None: self.character_default_control.observe_registration()
            self.early_watch.poll();self.report["early_readiness_event_files"]=list(self.early_watch.files)
            if self.phase == "ready": self.ready()
            elif self.phase == "idle":
                command = token(self.root, "arm.json", self.run)
                if command is not None and command["position"] == self.position: self.arm(command)
            elif self.phase == "observe": self.observe()
            elif self.phase == "quiet": self.quiet()
            elif self.phase == "accepted":
                accepted = token(self.root, "accepted.json", self.run)
                if accepted is not None and accepted["position"] == self.position:
                    self.position += 1; self.command = None
                    if self.position == TOTAL:
                        self.cleanup(); atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run)); self.enter("release")
                    else: self.enter("idle")
            elif self.phase == "release" and token(self.root, "release.json", self.run) is not None: self.finish()
            self.report["phase"] = self.phase
            self.report["pending_case"] = dict(command=self.command, health_events=copy.deepcopy(self.events), cues=copy.deepcopy(self.cues), witness=getattr(self,"witness",None), requested=getattr(self,"requested",False))
            self.write(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_MELEE_TRACE_NETWORK_VIEW_"+("FAILED "+error if error else "PASSED")); ue.request_exit()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; client(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_MELEE_TRACE_SHUTDOWN_"+self.report["status"].upper())


class Server(Playing):
    box, v, living_bots, preflight, root_task, effect_context = Trace.box, Trace.v, Trace.living_bots, Trace.preflight, Trace.root_task, Trace.effect_context
    def __init__(self, result, run):
        super().__init__(result, run); self.ability_class = CLASS; self.prepared = False; self.released = False; self.scope = None
        self.early_watch=readiness.EarlyWatch(self.root,"server",run)
        self.fixtures = []; self.bot_states = []; self.events = []; self.observation_errors = []
        self.report.update(native_net_mode="DedicatedServer", observation_errors=self.observation_errors,
            health_properties_written=False, activation_event_replayed=False, native_fixture_teleports=True)
    def owner_state(self, peer):
        value = self.owners[peer]; pawn, ability = value["pawn"], value["ability"]
        return dict(health=float(pawn.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth")),
            active=bool(ability.get_property("bIsActive")), profile=str(ue.get_mixin_profile(ability)), specs=specs(ability_system(pawn)), config=config(ability), equipment=equipment(pawn))
    def prepare(self):
        self.math = ue.find_class("KismetMathLibrary").get_cdo(); self.system = ue.find_class("KismetSystemLibrary").get_cdo(); self.gas = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo()
        self.teams = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem", self.world, ue.find_class("LyraTeamSubsystem"))
        self.report["native_net_mode"] = str(ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world).call_function("CaptureSnapshot").NetMode)
        self.originals = {peer: dict(profile=str(ue.get_mixin_profile(value["ability"])), specs=specs(ability_system(value["pawn"])), config=config(value["ability"]),
            location=value["pawn"].get_actor_location(), rotation=value["pawn"].get_actor_rotation()) for peer,value in self.owners.items()}
        self.floor = self.world.actor_spawn(ue.load_class(observation.FLOOR), self.v(200000., 200000., 1980.)); self.fixtures.append(self.floor)
        require(valid(self.floor) and floor_state(self.world, self.statics)["extent"] == [5000., 5000., 20.], "native replicated floor missing")
        self.invalid, self.invalid_box = self.box("UEPNetworkMeleeNoASC", self.v(200000., 202000., 2100.), self.v(30., 30., 48.), 2)
        self.wall, self.wall_box = self.box("UEPNetworkMeleeWall", self.v(200000., 202500., 2100.), self.v(8., 200., 150.), 0)
        observation.install(self); self.prepared = True
    def start_case(self):
        peer, index = PEERS[self.position//len(PLAN)], self.position%len(PLAN); self.pawn, self.melee = self.owners[peer]["pawn"], self.owners[peer]["ability"]
        if any(value["ability"].get_property("bIsActive") for value in self.owners.values()): return
        bots = self.living_bots()
        ready_bots = [value for value in bots if native_immunity_count(ability_system(value[1])) == 0]
        friendly = [value for value in ready_bots if value[3] == 0]; hostile = [value for value in ready_bots if value[3] == 1]
        if not friendly or not hostile: return
        for controller,pawn,_,_ in bots:
            if not any(value["controller"] == controller for value in self.bot_states): self.bot_states.append(dict(controller=controller, location=pawn.get_actor_location(), rotation=pawn.get_actor_rotation()))
        for number,(_,pawn,_,_) in enumerate(bots): require(pawn.call_function("K2_TeleportTo", self.v(202000.+number*300., 202000., 2100.), ue.FRotator()), "native bot parking failed")
        for number,(name,value) in enumerate(self.owners.items()):
            point = self.v(200000., 200000., 2100.) if name == peer else self.v(202000.+number*300., 201000., 2100.)
            require(value["pawn"].call_function("K2_TeleportTo", point, ue.FRotator()), "authority source/foreign pose refused")
            value["pawn"].CharacterMovement.call_function("StopMovementImmediately"); value["pawn"].call_function("ForceNetUpdate")
        scenario, profile = PLAN[index]; self.invalid_box.call_function("SetCollisionEnabled", 0); self.wall_box.call_function("SetCollisionEnabled", 0)
        self.target = self.target_health = None
        if scenario in ("friendly", "occluded", "hostile"):
            _,self.target,self.target_health,_ = (friendly if scenario == "friendly" else hostile)[0]
            require(self.target.call_function("K2_TeleportTo", self.v(200240., 200000., 2100.), ue.FRotator()), "authority target pose refused")
            self.target.CharacterMovement.call_function("StopMovementImmediately"); self.target.call_function("ForceNetUpdate")
        elif scenario == "invalid-asc":
            self.target = self.invalid; self.invalid_box.call_function("SetCollisionEnabled", 1)
            require(self.invalid.call_function("K2_TeleportTo", self.v(200240., 200000., 2100.), ue.FRotator()), "authority no-ASC pose refused")
        if scenario == "occluded":
            self.wall_box.call_function("SetCollisionEnabled", 1)
            require(self.wall.call_function("K2_TeleportTo", self.v(200100., 200000., 2100.), ue.FRotator()), "authority occlusion pose refused")
        ue.set_mixin_profile(self.melee, profile)
        self.current = dict(position=self.position, source_peer=peer, index=index, scenario=scenario, profile=profile, source_player_id=self.owners[peer]["player_id"],
            native_role=int(self.pawn.call_function("GetLocalRole")), original_config=config(self.melee), target=path(self.target),
            target_player_name=player_name(self.target) if valid(self.target_health) else None, native_activation_observed=False)
        command = dict(self.current, run_id=self.run, source_location=vector(self.pawn.get_actor_location()), target_player_id=player_id(self.target) if valid(self.target_health) else None,
            target_health=float(self.target_health.call_function("GetHealth")) if valid(self.target_health) else None,
            native_authority_views={name:readiness.view_state(value["controller"]) for name,value in self.owners.items()})
        self.case_started = time.monotonic(); self.permitted = self.end_sent = False; self.quiet_ticks = 0; self.events = []
        atomic_write(self.root/"arm.json", command)
    def before_activation(self, instance):
        require(self.current is not None and instance == self.melee, "unrequested actual authority Melee activation")
        self.current["preflight"] = self.preflight(); self.before_trace = policy.snapshot()
        self.current["target_immunity_count_at_activation"] = native_immunity_count(ability_system(self.target)) if valid(self.target_health) else None
        if valid(self.target_health): require(self.current["target_immunity_count_at_activation"] == 0, "native target still has original spawn damage immunity; do not remove it")
        self.foreign_before = {peer:self.owner_state(peer) for peer in PEERS if peer != self.current["source_peer"]}
        self.health_before = float(self.target_health.call_function("GetHealth")) if valid(self.target_health) else 0.
        self.scope = SubscriptionScope()
        if valid(self.target_health): self.scope.bind_event(self.target_health, "OnHealthChanged", lambda component,old,new,instigator: self.events.append(dict(old=float(old), new=float(new))))
    def after_activation(self, instance):
        require(instance == self.melee and self.current is not None, "foreign actual authority witness")
        self.current.update(native_activation_observed=bool(instance.get_property("bIsActive")), native_montage_observed=tasks(instance)["montage"],
            root_tasks=[self.root_task(task) for task in instance.get_property("ActiveTasks") if valid(task) and task.is_a(ue.find_class("AbilityTask_ApplyRootMotionConstantForce"))],
            native_health_delta=self.health_before-(float(self.target_health.call_function("GetHealth")) if valid(self.target_health) else 0.),
            stored_effect_context=self.effect_context() if self.current["scenario"] == "hostile" else None)
        atomic_write(self.root/("server-"+str(self.position)+"-activation.json"), dict(run_id=self.run, position=self.position, row=self.current, health_events=self.events))
    def observe(self):
        require(time.monotonic()-self.case_started < 35., "authority/client native trace case timeout")
        if not self.permitted:
            armed = [token(self.root, peer+"-"+str(self.position)+"-armed.json", self.run) for peer in PEERS]
            if not all(value is not None and value["position"] == self.position for value in armed): return
            self.permitted = True; atomic_write(self.root/"permit.json", dict(run_id=self.run, position=self.position)); return
        require(valid(self.melee), "actual authority source removed before coordinated cleanup")
        if not self.current["native_activation_observed"] or self.melee.get_property("bIsActive"): return
        if not self.end_sent:
            self.end_sent = True; self.quiet_before = policy.snapshot()
            atomic_write(self.root/"authority-ended.json", dict(run_id=self.run, position=self.position))
        require(policy.snapshot() == self.quiet_before, "late authority trace after native End")
        acks = {peer:token(self.root, peer+"-"+str(self.position)+"-ack.json", self.run) for peer in PEERS}
        if not all(acks.values()): return
        self.quiet_ticks += 1
        if self.quiet_ticks < 20: return
        self.scope.close(); self.scope = None; peer = self.current["source_peer"]
        self.current.update(trace_stats=delta(self.before_trace, policy.snapshot()), health_events=copy.deepcopy(self.events), native_ended=True,
            native_tasks_after=tasks(self.melee)["count"], quiet_ticks=self.quiet_ticks, observer_scope_closed=True,
            foreign_owner_unchanged=all(self.owner_state(name) == before for name,before in self.foreign_before.items()),
            specs_config_unchanged=all(specs(ability_system(value["pawn"])) == self.originals[name]["specs"] and config(value["ability"]) == self.originals[name]["config"] for name,value in self.owners.items()),
            viewers={name:value["row"] for name,value in acks.items()})
        self.report["cases"].append(copy.deepcopy(self.current)); atomic_write(self.root/"accepted.json", dict(run_id=self.run, position=self.position))
        ue.log("UEP_MELEE_TRACE_NETWORK_CASE_OBSERVED "+peer+"/"+str(self.current["index"]))
        self.position += 1; self.current = None
    def restore(self):
        if self.scope is not None: self.scope.close(); self.scope = None
        for peer,value in self.owners.items():
            ue.set_mixin_profile(value["ability"], self.originals[peer]["profile"])
            require(value["pawn"].call_function("K2_TeleportTo", self.originals[peer]["location"], self.originals[peer]["rotation"]), "native authority pose restore failed")
            value["pawn"].call_function("ForceNetUpdate")
        for row in self.bot_states:
            pawn = row["controller"].get_controlled_pawn()
            if valid(pawn) and not pawn.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("IsDeadOrDying"):
                require(pawn.call_function("K2_TeleportTo", row["location"], row["rotation"]), "native bot pose restore failed")
        for actor in reversed(self.fixtures):
            if valid(actor): actor.actor_destroy()
        self.report.update(profiles_restored=all(str(ue.get_mixin_profile(value["ability"])) == self.originals[peer]["profile"] for peer,value in self.owners.items()),
            specs_config_unchanged=all(specs(ability_system(value["pawn"])) == self.originals[peer]["specs"] and config(value["ability"]) == self.originals[peer]["config"] for peer,value in self.owners.items()),
            activation_observers_restored=observation.restore(), observer_scope_closed=self.scope is None,
            fixtures_destroyed=all(not valid(actor) or actor.call_function("IsActorBeingDestroyed") for actor in self.fixtures), shutdown=activation.snapshot())
    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 500., "native authority trace total timeout")
            if getattr(self,"warmup_join_control",None) is not None: self.warmup_join_control.server_poll()
            self.early_watch.poll();self.report["early_readiness_event_files"]=list(self.early_watch.files)
            if getattr(self,"character_default_control",None) is not None: self.character_default_control.observe_registration()
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == TOTAL:
                    if all(token(self.root, peer+"-complete.json", self.run) is not None for peer in PEERS):
                        if not self.released: self.restore(); atomic_write(self.root/"release.json", dict(run_id=self.run)); self.released = True
                        exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                        if all(value is not None and value["exit_code"] == 0 for value in exits): self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            self.report["pending_case"] = copy.deepcopy(self.current)
            self.report["pending_health_events"] = copy.deepcopy(self.events)
            atomic_write(self.path, self.report); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_MELEE_TRACE_NETWORK_"+self.report["status"].upper())
    def finish(self, error=None):
        if self.finished: return
        try:
            if getattr(self,"warmup_join_control",None) is not None: self.warmup_join_control.close()
            if getattr(self,"character_default_control",None) is not None: self.character_default_control.restore()
            self.early_watch.close()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report["early_readiness_event_files"]=list(self.early_watch.files)
        super().finish(error)


if any(value.startswith("-UEPMeleeTraceNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPMeleeTraceNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    mode=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPReplicaCharacterStartupProfile=")),None)
    if mode:
        from .melee_character_default_control import CharacterDefaultControl
        subset=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPReplicaCharacterOriginalSubset=")),None)
        character_default_control=CharacterDefaultControl(mode,original_begin_play="-UEPReplicaCharacterOriginalBeginPlay" in sys.argv,original_subset=subset)
    else: character_default_control=None
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    validation.character_default_control=character_default_control
    validation.warmup_join_control=None
    if "-UEPReplicaWarmupJoin" in sys.argv:
        from .melee_warmup_join_control import WarmupJoinControl
        validation.warmup_join_control=WarmupJoinControl(validation.root,peer,run)
        validation.report["controlled_warmup_join"]=validation.warmup_join_control.report
    if character_default_control is not None:
        character_default_control.observe_births(validation.early_watch)
        validation.report["character_startup_control"]=character_default_control.report
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
