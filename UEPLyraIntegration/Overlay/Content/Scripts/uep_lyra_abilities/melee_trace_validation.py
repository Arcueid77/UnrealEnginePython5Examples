"""Actual Melee ASC activation against native collision/team/GAS fixtures."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import EObjectTypeQuery, ETraceTypeQuery, EDrawDebugTrace
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from .melee_activation_validation import Validation as Activation, path, vector, config
from .auto_respawn_helpers_validation import specs
from .melee_hit_montage_mixin import CLASS
from .melee_trace_contract import PLAN, require, validate
from .death_observation import cue as cue_values
from . import melee_trace_mixin as policy, melee_activation_mixin as activation

CUE = "/ShooterCore/GameplayCues/GCN_Weapon_Melee.GCN_Weapon_Melee_C"


class Validation(Activation):
    def __init__(self, result):
        super().__init__(result); self.fixtures = []; self.bot_states = []; self.observer = None; self.cues = []; self.events = []; self.observation_errors = []
        self.report = dict(schema_version=1, status="running", error=None, cases=[], full_acceptance=False, network_acceptance=False,
            packaged_runtime=False, physical_input_tested=False, health_properties_written=False, activation_event_replayed=False,
            task_callbacks_replayed=False, ability_granted_by_fixture=False, quantitative_movement_parity_tested=False,
            request_entry="ASC.TryActivateAbilityByClass", fixture_entries=["Actor.K2_TeleportTo", "Actor.add_actor_root_component", "PrimitiveComponent.SetCollisionEnabled"],
            observation_errors=self.observation_errors)

    def box(self, label, location, extent, object_type):
        actor = self.world.actor_spawn(ue.find_class("Actor"), location); require(valid(actor), "native fixture Actor missing")
        self.fixtures.append(actor); actor.call_function("SetReplicates", False)
        box = actor.add_actor_root_component(ue.find_class("BoxComponent"), label)
        box.call_function("SetBoxExtent", extent, False); box.call_function("SetCollisionObjectType", object_type)
        box.call_function("SetCollisionResponseToAllChannels", 2); box.call_function("SetCollisionEnabled", 1)
        # Empty Actors have no root transform until their first native component.
        require(actor.call_function("K2_TeleportTo", location, ue.FRotator()), "native fixture transform refused")
        return actor, box

    def begin(self):
        super().begin(); self.math = ue.find_class("KismetMathLibrary").get_cdo(); self.system = ue.find_class("KismetSystemLibrary").get_cdo()
        self.gas = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo()
        self.teams = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem", self.world, ue.find_class("LyraTeamSubsystem"))
        self.origin = self.v(200000., 200000., 2100.)
        self.floor, _ = self.box("UEPMeleeFloor", self.v(200000., 200000., 1980.), self.v(5000., 5000., 20.), 0)
        self.invalid, self.invalid_box = self.box("UEPMeleeNoASC", self.v(200000., 202000., 2100.), self.v(30., 30., 48.), 2)
        self.wall, self.wall_box = self.box("UEPMeleeOccluder", self.v(200000., 202500., 2100.), self.v(8., 200., 150.), 0)
        self.invalid_box.call_function("SetCollisionEnabled", 0); self.wall_box.call_function("SetCollisionEnabled", 0)
        self.cue_class = ue.load_class(CUE)
        require(not any(row["target_class"] == self.cue_class for row in ue.get_registered_mixins()), "do not replace a production Cue Profile")
        self.original_cue = self.cue_class.get_cdo().find_function("OnBurst"); owner = self
        class ObserveCue:
            def OnBurst(self, Target, Parameters, SpawnResults):
                try:
                    if Target == owner.pawn: owner.cues.append(cue_values(Target, Parameters))
                except Exception: owner.observation_errors.append(traceback.format_exc())
                return self.call_mixin_original("OnBurst", Target, Parameters, SpawnResults)
        ue.register_mixin_profile(self.cue_class, "UEPMeleeTraceObserve", ObserveCue, make_default=True)

    def v(self, x, y, z): return self.math.call_function("MakeVector", float(x), float(y), float(z))

    def living_bots(self):
        controllers, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraPlayerBotController")); result = []
        for controller in controllers:
            pawn = controller.get_controlled_pawn()
            if not valid(pawn): continue
            health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if not valid(health) or health.call_function("IsDeadOrDying") or health.call_function("GetHealth") <= 0: continue
            asc = ability_system(pawn)
            if not valid(asc): continue
            comparison = self.teams.call_function("CompareTeams", pawn, self.pawn)
            result.append((controller, pawn, health, int(comparison[0])))
        return result

    def start(self):
        if self.melee.get_property("bIsActive"): return
        require(time.monotonic()-self.phase_started < 45., "waiting for real living friendly/hostile bot or native respawn")
        bots = self.living_bots(); friendly = [row for row in bots if row[3] == 0]; hostile = [row for row in bots if row[3] == 1]
        if not friendly or not hostile: return
        for controller, pawn, _, _ in bots:
            if not any(row["controller"] == controller for row in self.bot_states):
                self.bot_states.append(dict(controller=controller, pawn=pawn, location=pawn.get_actor_location(), rotation=pawn.get_actor_rotation()))
        scenario, profile = PLAN[self.index]
        for number, (_, pawn, _, _) in enumerate(bots):
            require(pawn.call_function("K2_TeleportTo", self.v(202000.+number*300., 201000., 2100.), ue.FRotator()), "native bot parking refused")
        require(self.pawn.call_function("K2_TeleportTo", self.origin, ue.FRotator()), "native source pose refused")
        self.pawn.call_function("GetMovementComponent").call_function("StopMovementImmediately")
        self.invalid_box.call_function("SetCollisionEnabled", 0); self.wall_box.call_function("SetCollisionEnabled", 0)
        self.target, self.target_health = None, None
        if scenario in ("friendly", "hostile", "occluded"):
            _, self.target, self.target_health, _ = (friendly if scenario == "friendly" else hostile)[0]
            require(self.target.call_function("K2_TeleportTo", self.v(200240., 200000., 2100.), ue.FRotator()), "native target pose refused")
            self.target.call_function("GetMovementComponent").call_function("StopMovementImmediately")
        elif scenario == "invalid-asc":
            self.target = self.invalid; self.invalid_box.call_function("SetCollisionEnabled", 1)
            require(self.target.call_function("K2_TeleportTo", self.v(200240., 200000., 2100.), ue.FRotator()), "native no-ASC fixture pose refused")
        if scenario == "occluded":
            self.wall_box.call_function("SetCollisionEnabled", 1)
            require(self.wall.call_function("K2_TeleportTo", self.v(200100., 200000., 2100.), ue.FRotator()), "native occluder pose refused")
        ue.set_mixin_profile(self.melee, profile)
        self.row = dict(index=self.index, scenario=scenario, profile=profile, source=path(self.pawn), target=path(self.target),
            original_config=config(self.melee), native_active_observed=False, native_montage_task_observed=False)
        self.enter("settle")

    def preflight(self):
        # Independent native calls use authored constants, not policy.trace or
        # a replayed BP event. These also prove each collision fixture branch.
        start = self.pawn.get_property("Mesh").call_function("GetSocketLocation", "hand_r")
        forward = self.pawn.call_function("GetActorForwardVector"); distance = config(self.melee)["Distance"]
        end = self.math.call_function("Add_VectorVector", start, self.math.call_function("Multiply_VectorVector", forward, self.v(distance, distance, distance)))
        options = dict(WorldContextObject=self.melee, bTraceComplex=False, DrawDebugType=getattr(EDrawDebugTrace, "None"), bIgnoreSelf=True,
            TraceColor=ue.FLinearColor(1., 0., 0., 1.), TraceHitColor=ue.FLinearColor(0., 1., 0., 1.), DrawTime=5.)
        hit, result = policy.trace_outputs("CapsuleTraceSingleForObjects", self.system.call_function("CapsuleTraceSingleForObjects", Start=start, End=end, Radius=float(self.melee.Radius),
            HalfHeight=float(self.melee.get_property("Half Height")), ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery3], ActorsToIgnore=[self.pawn], **options))
        row = dict(hit=bool(hit), start=vector(start), end=vector(end), target=None)
        if not hit: return row
        fields = policy.break_hit(result); target = fields["HitActor"]; asc = ability_system(target)
        row.update(target=path(target), target_asc_valid=valid(asc), distance=float(fields["Distance"]))
        if valid(asc):
            comparison = self.teams.call_function("CompareTeams", target, self.pawn)
            row.update(team_comparison=int(comparison[0]), team_ids=[int(value) for value in comparison[1:]])
            if int(comparison[0]) == 1:
                blocked, _ = policy.trace_outputs("LineTraceSingle", self.system.call_function("LineTraceSingle", Start=start, End=fields["ImpactPoint"], TraceChannel=ETraceTypeQuery.TraceTypeQuery4,
                    ActorsToIgnore=[target, self.pawn], **options))
                row["occluded"] = bool(blocked)
        return row

    def request(self):
        self.row["preflight"] = self.preflight(); pre = self.row["preflight"]; scenario = self.row["scenario"]
        require(pre["hit"] == (scenario != "miss") and (not pre["hit"] or pre["target"] == path(self.target)), "real capsule fixture did not select expected target: "+str(pre))
        self.before_trace = policy.snapshot(); self.before_activation = activation.instance_snapshot(self.melee)
        self.cues = []; self.events = []; self.observer = SubscriptionScope()
        if valid(self.target_health):
            target_path = path(self.target)
            self.observer.bind_event(self.target_health, "OnHealthChanged", lambda component, old, new, instigator:
                self.events.append(dict(target=target_path, old=float(old), new=float(new), instigator=path(instigator))))
        self.health_before = float(self.target_health.call_function("GetHealth")) if valid(self.target_health) else 0.
        self.foreign_before = self.foreign_health(); self.started_game = self.game_time()
        self.row["native_request_accepted"] = bool(self.asc.call_function("TryActivateAbilityByClass", ue.load_class(CLASS), False))
        require(self.row["native_request_accepted"], "native Melee activation rejected")
        self.row["native_active_observed"] = bool(self.melee.get_property("bIsActive")); self.row["native_montage_task_observed"] = self.tasks()["montage"]
        self.row["root_tasks"] = [self.root_task(task) for task in self.melee.get_property("ActiveTasks") if valid(task) and task.is_a(ue.find_class("AbilityTask_ApplyRootMotionConstantForce"))]
        self.row["health_after_request"] = float(self.target_health.call_function("GetHealth")) if valid(self.target_health) else 0.
        self.row["health_delta"] = self.health_before-self.row["health_after_request"]
        self.row["stored_effect_context"] = self.effect_context() if scenario == "hostile" else None
        self.enter("observe")

    def foreign_health(self):
        return {key: value for key, value in self.healths().items() if key != path(self.target)}

    def root_task(self, task):
        return dict(direction=vector(task.get_property("WorldDirection")), strength=float(task.get_property("Strength")), duration=float(task.get_property("Duration")),
            additive=bool(task.get_property("bIsAdditive")), gravity=bool(task.get_property("bEnableGravity")), curve=path(task.get_property("StrengthOverTime")),
            finish_mode=int(task.get_property("FinishVelocityMode")), finish_velocity=vector(task.get_property("FinishSetVelocity")), clamp=float(task.get_property("FinishClampVelocity")))

    def effect_context(self):
        context = self.melee.get_property("Gameplay Effect Control Handle Struct")
        hit = self.gas.call_function("EffectContextGetHitResult", context); fields = policy.break_hit(hit)
        return dict(valid=bool(self.gas.call_function("EffectContextIsValid", context)), has_hit=bool(self.gas.call_function("EffectContextHasHitResult", context)),
            hit_actor=path(fields["HitActor"]), blocking=bool(fields["bBlockingHit"]), distance=float(fields["Distance"]))

    def observe(self):
        require(time.monotonic()-self.phase_started < 12., "native Melee trace montage/end timeout")
        if self.melee.get_property("bIsActive"): return
        self.quiet_events = len(self.events); self.quiet_cues = len(self.cues); self.quiet_ticks = 0; self.enter("quiet")

    def quiet(self):
        require(len(self.events) == self.quiet_events and len(self.cues) == self.quiet_cues, "late native damage/Cue after End")
        self.quiet_ticks += 1
        if self.quiet_ticks < 20: return
        after = policy.snapshot()
        self.row.update(trace_stats={key: after[key]-self.before_trace[key] for key in after},
            health_events=copy.deepcopy(self.events), cues=copy.deepcopy(self.cues), health_events_quiet=True,
            native_ended=not bool(self.melee.get_property("bIsActive")), native_tasks_after=self.tasks()["count"],
            actual_scope_closed=getattr(self.melee, "_uep_melee_montage_scope", None) is None, quiet_ticks=self.quiet_ticks,
            foreign_health_unchanged=self.foreign_health() == self.foreign_before, specs_unchanged=specs(self.asc) == self.original["specs"],
            config_unchanged=config(self.melee) == self.original["config"], native_final_location=vector(self.pawn.get_actor_location()))
        self.observer.close(); self.observer = None
        self.report["cases"].append(copy.deepcopy(self.row)); self.index += 1
        ue.log("UEP_MELEE_TRACE_CASE_PASSED "+self.row["scenario"]+" "+self.row["profile"])
        if self.index == len(PLAN): self.finish()
        else: self.enter("start")

    def cleanup(self):
        if self.cleaned: return
        if self.observer is not None: self.observer.close(); self.observer = None
        self.report["observer_scopes_closed"] = self.observer is None
        if hasattr(self, "cue_class"):
            self.report["cue_observer_restored"] = bool(ue.unregister_mixin(self.cue_class)) and self.cue_class.get_cdo().find_function("OnBurst") == self.original_cue
        for row in self.bot_states:
            pawn = row["controller"].get_controlled_pawn()
            if valid(pawn) and not pawn.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("IsDeadOrDying"):
                require(pawn.call_function("K2_TeleportTo", row["location"], row["rotation"]), "native bot pose restore refused")
        for actor in reversed(self.fixtures):
            if valid(actor): actor.actor_destroy()
        self.report["fixtures_destroyed"] = all(not valid(actor) or actor.call_function("IsActorBeingDestroyed") for actor in self.fixtures)
        super().cleanup()

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_MELEE_TRACE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_MELEE_TRACE_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPMeleeTraceResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
