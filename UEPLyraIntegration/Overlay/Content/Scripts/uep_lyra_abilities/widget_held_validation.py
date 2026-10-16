"""Actual held scoreboards: original BP/Python UI, native input/state/end/GC.

Each actual Experience uses its existing grant and real EnhancedInput. No
Widget class/CDO is overwritten and no extra ability is granted by the probe.
"""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_world.inventory_pad_network_state import capture
from . import widget_held_mixin as policy
from .widget_held_contract import PLAN, CLASSES, WIDGETS, FALSE_CLAIMS, require, validate

SCORING = dict(tdm="/ShooterCore/Elimination/B_TeamDeathMatchScoring.B_TeamDeathMatchScoring_C",
               cp="/ShooterCore/ControlPoint/B_ControlPointScoring.B_ControlPointScoring_C")


def optional_object(path):
    try: return ue.find_object(path)
    except Exception as error:
        if str(error) == "unable to find object " + path: return None
        raise


def instances(asc, cls):
    return [value for spec in asc.get_property("ActivatableAbilities").Items
            if valid(spec.Ability) and spec.Ability.get_class() == cls
            for value in list(spec.NonReplicatedInstances) + list(spec.ReplicatedInstances) if valid(value)]


def cdos():
    return {name: dict(layer=str(ue.load_class(path).get_cdo().get_property("Layer Name").TagName),
                       policy=int(ue.load_class(path).get_cdo().get_property("NetExecutionPolicy")),
                       path=ue.load_class(path).get_cdo().call_function(policy.CLASS_PATH)) for name, path in CLASSES.items()}


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.paused, self.sides = False, False, []
        target = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPWidgetHeldTarget=")), "tdm")
        require(target in CLASSES, "unknown held-widget Experience target")
        self.targets, self.plan, self.timeout, self.safety = (target,), PLAN, 240., True
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(status="running", error=None, cases=[], safety_regressions=[],
            original_player_restored=False, original_profiles_restored=False, original_ability_specs_restored=False,
            original_cdos_untouched=False, native_layer_restored=False, targets=list(self.targets))
        self.report.update({field: False for field in FALSE_CLAIMS})

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def active(self): return bool(self.ability.get_property("bIsActive"))
    def tasks(self): return sum(valid(value) for value in self.ability.get_property("ActiveTasks"))
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))
    def layer_active(self): return self.layer.call_function("GetActiveWidget")
    def specs(self):
        return sorted(value.get_path_name() for spec in self.asc.get_property("ActivatableAbilities").Items
                      for value in list(spec.NonReplicatedInstances) + list(spec.ReplicatedInstances) if valid(value))
    def state(self):
        return dict(model=capture(self.controller), active=bool(self.abilities["tdm"].get_property("bIsActive")),
                    tasks=len(self.abilities["tdm"].get_property("ActiveTasks")),
                    menu_active=valid(self.layer_active()))

    def inject(self, pressed):
        self.controller.inject_enhanced_input_for_action(self.action, pressed)
        if pressed: self.row["input_injections"] += 1

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
            pawn = controller.get_controlled_pawn(); asc = ability_system(pawn)
            target = self.targets[0]
            values = instances(asc, ue.load_class(CLASSES[target]))
            if len(values) != 1 or values[0].get_property("bIsActive"): continue
            state = self.statics.call_function("GetGameState", world)
            scoring = state.get_component_by_type(ue.load_class(SCORING[target]))
            if not valid(scoring): continue
            layouts = [obj for obj in world.all_objects() if valid(obj) and obj.is_a(ue.find_class("PrimaryGameLayout"))
                       and obj.call_function("GetOwningPlayer") == controller]
            if len(layouts) != 1: continue
            # W_OverallUILayout's unchanged OnInitialized registers this exact
            # designer control under UI.Layer.GameMenu. Avoid converting its
            # native TMap<FGameplayTag, Widget*> to a Python dict (struct keys).
            menu = layouts[0].get_property("GameMenu_Stack")
            if not valid(menu): continue
            self.world, self.controller, self.pawn, self.asc, self.layer = world, controller, pawn, asc, menu
            self.original_model, self.original_specs, self.original_cdos = model, self.specs(), cdos()
            require(not valid(self.layer_active()), "do not remove preexisting GameMenu UI")
            self.abilities = {target: values[0]}
            self.original_profiles = {target: str(ue.get_mixin_profile(values[0]))}
            self.native_scoring_component = scoring.get_class().get_path_name()
            require(all(row["policy"] == 1 and row["layer"] == "UI.Layer.GameMenu" and row["path"] == WIDGETS[name]
                        for name, row in self.original_cdos.items()), "original LocalOnly/layer/soft targets differ")
            self.action = ue.load_object(ue.find_class("InputAction"), "/ShooterCore/Input/Actions/IA_ShowScoreboard.IA_ShowScoreboard")
            self.begin(); return

    def begin(self):
        pair = self.index // 2
        self.target, self.name = self.targets[pair // len(self.plan)], self.plan[pair % len(self.plan)]
        self.ability = self.abilities[self.target]
        self.profile = ("BlueprintFallback", "Python")[self.index % 2]
        require(not self.active() and not valid(self.layer_active()), "previous native held-widget not restored")
        ue.set_mixin_profile(self.ability, self.profile)
        self.before = policy.snapshot()
        self.row = dict(native_type_preserved=self.ability.get_class().get_path_name() == CLASSES[self.target],
            profile_selected=str(ue.get_mixin_profile(self.ability)) == self.profile,
            original_soft_class_path=self.ability.call_function(policy.CLASS_PATH),
            activation_source="existing-spec-enhanced-input", native_map=self.world.get_name(),
            native_scoring_component=self.native_scoring_component,
            input_injections=0, native_widget_activated=False, native_widget_owner_correct=False,
            native_widget_in_original_layer=False, native_widget_class=None, native_tasks_during=0,
            native_state_end_removed_while_active=False, profile_teardown_ended_ability=False,
            native_pause_observed=False, active_during_pause=False, native_widget_removed_during_pause=False,
            native_action_triggers_when_paused=bool(self.action.get_property("bTriggerWhenPaused")), paused_input_injections=0)
        self.widget = None
        self.enter("hold")

    def hold(self):
        require(time.monotonic() - self.phase_started < 12., "native held-widget input/push timeout")
        widget = self.ability.get_property("SpawnedWidget")
        if not self.active() or not valid(widget) or not widget.call_function("IsActivated"):
            self.inject(True); return
        self.widget = widget
        self.row.update(native_widget_activated=True, native_widget_class=widget.get_class().get_path_name(),
            native_widget_owner_correct=widget.call_function("GetOwningPlayer") == self.controller,
            native_widget_in_original_layer=self.layer_active() == widget, native_tasks_during=self.tasks())
        if time.monotonic() - self.phase_started < .35 or not self.may_finish_hold():
            self.inject(True); return
        # Do not enqueue a fresh pressed value in the frame that cancels/ends
        # the ability. EnhancedInput combines injections for that frame; adding
        # False cannot retract an already queued True and would reactivate it.
        if self.name == "native-cancel": self.ability.call_function("K2_CancelAbility")
        elif self.name == "external-native-end": self.ability.call_function("K2_EndAbility")
        elif self.name == "native-state-end":
            self.ability.call_function("EndAbilityState", "ShowWidget_WhenInputHeld")
            self.row["native_state_end_removed_while_active"] = self.active() and not valid(self.ability.get_property("SpawnedWidget")) and not widget.call_function("IsActivated")
        elif self.name == "active-profile-switch":
            ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
            self.row["profile_teardown_ended_ability"] = not self.active()
        elif self.name == "paused-world-time":
            self.inject(True)
            self.frozen_time = self.game_time()
            require(self.statics.call_function("SetGamePaused", self.world, True), "held-widget native pause refused")
            self.paused = True; self.enter("paused"); return
        self.inject(False); self.enter("ended")

    def may_finish_hold(self): return True

    def ended(self):
        self.inject(False)
        require(time.monotonic() - self.phase_started < 8., "native held-widget end/stack timeout")
        if self.active() or valid(self.layer_active()) or time.monotonic() - self.phase_started < .4: return
        self.row.update(ability_ended=True, native_tasks_after=self.tasks(), native_layer_restored=True,
            native_widget_removed=not valid(self.ability.get_property("SpawnedWidget")) and not self.widget.call_function("IsActivated"),
            player_restored=capture(self.controller) == self.original_model)
        self.at_end = policy.snapshot(); self.enter("settled")

    def settled(self):
        if time.monotonic() - self.phase_started < .25: return
        after = policy.snapshot()
        self.row.update(no_late_callbacks=after == self.at_end,
            counters={key: value - self.before[key] for key, value in after.items() if type(value) is int and key != "active_count"})
        self.complete_trial()

    def complete_trial(self):
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(target=self.target, name=self.name, blueprint=self.sides[0], python=self.sides[1]))
            self.sides = []
            ue.log("UEP_WIDGET_HELD_CASE_OBSERVED " + self.target + "/" + self.name)
        self.index += 1
        if self.index < len(self.targets) * len(self.plan) * 2: self.begin()
        elif self.safety: self.safety_index = 0; self.start_safety()
        else: self.finish()

    def start_safety(self):
        self.target = self.targets[0]
        self.ability = self.abilities[self.target]
        ue.set_mixin_profile(self.ability, "Python")
        self.before = policy.snapshot()
        self.row = dict(name=("cancel-pending", "repeat-pending", "profile-switch-pending")[self.safety_index],
            direct_native_asc_activation_fixture=True, bp_parity_claimed=False, input_injections=0)
        require(self.asc.call_function("TryActivateAbilityByClass", ue.load_class(CLASSES[self.target]), False), "native pending fixture activation refused")
        action = self.ability.get_property("Async Action")
        self.row["native_pending_observed"] = valid(action) and not valid(self.ability.get_property("SpawnedWidget"))
        require(self.row["native_pending_observed"], "no real asynchronous pending window observed")
        self.pending_path = action.get_path_name()
        action = None
        if self.row["name"] == "repeat-pending":
            self.ability.call_function("CreateAndDisplayWidget")
            require(policy.snapshot()["pending_cancelled"] == self.before["pending_cancelled"] + 1,
                    "public repeated Create did not cancel previous owned pending action")
            self.enter("safety-push")
        else:
            if self.row["name"] == "cancel-pending": self.ability.call_function("K2_CancelAbility")
            else: ue.set_mixin_profile(self.ability, "BlueprintFallback")
            self.enter("safety-ended")

    def safety_tick(self):
        require(time.monotonic() - self.phase_started < 8., "held-widget native pending lifetime timeout")
        if self.phase == "safety-push":
            widget = self.ability.get_property("SpawnedWidget")
            if not valid(widget) or not widget.call_function("IsActivated"): return
            self.ability.call_function("K2_EndAbility"); self.enter("safety-ended"); return
        if self.phase == "safety-ended":
            self.inject(False)
            if self.active() or valid(self.layer_active()) or time.monotonic() - self.phase_started < .4: return
            self.row.update(ability_ended=True, native_layer_restored=True,
                pending_references_cleared=not valid(self.ability.get_property("Async Action")) and not valid(self.ability.get_property("SpawnedWidget")))
            self.at_end = policy.snapshot()
            ue.find_class("KismetSystemLibrary").get_cdo().call_function("CollectGarbage")
            self.enter("safety-gc"); return
        if time.monotonic() - self.phase_started < .35: return
        after = policy.snapshot()
        self.row.update(no_late_callbacks=after == self.at_end, pending_proxy_collected=optional_object(self.pending_path) is None,
            owned_scopes_balanced=after["scopes_created"] - self.before["scopes_created"] == after["scopes_closed"] - self.before["scopes_closed"])
        self.report["safety_regressions"].append(copy.deepcopy(self.row)); self.safety_index += 1
        if self.safety_index == 3: self.finish()
        else: self.start_safety()

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < self.timeout, "held-widget total timeout: " + self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "hold": self.hold()
            elif self.phase == "ended": self.ended()
            elif self.phase == "settled": self.settled()
            elif self.phase.startswith("safety-"): self.safety_tick()
            elif self.phase == "paused":
                if time.monotonic() - self.phase_started <= .3:
                    self.inject(True); self.row["paused_input_injections"] += 1
                else:
                    # IA_ShowScoreboard does not trigger when paused. Native
                    # EnhancedInput invalidates even a continuously injected
                    # held value, delivering release -> native WaitInputRelease.
                    self.row.update(native_pause_observed=self.game_time() == self.frozen_time,
                        active_during_pause=self.active(), native_widget_removed_during_pause=(
                            not valid(self.ability.get_property("SpawnedWidget")) and
                            not self.widget.call_function("IsActivated") and not valid(self.layer_active())))
                    require(self.statics.call_function("SetGamePaused", self.world, False), "held-widget unpause refused")
                    self.paused = False; self.inject(False); self.enter("ended")
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            if hasattr(self, "abilities"):
                for target, ability in self.abilities.items():
                    self.target, self.ability = target, ability
                    if hasattr(self, "row"): self.inject(False)
                    if self.active(): ability.call_function("K2_EndAbility")
                    ue.set_mixin_profile(ability, self.original_profiles[target])
                self.report["original_profiles_restored"] = all(str(ue.get_mixin_profile(ability)) == self.original_profiles[name]
                                                                for name, ability in self.abilities.items())
                self.report.update(original_ability_specs_restored=self.specs() == self.original_specs,
                    original_player_restored=capture(self.controller) == self.original_model,
                    original_cdos_untouched=cdos() == self.original_cdos, native_layer_restored=not valid(self.layer_active()))
        except Exception: error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_WIDGET_HELD_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report, self.targets, self.plan, self.safety)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_WIDGET_HELD_SHUTDOWN_" + self.report["status"].upper())


if any(value.startswith("-UEPWidgetHeldResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPWidgetHeldResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
