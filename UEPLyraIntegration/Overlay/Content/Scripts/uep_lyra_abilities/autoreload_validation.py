"""Real equipment grant, native ammo fixture, EnhancedInput fire and original reload."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_network_bots import isolate_bots
from uep_lyra_weapon_input import aim_above_players, aim_snapshot
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_world.inventory_pad_network_state import capture, services
from uep_lyra_hud.weapon_validation_helpers import set_stat
from . import autoreload_mixin as policy
from .autoreload_contract import PLAN, WEAPONS, require, validate
from .reload_magazine_contract import WEAPONS as RELOAD_WEAPONS

CAPACITY = "Lyra.ShooterGame.Weapon.MagazineSize"


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.scope, self.sides = False, None, []
        self.timeout = 240.
        self.weapon = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoReloadWeapon=")), "pistol")
        require(self.weapon in WEAPONS, "weapon has no original AutoReload grant")
        self.report = dict(schema_version=2, weapon=self.weapon, status="running", error=None, cases=[], fixture_native_inventory_api_used=True,
            original_player_restored=False, original_ability_active_restored=False, native_default_python_loop_owned=False,
            observer_scopes_created=0, observer_scopes_closed=0)
        self.report.update({key: False for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "ammo_properties_written",
            "activation_handler_replayed", "task_callbacks_replayed", "reload_handler_called_by_probe", "poll_interval_or_idle_threshold_written")})
        self.statics = ue.find_class("GameplayStatics").get_cdo()

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))
    def ammo(self): return tuple(int(self.item.call_function("GetStatTagStackCount", GameplayTag(TagName=tag))) for tag in (policy.MAGAZINE, policy.SPARE))
    def tasks(self): return sum(valid(task) and task.is_a(ue.find_class("AbilityTask_WaitDelay")) for task in self.ability.get_property("ActiveTasks"))

    def reload_tag(self):
        return bool(ue.find_class("BlueprintGameplayTagLibrary").get_cdo().call_function(
            "DoesTagAssetInterfaceHaveTag", self.pawn, GameplayTag(TagName="Event.Movement.Reload")))

    def reload_active(self):
        return any(valid(value) and value.get_property("bIsActive") for spec in self.asc.get_property("ActivatableAbilities").Items
            if valid(spec.Ability) and "GA_Weapon_Reload" in spec.Ability.get_class().get_name()
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances))

    def inject(self, pressed):
        for name in ("IA_Weapon_Fire", "IA_Weapon_Fire_Auto"):
            action = ue.load_object(ue.find_class("InputAction"), "/Game/Input/Actions/"+name+"."+name)
            self.controller.inject_enhanced_input_for_action(action, pressed)
        if pressed: self.row["native_input_injections"] += 1

    def end_native(self):
        if valid(self.ability) and self.ability.get_property("bIsActive"): self.ability.call_function("K2_EndAbility")

    def close_observer(self):
        if self.scope is not None:
            self.scope.close(); self.scope = None; self.report["observer_scopes_closed"] += 1

    def set_ammo(self, values):
        if self.phase == "running" and self.name == "real-fire-auto-reload":
            self.row["ammo_api_calls_after_firing_began"] += 1
        for tag, value in zip((policy.MAGAZINE, policy.SPARE), values): set_stat(self.item, tag, value)

    def prepare_weapon(self, controller, model): return True

    def initial_ammo(self):
        return (0, self.capacity*2) if self.name == "empty-spare" else ((0, 0) if self.name == "empty-no-spare" else (self.capacity, self.capacity*2))

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
            if model is None or not self.prepare_weapon(controller, model): continue
            if RELOAD_WEAPONS[self.weapon][2] not in model["definition"]: continue
            self.world, self.bridge, self.controller, self.pawn = world, bridge, controller, controller.get_controlled_pawn()
            self.asc, self.cls = ability_system(self.pawn), ue.load_class(policy.CLASS)
            matches = [value for spec in self.asc.get_property("ActivatableAbilities").Items if valid(spec.Ability) and spec.Ability.get_class() == self.cls
                for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
            if len(matches) != 1: continue
            self.ability = matches[0]
            if not self.ability.get_property("bIsActive"): continue
            self.item = self.ability.call_function("GetAssociatedItem")
            if not valid(self.item): continue
            _, self.quickbar = services(controller)
            self.equipment = self.ability.call_function("GetAssociatedEquipment")
            require(valid(self.equipment) and self.equipment.call_function("GetInstigator") == self.item == self.quickbar.call_function("GetActiveSlotItem"),
                "native equipment/item SourceObject mismatch")
            self.capacity = int(self.item.call_function("GetStatTagStackCount", GameplayTag(TagName=CAPACITY)))
            require(self.capacity > 0, "native magazine capacity missing")
            self.original_ammo, self.original_model, self.original_aim = self.ammo(), model, aim_snapshot(controller)
            self.report.update(native_weapon_definition=model["definition"], magazine_capacity=self.capacity)
            self.report["native_default_python_loop_owned"] = (self.ability.get_path_name() in policy.snapshot()["active_abilities"] and
                str(ue.get_mixin_profile(self.ability)) == "Python" and self.tasks() == 1)
            require(self.report["native_default_python_loop_owned"], "native LocalOnly OnSpawn did not start Python WaitDelay")
            self.end_native(); aim_above_players(controller); self.begin(); return

    def begin(self):
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        self.end_native(); ue.set_mixin_profile(self.ability, self.profile)
        self.set_ammo(self.initial_ammo())
        self.before = policy.instance_snapshot(self.ability)
        self.row = dict(native_type_preserved=self.ability.get_class() == self.cls, native_equipment_item_source_matches=True,
            initial_ammo=list(self.ammo()),
            magazine_capacity=self.capacity, ammo_check=bool(self.ability.call_function("CheckAmmoState")), reload_event_deliveries=0,
            native_reload_active_observed=False, native_reload_tag_observed=False, real_fire_rounds=0, native_input_injections=0,
            ammo_api_calls_after_firing_began=0, profile_teardown_ended_native_ability=False)
        require(not self.reload_active() and not self.reload_tag(), "previous native Reload still active at AutoReload trial start")
        self.row["native_reload_observations"] = []
        require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native AutoReload activation refused")
        self.row["tasks_at_start"] = self.tasks()
        self.scope = SubscriptionScope(); self.report["observer_scopes_created"] += 1
        task = ue.find_class("AbilityTask_WaitGameplayEvent").get_cdo().call_function("WaitGameplayEvent", self.ability,
            GameplayTag(TagName="InputTag.Weapon.Reload"), None, False, True)
        def reloaded(payload): self.row["reload_event_deliveries"] += 1
        self.scope.bind_event(task, "EventReceived", reloaded); task.call_function("ReadyForActivation")
        self.trial_started, self.minimum_magazine = self.game_time(), self.capacity
        self.enter("running")

    def running(self):
        elapsed = self.game_time()-self.trial_started
        require(elapsed < 18., "native AutoReload case timeout: "+self.name)
        magazine, spare = self.ammo()
        observed = dict(ammo=[magazine, spare], active=self.reload_active(), tag=self.reload_tag())
        history = self.row["native_reload_observations"]
        if not history or any(history[-1][key] != value for key, value in observed.items()):
            if len(history) < 64: history.append(dict(observed, elapsed=elapsed, requests=self.row["reload_event_deliveries"]))
        self.row["native_reload_active_observed"] |= self.reload_active()
        self.row["native_reload_tag_observed"] |= self.reload_tag()
        if self.name == "real-fire-auto-reload":
            self.minimum_magazine = min(self.minimum_magazine, magazine)
            self.row["real_fire_rounds"] = self.capacity-self.minimum_magazine
            if self.minimum_magazine > 0:
                self.inject((time.monotonic()-self.phase_started) % .30 < .12)
                return
            self.inject(False)
        if self.name in ("empty-spare", "real-fire-auto-reload"):
            if not (self.row["native_reload_active_observed"] and magazine == self.capacity and not self.reload_active() and not self.reload_tag()): return
            self.row["ammo_conserved"] = magazine+spare == self.capacity*2 if self.name == "empty-spare" else magazine+spare == self.capacity*3-self.row["real_fire_rounds"]
        elif elapsed < max(float(self.ability.PollInterval)*3.2, .8): return
        if self.name == "native-cancel": self.ability.call_function("K2_CancelAbility")
        elif self.name == "active-profile-switch":
            ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
            self.row["profile_teardown_ended_native_ability"] = not self.ability.get_property("bIsActive")
        else: self.end_native()
        self.close_observer()
        self.row.update(final_magazine=magazine, final_spare=spare, tasks_after_end=self.tasks())
        self.at_end = policy.instance_snapshot(self.ability)
        self.enter("ended")

    def ended(self):
        if time.monotonic()-self.phase_started < float(self.ability.PollInterval)*2.2: return
        stats = policy.instance_snapshot(self.ability)
        self.row["no_callbacks_after_end"] = all(stats[key] == self.at_end[key] for key in ("polls", "tasks_created", "reload_requests"))
        self.row["counters"] = {key: value-self.before[key] for key, value in stats.items()}
        self.complete_trial()

    def complete_trial(self):
        self.set_ammo(self.original_ammo)
        self.row["fixture_ammo_restored"] = self.ammo() == self.original_ammo
        self.append_side()

    def append_side(self):
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_AUTORELOAD_CASE_OBSERVED "+self.name)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.begin()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < self.timeout, "native AutoReload total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "running": self.running()
            else: self.ended()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            self.close_observer()
            if hasattr(self, "ability"):
                self.inject(False); self.end_native()
                self.set_ammo(self.original_ammo)
                rotation = ue.FRotator()
                for field, value in self.original_aim.items(): setattr(rotation, field, value)
                self.controller.call_function("SetControlRotation", rotation)
                self.report["original_player_restored"] = capture(self.controller) == self.original_model and aim_snapshot(self.controller) == self.original_aim
                ue.set_mixin_profile(self.ability, "Python")
                require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native default AutoReload restore refused")
                self.report["original_ability_active_restored"] = bool(self.ability.get_property("bIsActive")) and self.tasks() == 1
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_AUTORELOAD_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def validate_report(self): validate(self.report)

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; self.validate_report()
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_AUTORELOAD_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPAutoReloadResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoReloadResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
