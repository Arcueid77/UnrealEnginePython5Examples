"""Actual ASC Melee activation/montage lifecycle, no fabricated damage or callbacks."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_helpers_validation import Validation as Ready, instances, specs
from .melee_hit_montage_mixin import CLASS
from . import melee_activation_mixin as policy
from .melee_activation_contract import TRIALS, require, validate
from .dash_local_direction_validation import restore_control

def path(value): return value.get_path_name() if valid(value) else None
def vector(value): return [float(value.x), float(value.y), float(value.z)]
def config(ability): return {name: float(ability.get_property(name)) for name in ("Distance", "Radius", "Half Height", "Strength", "Duration")}


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result); self.require_auto_active = False; self.cleaned = False; self.index = 0
        self.report = dict(schema_version=1, status="running", error=None, cases=[], full_acceptance=False, network_acceptance=False,
            packaged_runtime=False, physical_input_tested=False, activation_event_replayed=False, task_callbacks_replayed=False,
            ability_granted_by_fixture=False, health_or_raw_velocity_written=False, trace_damage_business_migrated=False,
            request_entry="ASC.TryActivateAbilityByClass", fixture_entries=["Actor.K2_TeleportTo", "Character.StopAnimMontage", "GameplayAbility.K2_CancelAbility", "ue.set_mixin_profile"])
    def begin(self):
        values = instances(self.asc, ue.load_class(CLASS)); require(len(values) == 1 and not values[0].get_property("bIsActive"), "one actual granted inactive Melee required")
        self.melee = values[0]; self.original = dict(profile=str(ue.get_mixin_profile(self.melee)), config=config(self.melee), specs=specs(self.asc),
            location=self.pawn.get_actor_location(), rotation=self.pawn.get_actor_rotation(), control=self.controller.call_function("GetControlRotation"))
        self.report.update(actual_ability_class=path(self.melee.get_class()), actual_granted_primary_instance=True,
            native_role=int(self.pawn.call_function("GetLocalRole")))
        self.enter("start")
    def healths(self):
        actors, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("Pawn")); rows = {}
        for actor in actors:
            component = actor.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if valid(component): rows[path(actor)] = dict(health=float(component.call_function("GetHealth")), death=int(component.call_function("GetDeathState")))
        return rows
    def equipment(self):
        manager = self.pawn.call_function("GetComponentByClass", ue.find_class("LyraEquipmentManagerComponent"))
        values = manager.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance"))
        require(values and values[0].is_a(ue.load_class(policy.WEAPON)), "actual native first equipped Melee weapon required")
        return dict(weapon=path(values[0]), montage=path(values[0].get_property("MeleeAttackMontage")))
    def tasks(self):
        values = [task for task in self.melee.get_property("ActiveTasks") if valid(task)]
        return dict(count=len(values), montage=any(task.is_a(ue.find_class("AbilityTask_PlayMontageAndWait")) for task in values),
            root=any(task.is_a(ue.find_class("AbilityTask_ApplyRootMotionConstantForce")) for task in values))
    def start(self):
        if self.melee.get_property("bIsActive") or self.melee.call_function("GetCooldownTimeRemaining") > 0: return
        moved = bool(self.pawn.call_function("K2_TeleportTo", self.original["location"], self.original["rotation"]))
        require(moved, "native Melee fixture pose reset refused")
        name, profile = TRIALS[self.index]; ue.set_mixin_profile(self.melee, profile)
        self.before = policy.instance_snapshot(self.melee); self.health_before = self.healths(); self.intervened = False
        self.row = dict(index=self.index, name=name, profile=profile, native_pose_reset=moved, equipment=self.equipment(),
            native_active_observed=False, native_montage_task_observed=False, native_root_task_observed=False, intervention=None)
        require(self.row["equipment"]["montage"] is not None, "actual equipped Melee montage missing")
        self.enter("settle")
    def request(self):
        self.row["native_request_accepted"] = bool(self.asc.call_function("TryActivateAbilityByClass", ue.load_class(CLASS), False))
        require(self.row["native_request_accepted"], "native Melee ASC request rejected")
        self.row["native_initial_montage"] = path(self.pawn.call_function("GetCurrentMontage"))
        self.row["native_repeat_rejected"] = self.asc.call_function("TryActivateAbilityByClass", ue.load_class(CLASS), False) is False
        self.game_started = self.game_time(); self.sample(); self.enter("observe")
    def sample(self):
        state = self.tasks(); self.row["native_active_observed"] |= bool(self.melee.get_property("bIsActive"))
        self.row["native_montage_task_observed"] |= state["montage"]; self.row["native_root_task_observed"] |= state["root"]
        require(self.healths() == self.health_before, "no-damage activation control hit an actual Pawn; do not reset Health")
    def observe(self):
        require(time.monotonic()-self.phase_started < 12., "native Melee montage/cleanup timeout")
        self.sample(); elapsed = self.game_time()-self.game_started
        if self.row["name"] != "natural" and not self.intervened and elapsed >= .07:
            require(self.melee.get_property("bIsActive") and self.tasks()["montage"], "native montage intervention missed active window")
            self.intervened = True; self.row["intervention"] = dict(active_before=True, time=elapsed)
            if self.row["name"] == "interrupt": self.pawn.call_function("StopAnimMontage")
            elif self.row["name"] == "cancel": self.melee.call_function("K2_CancelAbility")
            else:
                ue.set_mixin_profile(self.melee, "Python" if self.row["profile"] == "BlueprintFallback" else "BlueprintFallback")
                self.row["intervention"]["new_profile"] = str(ue.get_mixin_profile(self.melee))
            self.row["intervention"]["active_after"] = bool(self.melee.get_property("bIsActive"))
        if self.melee.get_property("bIsActive") or self.melee.call_function("GetCooldownTimeRemaining") > 0: return
        self.quiet_before = policy.instance_snapshot(self.melee); self.quiet_ticks = 0; self.enter("quiet")
    def quiet(self):
        require(policy.instance_snapshot(self.melee) == self.quiet_before and self.healths() == self.health_before, "late Melee callback or damage after End")
        self.quiet_ticks += 1
        if self.quiet_ticks < 20: return
        after = policy.instance_snapshot(self.melee)
        self.row.update(stats={key: after.get(key, 0)-self.before.get(key, 0) for key in set(after)|set(self.before)},
            native_ended=not bool(self.melee.get_property("bIsActive")), native_tasks_after=self.tasks()["count"], quiet_ticks=self.quiet_ticks,
            actual_scope_closed=getattr(self.melee, "_uep_melee_montage_scope", None) is None,
            all_pawn_health_unchanged=self.healths() == self.health_before, specs_unchanged=specs(self.asc) == self.original["specs"],
            config_unchanged=config(self.melee) == self.original["config"])
        self.report["cases"].append(copy.deepcopy(self.row)); self.index += 1
        if self.index == len(TRIALS): self.finish()
        else: self.enter("start")
    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "native Melee activation total timeout")
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "start": self.start()
            elif self.phase == "settle" and time.monotonic()-self.phase_started >= .5: self.request()
            elif self.phase == "observe": self.observe()
            elif self.phase == "quiet": self.quiet()
            self.report["phase"] = self.phase; self.write(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def cleanup(self):
        if self.cleaned: return
        if hasattr(self, "original"):
            ue.set_mixin_profile(self.melee, self.original["profile"])
            self.report.update(profile_restored=str(ue.get_mixin_profile(self.melee)) == self.original["profile"],
                specs_unchanged=specs(self.asc) == self.original["specs"], config_unchanged=config(self.melee) == self.original["config"],
                native_pose_restored=bool(self.pawn.call_function("K2_TeleportTo", self.original["location"], self.original["rotation"])),
                native_control_restoration=restore_control(self.controller, self.original["control"]))
        self.report["shutdown"] = policy.snapshot(); self.cleaned = True
    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_MELEE_ACTIVATION_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_MELEE_ACTIVATION_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPMeleeActivationResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
