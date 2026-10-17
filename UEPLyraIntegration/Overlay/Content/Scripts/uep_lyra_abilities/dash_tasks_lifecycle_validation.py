"""Real pause/interruption/cancel/Profile teardown, never task-callback replay."""
import atexit
import copy
import sys
import time
import unreal_engine as ue
from .dash_tasks_validation import Validation as Tasks
from .dash_rpc_input_network_validation import task_state
from .dash_activation_mixin import evidence as activation_evidence
from .dash_rpc_input_network_validation import delta
from .dash_tasks_lifecycle_contract import TRIALS, validate, require


class Validation(Tasks):
    marker = "UEP_DASH_TASKS_LIFECYCLE"
    def __init__(self, result):
        super().__init__(result); self.plan = TRIALS; self.paused = False
        self.report.update(lifecycle_interventions_declared=True, frame_times_observed=True,
            fixture_native_entries=["GameplayStatics.SetGamePaused", "Character.StopAnimMontage", "GameplayAbility.K2_CancelAbility", "ue.set_mixin_profile"])
    def intent_name(self): return "forward"
    def trial_begin_evidence(self):
        super().trial_begin_evidence()
        self.row["lifecycle"] = dict(samples=[], intervention=None, pause=None, quiet_unchanged=True)
        self.intervened = False; self.quiet_lifecycle = None
    def sample(self):
        super().sample(); ability = self.current["ability"]
        value = self.row["lifecycle"]; now = self.game_time()
        if not value["samples"]:
            after = copy.deepcopy(activation_evidence(ability))
            value["activation_at_start"] = dict(counters=delta(after, self.activation_before), last=after["last"] if self.row["profile"] == "Python" else None)
        tasks = task_state(ability)
        row = dict(time=now, active=bool(ability.get_property("bIsActive")), root=tasks["root"], montage=tasks["montage"], tasks=tasks["count"])
        if not value["samples"] or value["samples"][-1] != row: value["samples"].append(row)
    def observe(self):
        self.sample(); ability = self.current["ability"]; life = self.row["lifecycle"]; state = life["samples"][-1]
        name = self.row["name"]; elapsed = state["time"]-life["samples"][0]["time"]
        if self.paused:
            pause = life["pause"]
            require(abs(self.game_time()-pause["time"]) <= .000001 and task_state(ability) == pause["tasks"] and ability.get_property("bIsActive"), "native task or game time advanced during pause")
            pause["ticks"] += 1
            if time.monotonic()-self.pause_wall >= .3 and pause["ticks"] >= 3:
                require(self.statics.call_function("SetGamePaused", self.world, False), "native unpause refused")
                pause.update(unpaused=True, wall_seconds=time.monotonic()-self.pause_wall); self.paused = False
            return
        ready = (state["root"] and elapsed >= .07) if name != "pause-delay" else (not state["root"] and state["active"])
        if not self.intervened and ready:
            self.intervened = True
            life["intervention"] = dict(time=self.game_time(), active_before=state["active"], root_before=state["root"], native_entry=None)
            action = life["intervention"]
            if name in ("pause-root", "pause-delay"):
                action["native_entry"] = "GameplayStatics.SetGamePaused"
                require(self.statics.call_function("SetGamePaused", self.world, True), "native pause refused")
                self.paused, self.pause_wall = True, time.monotonic()
                life["pause"] = dict(time=self.game_time(), tasks=task_state(ability), ticks=0, unpaused=False)
                return
            if name == "montage-interrupt":
                action["native_entry"] = "Character.StopAnimMontage"
                self.current["pawn"].call_function("StopAnimMontage", ability.get_property("Montage"))
            elif name == "native-cancel":
                action["native_entry"] = "GameplayAbility.K2_CancelAbility"; ability.call_function("K2_CancelAbility")
            elif name == "profile-switch-active":
                action["native_entry"] = "ue.set_mixin_profile"
                switched = "Python" if self.row["profile"] == "BlueprintFallback" else "BlueprintFallback"
                ue.set_mixin_profile(ability, switched); action["new_profile"] = str(ue.get_mixin_profile(ability))
            else: raise RuntimeError("unknown native intervention")
            action["active_after"] = bool(ability.get_property("bIsActive"))
        super().observe()
    def quiet(self):
        now = self.producer.finish()
        if self.quiet_lifecycle is None: self.quiet_lifecycle = copy.deepcopy(now)
        require(now == self.quiet_lifecycle, "late task/producer work after native lifecycle intervention")
        super().quiet()
    def cleanup(self):
        if self.paused:
            self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
        super().cleanup()
    def validate_report(self): return validate(self.report)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPDashTasksLifecycleResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
