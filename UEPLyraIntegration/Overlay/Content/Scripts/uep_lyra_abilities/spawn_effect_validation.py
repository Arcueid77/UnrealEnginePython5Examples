"""Native existing OnSpawn spec, original effect/montage and world-time matrix."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayEffectQuery, GameplayTag
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_world.inventory_pad_network_state import capture
from . import spawn_effect_mixin as policy
from .spawn_effect_contract import PLAN, require, validate


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.paused, self.foreign_owned, self.sides = False, False, False, []
        self.plan, self.timeout = PLAN, 240.
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(status="running", error=None, cases=[], original_player_restored=False,
            original_ability_specs_restored=False, original_fraction_restored=False,
            native_default_on_spawn_observed=False, fixture_native_existing_spec_activation=True,
            fixture_input_fraction_per_instance_written=True, native_immediate_handoff_tested=False,
            nullable_cached_controller_regressions=[])
        for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "activation_handler_replayed", "task_callbacks_replayed",
            "health_properties_written", "animation_assets_modified", "original_montage_or_effect_written"): self.report[field] = False

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))
    def ignored(self): return bool(self.controller.call_function("IsMoveInputIgnored"))
    def active(self): return bool(self.ability.get_property("bIsActive"))
    def tasks(self): return sum(valid(value) for value in self.ability.get_property("ActiveTasks"))
    def effects(self): return len(self.asc.call_function("GetActiveEffects", GameplayEffectQuery(EffectDefinition=ue.load_class(policy.EFFECT))))
    def immune(self): return bool(self.asc.call_function("HasMatchingGameplayTag", GameplayTag(TagName="Gameplay.DamageImmunity")))
    def specs(self):
        return sorted(value.get_path_name() for spec in self.asc.get_property("ActivatableAbilities").Items
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value))

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bHealthReady and snap.Health > 0 and not snap.bDamageImmune): continue
            controller = self.statics.call_function("GetPlayerController", world, 0); model = capture(controller)
            if model is None or "ID_Pistol" not in model["definition"]: continue
            pawn = controller.get_controlled_pawn(); asc = ability_system(pawn); cls = ue.load_class(policy.CLASS)
            matches = [value for spec in asc.get_property("ActivatableAbilities").Items if valid(spec.Ability) and spec.Ability.get_class() == cls
                for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
            self.waiting = dict(spawn_instances=len(matches))
            if len(matches) != 1 or matches[0].get_property("bIsActive"): continue
            self.attach(controller, matches[0]); self.begin(); return

    def attach(self, controller, ability):
        pawn = controller.get_controlled_pawn()
        self.world, self.controller, self.pawn, self.asc, self.cls, self.ability = pawn.get_world(), controller, pawn, ability_system(pawn), ue.load_class(policy.CLASS), ability
        self.bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.anim = pawn.Mesh.call_function("GetAnimInstance")
        self.original_model, self.original_specs, self.original_fraction = capture(controller), self.specs(), float(self.ability.EnableInputAfterTimeFraction)
        self.original_profile = str(ue.get_mixin_profile(self.ability))
        require(self.effects() == 0 and not self.ignored(), "native SpawnEffect baseline is not clean")
        counts = policy.instance_snapshot(self.ability)
        self.report["native_default_on_spawn_observed"] = counts["activations"] >= 1 and counts["native_ends"] == counts["activations"]
        require(self.report["native_default_on_spawn_observed"], "actual existing OnSpawn instance did not naturally run Python")
        self.report.update(native_policy=[int(self.ability.NetExecutionPolicy), int(self.ability.InstancingPolicy), int(self.ability.ActivationPolicy)],
            original_montage=self.ability.SpawnMontage.get_path_name(), original_effect=policy.EFFECT, original_input_fraction=self.original_fraction)
        self.nullable_controller_regression()

    def nullable_controller_regression(self):
        # Real existing native instance + real Controller foreign lock. Only
        # its cache is temporarily made null, never its ActorInfo/CDO/owner.
        cached, held = self.ability.CachedController, False
        before = policy.instance_snapshot(self.ability)
        effects_before, tasks_before = self.effects(), self.tasks()
        row = dict(fixture_cached_controller_per_instance_written=True, original_bp_null_warning_parity_claimed=False,
            actual_existing_instance=self.ability.get_class() == self.cls, native_actor_info_controller_preserved=False)
        try:
            self.controller.call_function("SetIgnoreMoveInput", True); held = True
            self.ability.set_property("CachedController", None)
            row["native_actor_info_controller_preserved"] = self.ability.call_function("GetControllerFromActorInfo") == self.controller
            self.ability.call_function("DisableInput"); self.ability.call_function("EnableInputAgain")
            row["foreign_native_input_lock_preserved"] = self.ignored()
            after = policy.instance_snapshot(self.ability)
            effects_after, tasks_after = self.effects(), self.tasks()
            row.update(effects_before=effects_before, effects_after=effects_after, tasks_before=tasks_before, tasks_after=tasks_after,
                effects_created=after["effects_applied"]-before["effects_applied"], tasks_created=after["tasks_created"]-before["tasks_created"])
            row["no_effect_or_task_created"] = effects_after <= effects_before and tasks_after <= tasks_before and row["effects_created"] == row["tasks_created"] == 0
            row.update(nullable_entries=after["controller_unavailable"]-before["controller_unavailable"],
                owned_locks=after["movement_locks"]-before["movement_locks"], owned_unlocks=after["movement_unlocks"]-before["movement_unlocks"])
        finally:
            self.ability.set_property("CachedController", cached)
            if held: self.controller.call_function("SetIgnoreMoveInput", False)
        row.update(original_cache_restored=self.ability.CachedController == cached, native_input_baseline_restored=not self.ignored())
        self.report["nullable_cached_controller_regressions"].append(row)

    def begin(self):
        self.prepare_trial()
        require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native existing SpawnEffect activation refused")
        self.record_start(); self.enter("running")

    def prepare_trial(self):
        self.name, self.profile = self.plan[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        require(not self.active() and self.effects() == 0 and not self.ignored(), "previous native spawn fixture not settled")
        ue.set_mixin_profile(self.ability, self.profile)
        fraction = 0. if self.name == "zero-input-fraction" else (1. if self.name == "end-input-fraction" else self.original_fraction)
        self.ability.set_property("EnableInputAfterTimeFraction", fraction)
        if self.name == "foreign-input-lock":
            self.controller.call_function("SetIgnoreMoveInput", True); self.foreign_owned = True
        self.before, self.trial_started = policy.instance_snapshot(self.ability), self.game_time()
        self.row = dict(native_type_preserved=self.ability.get_class() == self.cls, input_fraction=fraction,
            montage_length=float(self.ability.SpawnMontage.call_function("GetPlayLength")), unlock_elapsed=None,
            native_montage_playing_observed=False, profile_teardown_ended_ability=False,
            native_pause_observed=False, interrupt_left_ability_active=False)
        self.action_done = False
    def record_start(self):
        self.row.update(effect_at_start=self.effects(), immune_at_start=self.immune(), movement_locked_at_start=self.ignored())
        self.row.update(native_source_avatar_matches=self.ability.call_function("GetAvatarActorFromActorInfo") == self.pawn,
            native_role=int(self.pawn.call_function("GetLocalRole")))

    def may_perform_action(self): return True
    def may_capture_end(self): return True

    def running(self):
        elapsed = self.game_time()-self.trial_started; active = self.active()
        self.row["native_montage_playing_observed"] |= bool(self.anim.call_function("Montage_IsPlaying", self.ability.SpawnMontage))
        if self.row["unlock_elapsed"] is None and not self.ignored(): self.row["unlock_elapsed"] = elapsed
        if active and elapsed > .3 and not self.action_done and self.may_perform_action():
            self.action_done = True
            if self.name == "montage-interrupt":
                self.anim.call_function("Montage_Stop", 0., self.ability.SpawnMontage)
                self.row["interrupt_left_ability_active"] = self.active() and self.effects() == 1
            elif self.name == "native-cancel": self.ability.call_function("K2_CancelAbility")
            elif self.name == "external-native-end": self.ability.call_function("K2_EndAbility")
            elif self.name == "active-profile-switch":
                ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
                self.row["profile_teardown_ended_ability"] = not self.active()
            elif self.name == "paused-world-time":
                self.frozen_time = self.game_time()
                require(self.statics.call_function("SetGamePaused", self.world, True), "native spawn pause refused")
                self.paused = True; self.enter("paused"); return
        if self.active():
            require(elapsed < self.row["montage_length"]+1., "native spawn ability did not end"); return
        if not self.may_capture_end(): return
        self.row.update(native_elapsed=elapsed, native_ability_ended=True, tasks_after_end=self.tasks(), effects_after_end=self.effects(),
            immune_after_end=self.immune(), movement_after_end=self.ignored())
        self.at_end_business = self.business_counts(); self.enter("settle")

    def business_counts(self):
        counts = policy.instance_snapshot(self.ability)
        return {key: counts[key] for key in ("activations", "effects_applied", "effects_removed", "movement_locks", "movement_unlocks")}

    def paused_tick(self):
        require(abs(self.game_time()-self.frozen_time) < .001 and self.active() and self.effects() == 1 and self.ignored(), "paused world advanced native spawn lifetime")
        if time.monotonic()-self.phase_started < .3: return
        self.row["native_pause_observed"] = True
        require(self.statics.call_function("SetGamePaused", self.world, False), "native spawn unpause refused")
        self.paused = False; self.enter("running")

    def settle(self):
        # Also observe the old deadline after early End. UE's native EndAbility
        # removes Blueprint latent actions; neither side may mutate afterward.
        if self.game_time()-self.trial_started < self.row["montage_length"]+.3: return
        self.row["no_late_business_mutation"] = self.business_counts() == self.at_end_business
        require(not self.active() and self.effects() == 0 and self.tasks() == 0, "native spawn tasks/effect not settled")
        if self.foreign_owned:
            require(self.ignored(), "spawn cleanup consumed the foreign movement lock")
            self.controller.call_function("SetIgnoreMoveInput", False); self.foreign_owned = False
        self.row["foreign_lock_released_restores_baseline"] = not self.ignored()
        self.row["original_player_restored"] = capture(self.controller) == self.original_model
        after = policy.instance_snapshot(self.ability)
        self.row["counters"] = {key: value-self.before[key] for key, value in after.items()}
        self.complete_trial()

    def complete_trial(self):
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_SPAWN_EFFECT_CASE_OBSERVED "+self.name)
        self.index += 1
        if self.index == len(self.plan)*2: self.begin_handoff()
        else: self.begin()

    def begin_handoff(self):
        require(not self.active() and self.effects() == 0 and not self.ignored(), "handoff fixture baseline not clean")
        self.ability.set_property("EnableInputAfterTimeFraction", self.original_fraction)
        ue.set_mixin_profile(self.ability, "BlueprintFallback")
        self.handoff = dict(old_activation_ended=False, new_python_activated=False,
            alive_after_old_bp_deadline=False, new_python_enable_requests=0, unlock_elapsed=None)
        self.handoff_before = policy.instance_snapshot(self.ability)
        self.old_started = self.game_time()
        require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native BP handoff activation refused")
        self.enter("handoff-bp")

    def handoff_bp(self):
        if self.game_time()-self.old_started < .3: return
        require(self.active() and self.effects() == 1, "native BP ended before handoff")
        ue.set_mixin_profile(self.ability, "Python")
        self.handoff["old_activation_ended"] = not self.active() and self.effects() == 0 and not self.ignored()
        require(self.handoff["old_activation_ended"], "native old BP Profile cleanup failed")
        self.new_started = self.game_time()
        require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "immediate native Python activation refused")
        self.handoff["new_python_activated"] = self.active() and self.effects() == 1 and self.ignored()
        self.enter("handoff-python")

    def handoff_python(self):
        elapsed = self.game_time()-self.new_started
        if self.handoff["unlock_elapsed"] is None and not self.ignored(): self.handoff["unlock_elapsed"] = elapsed
        duration = float(self.ability.SpawnMontage.call_function("GetPlayLength"))
        if not self.handoff["alive_after_old_bp_deadline"] and self.game_time()-self.old_started >= duration+.06:
            self.handoff["alive_after_old_bp_deadline"] = self.active() and self.effects() == 1
            require(self.handoff["alive_after_old_bp_deadline"], "old BP Delay ended the new Python activation")
        if self.active():
            require(elapsed < duration+.5, "handoff Python native timer did not finish"); return
        require(self.effects() == self.tasks() == 0 and not self.ignored() and not self.immune(), "handoff native cleanup leaked")
        counts = policy.instance_snapshot(self.ability)
        self.handoff.update(new_native_elapsed=elapsed, montage_length=duration, input_fraction=self.original_fraction,
            new_python_enable_requests=counts["enable_requests"]-self.handoff_before["enable_requests"],
            effects_after_end=self.effects(), tasks_after_end=self.tasks(), original_player_restored=capture(self.controller) == self.original_model)
        self.report["blueprint_to_python_immediate_handoff"] = copy.deepcopy(self.handoff)
        self.report["native_immediate_handoff_tested"] = True
        ue.log("UEP_SPAWN_EFFECT_IMMEDIATE_HANDOFF_OBSERVED"); self.finish()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < self.timeout, "native SpawnEffect total timeout: "+self.phase+" "+repr(getattr(self, "waiting", None)))
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            {"ready": self.ready, "running": self.running, "paused": self.paused_tick, "settle": self.settle,
                "handoff-bp": self.handoff_bp, "handoff-python": self.handoff_python}[self.phase]()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            if hasattr(self, "ability"):
                if self.active(): self.ability.call_function("K2_EndAbility")
                if self.foreign_owned: self.controller.call_function("SetIgnoreMoveInput", False); self.foreign_owned = False
                self.ability.set_property("EnableInputAfterTimeFraction", self.original_fraction)
                ue.set_mixin_profile(self.ability, self.original_profile)
                self.report["original_fraction_restored"] = float(self.ability.EnableInputAfterTimeFraction) == self.original_fraction
                self.report["original_player_restored"] = capture(self.controller) == self.original_model and not self.ignored() and not self.immune() and self.effects() == 0
                self.report["original_ability_specs_restored"] = self.specs() == self.original_specs
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_SPAWN_EFFECT_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_SPAWN_EFFECT_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPSpawnEffectResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPSpawnEffectResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
