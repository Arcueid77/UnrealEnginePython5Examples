"""Native GAS grant/activate/input, original montage and original healing GE."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayEffectQuery
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from . import hero_heal_mixin as policy
from .hero_heal_contract import PLAN, require, validate

INPUT_ID = 9231


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.grant, self.sides, self.paused = False, None, [], False
        self.health_commands = 0
        self.plan, self.timeout = PLAN, 240.
        self.foreign_index, self.foreign_lock_owned, self.foreign_done = 0, False, False
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(status="running", error=None, cases=[], original_player_restored=False,
            original_ability_specs_restored=False, fixture_native_asc_grant_activate_and_input_api=True, foreign_lock_regressions=[])
        for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_or_enhanced_input_tested",
            "activation_handler_replayed", "task_callbacks_replayed", "health_properties_written", "animation_assets_modified", "original_montage_or_effect_written"):
            self.report[field] = False

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))
    def health(self): return float(self.health_component.call_function("GetHealth"))
    def ignored(self): return bool(self.controller.call_function("IsMoveInputIgnored"))
    def tasks(self): return sum(valid(task) for task in self.ability.get_property("ActiveTasks"))
    def effects(self): return len(self.asc.call_function("GetActiveEffects", GameplayEffectQuery(EffectDefinition=self.ability.GE_Heal)))
    def specs(self): return sorted(value.get_path_name() for spec in self.asc.get_property("ActivatableAbilities").Items
        for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value))

    def set_health(self, value):
        delta = value-self.health()
        if abs(delta) > .01:
            self.health_commands += 1
            applied = self.bridge.call_function("ApplyAuthorityHealthDelta", "hero-heal."+str(self.health_commands), delta)
            require(applied.bApplied and abs(applied.HealthAfter-value) < .01,
                "bounded authority Hero Heal health fixture refused: "+str(applied.Status))

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bHealthReady and not snap.bDamageImmune and snap.Health > 0): continue
            controller = self.statics.call_function("GetPlayerController", world, 0)
            model = capture(controller)
            if model is None or "ID_Pistol" not in model["definition"]: continue
            self.world, self.bridge, self.controller, self.pawn = world, bridge, controller, controller.get_controlled_pawn()
            self.asc, self.cls = ability_system(self.pawn), ue.load_class(policy.CLASS)
            require(not self.ignored(), "original controller already ignores movement")
            require(not any(spec.InputID == INPUT_ID for spec in self.asc.get_property("ActivatableAbilities").Items), "Hero Heal fixture input ID collision")
            require(not any(valid(spec.Ability) and spec.Ability.get_class() == self.cls for spec in self.asc.get_property("ActivatableAbilities").Items), "do not replace an existing Hero Heal spec")
            self.health_component = self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            self.original_health, self.original_model, self.original_specs = self.health(), model, self.specs()
            self.enter("grant"); self.grant_ability(); return

    def grant_ability(self):
        self.grant = self.asc.call_function("K2_GiveAbility", self.cls, 1, INPUT_ID)
        self.attach_ability()

    def attach_ability(self):
        values = [value for spec in self.asc.get_property("ActivatableAbilities").Items
            if valid(spec.Ability) and spec.Ability.get_class() == self.cls
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
        require(len(values) == 1, "native GAS grant did not create one Hero Heal instance")
        self.ability, self.anim = values[0], self.pawn.Mesh.call_function("GetAnimInstance")
        self.original_effects = self.effects()
        require(self.original_effects == 0, "do not remove a preexisting instance of the same native healing effect")
        self.report.update(original_montage=self.ability.HealMontage.get_path_name(), original_effect=self.ability.GE_Heal.get_path_name(),
            native_effect_duration_policy=int(self.ability.GE_Heal.get_cdo().DurationPolicy))
        self.begin()

    def begin(self):
        self.name, self.profile = self.plan[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        require(not self.ability.get_property("bIsActive"), "previous Hero Heal activation still active")
        ue.set_mixin_profile(self.ability, self.profile)
        self.set_health(75.)
        self.before, self.trial_started = policy.snapshot(), self.game_time()
        self.row = dict(native_type_preserved=self.ability.get_class() == self.cls, health_before=self.health(),
            max_health=float(self.health_component.call_function("GetMaxHealth")), native_input_press_sent=False,
            profile_teardown_ended_ability=False, native_state_end_released_effects_while_active=False,
            native_pause_observed=False, original_montage_playing_observed=False)
        self.action_done = False
        require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native GAS Hero Heal activation refused")
        self.row.update(native_tasks_at_start=self.tasks(), movement_locked_at_start=self.ignored())
        self.enter("running")

    def may_perform_action(self): return True

    def running(self):
        elapsed = self.game_time()-self.trial_started
        active = bool(self.ability.get_property("bIsActive"))
        self.row["original_montage_playing_observed"] |= bool(self.anim.call_function("Montage_IsPlaying", self.ability.HealMontage))
        if active and elapsed > .06 and not self.action_done and self.name != "original-montage" and self.may_perform_action():
            self.action_done = True
            if self.name == "native-input-press":
                self.asc.call_function("PressInputID", INPUT_ID); self.row["native_input_press_sent"] = True
                self.asc.call_function("ReleaseInputID", INPUT_ID)
            elif self.name == "native-cancel": self.ability.call_function("K2_CancelAbility")
            elif self.name == "native-interrupt": self.anim.call_function("Montage_Stop", 0., self.ability.HealMontage)
            elif self.name == "external-native-end": self.ability.call_function("K2_EndAbility")
            elif self.name == "active-profile-switch":
                ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
                self.row["profile_teardown_ended_ability"] = not self.ability.get_property("bIsActive")
            elif self.name == "native-state-end":
                self.ability.call_function("EndAbilityState", "HealAbility")
                self.row["native_state_end_released_movement_while_active"] = bool(self.ability.get_property("bIsActive") and not self.ignored())
                self.row["native_state_end_released_effects_while_active"] = (self.row["native_state_end_released_movement_while_active"] and self.effects() == self.original_effects)
            elif self.name == "paused-world-time":
                self.frozen_time = self.game_time()
                require(self.statics.call_function("SetGamePaused", self.world, True), "Hero Heal pause refused")
                self.paused = True; self.enter("paused")
            return
        if active:
            require(elapsed < 8., "native Hero Heal did not end: "+self.name); return
        self.row.update(health_after=self.health(), tasks_after_end=self.tasks(), native_ability_ended=True,
            movement_unlocked_after_end=not self.ignored(), native_montage_stopped=not self.anim.call_function("Montage_IsPlaying", self.ability.HealMontage),
            native_heal_effects_restored=self.effects() == self.original_effects)
        self.at_end = policy.snapshot(); self.enter("ended")

    def ended(self):
        if time.monotonic()-self.phase_started < .35: return
        after = policy.snapshot()
        self.row["no_late_callbacks"] = after == self.at_end
        self.row["counters"] = {key: value-self.before[key] for key, value in after.items() if type(value) is int and key != "active_count"}
        self.complete_trial()

    def complete_trial(self):
        self.set_health(self.original_health)
        self.row["fixture_health_restored"] = self.health() == self.original_health
        self.append_side()

    def append_side(self):
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_HERO_HEAL_CASE_OBSERVED "+self.name)
        self.index += 1
        if self.index == len(self.plan)*2: self.finish()
        else: self.begin()

    def begin_foreign_lock(self):
        require(not self.ignored() and not self.ability.get_property("bIsActive"), "foreign-lock regression baseline not clean")
        self.foreign_name = ("montage-end", "state-end", "profile-teardown")[self.foreign_index]
        ue.set_mixin_profile(self.ability, "Python"); self.set_health(75.)
        self.controller.call_function("SetIgnoreMoveInput", True); self.foreign_lock_owned = True
        self.foreign_before, self.foreign_started, self.foreign_action = policy.snapshot(), self.game_time(), False
        self.foreign_row = dict(name=self.foreign_name, external_lock_added_with_native_api=self.ignored(),
            external_lock_preserved_after_native_end=False, external_lock_released_once_restores_baseline=False,
            state_cleanup_preserved_external_lock=False)
        require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native foreign-lock Hero Heal activation refused")
        self.enter("foreign-running")

    def foreign_tick(self):
        active = bool(self.ability.get_property("bIsActive"))
        if self.phase == "foreign-running":
            elapsed = self.game_time()-self.foreign_started
            require(elapsed < 8., "foreign-lock native Hero Heal end timeout")
            if active:
                if elapsed > .06 and not self.foreign_action and self.foreign_name != "montage-end":
                    self.foreign_action = True
                    if self.foreign_name == "state-end":
                        self.ability.call_function("EndAbilityState", "HealAbility")
                        self.foreign_row["state_cleanup_preserved_external_lock"] = bool(self.ability.get_property("bIsActive") and self.ignored())
                    else: ue.set_mixin_profile(self.ability, "BlueprintFallback")
                return
            self.foreign_row.update(external_lock_preserved_after_native_end=self.ignored(), tasks_after_end=self.tasks(),
                effects_after_end=self.effects(), health_after=self.health())
            self.foreign_at_end = policy.snapshot(); self.enter("foreign-ended"); return
        if time.monotonic()-self.phase_started < .35: return
        after = policy.snapshot()
        self.foreign_row["no_late_callbacks"] = after == self.foreign_at_end
        self.foreign_row["counters"] = {key: value-self.foreign_before[key] for key, value in after.items() if type(value) is int and key != "active_count"}
        self.controller.call_function("SetIgnoreMoveInput", False); self.foreign_lock_owned = False
        self.foreign_row["external_lock_released_once_restores_baseline"] = not self.ignored()
        self.set_health(self.original_health)
        self.report["foreign_lock_regressions"].append(copy.deepcopy(self.foreign_row))
        ue.log("UEP_HERO_HEAL_FOREIGN_LOCK_OBSERVED "+self.foreign_name)
        self.foreign_index += 1
        if self.foreign_index == 3: self.foreign_done = True; self.finish()
        else: self.begin_foreign_lock()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < self.timeout, "native Hero Heal total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "grant": self.grant_ability()
            elif self.phase == "running": self.running()
            elif self.phase == "ended": self.ended()
            elif self.phase.startswith("foreign-"): self.foreign_tick()
            elif time.monotonic()-self.phase_started > .3:
                self.row["native_pause_observed"] = self.game_time() == self.frozen_time and self.ability.get_property("bIsActive")
                require(self.statics.call_function("SetGamePaused", self.world, False), "Hero Heal unpause refused")
                self.paused = False; self.enter("running")
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        if not error and not getattr(self, "network_fixture", False) and not self.foreign_done:
            self.begin_foreign_lock(); return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            if self.grant is not None:
                if valid(getattr(self, "ability", None)) and self.ability.get_property("bIsActive"): self.ability.call_function("K2_EndAbility")
                if self.foreign_lock_owned:
                    self.controller.call_function("SetIgnoreMoveInput", False); self.foreign_lock_owned = False
                self.asc.call_function("ClearAbility", self.grant); self.grant = None
                self.set_health(self.original_health)
                self.report["original_player_restored"] = (capture(self.controller) == self.original_model and self.health() == self.original_health and not self.ignored())
                self.report["original_ability_specs_restored"] = self.specs() == self.original_specs
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_HERO_HEAL_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report, self.plan, network=getattr(self, "network_fixture", False))
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_HERO_HEAL_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPHeroHealResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPHeroHealResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
