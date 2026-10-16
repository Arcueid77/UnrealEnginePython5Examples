"""Real Inventory Experience input, original/Python pairs, pending GC/isolation."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from . import widget_pressed_mixin as policy
from .widget_pressed_context_validation import Validation as Context
from .widget_held_validation import optional_object
from .widget_pressed_contract import PLAN, TARGETS, FALSE_CLAIMS, CLASSES, WIDGETS, require, validate
from uep_lyra_world.effect_pad_mixin import valid


class Validation(Context):
    def __init__(self, result):
        super().__init__(result)
        self.plan, self.extras, self.timeout, self.paused = PLAN, True, 240., False
        self.scope, self.sides, self.original_profiles = None, [], None
        self.report = dict(status="running", error=None, cases=[], pending_regressions=[], mixed_profiles=[], last_readiness="native existing grants/input/layout",
            original_specs_restored=False, original_profiles_restored=False, original_cdos_preserved=False, native_layer_restored=False,
            fixture_observers_closed=False, fixture_scopes_created=0, fixture_scopes_closed=0)
        self.report.update({key: False for key in FALSE_CLAIMS})

    def cdo_state(self):
        return {target: dict(path=ue.load_class(path).get_cdo().call_function(policy.CLASS_PATH),
            profile=str(ue.load_class(path).get_cdo().get_property("PythonMixinProfile")),
            net=int(ue.load_class(path).get_cdo().get_property("NetExecutionPolicy"))) for target, path in CLASSES.items()}

    def active(self): return any(value.get_property("bIsActive") for value in self.current_abilities)
    def tasks(self): return sum(len(value.get_property("ActiveTasks")) for value in self.current_abilities)
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))
    def counts(self): return {key: value - self.before[key] for key, value in policy.snapshot().items() if type(value) is int and key != "active_count"}
    def close_observer(self):
        if self.scope is not None:
            self.scope.close(); self.scope = None; self.report["fixture_scopes_closed"] += 1

    def begin(self):
        if self.original_profiles is None:
            self.original_profiles = {value.get_path_name(): str(ue.get_mixin_profile(value)) for values in self.abilities.values() for value in values}
            self.original_cdos = self.cdo_state()
        pair = self.index // 2
        self.target, self.name = TARGETS[pair // len(self.plan)], self.plan[pair % len(self.plan)]
        self.current_abilities, self.profile = self.abilities[self.target], ("BlueprintFallback", "Python")[self.index % 2]
        require(not self.active() and not valid(self.active_layer()), "previous pressed-widget UI/ability still active")
        for ability in self.current_abilities: ue.set_mixin_profile(ability, self.profile)
        self.before = policy.snapshot()
        suffix = "Inventory" if self.target == "inventory" else "Map"
        self.action = ue.load_object(ue.find_class("InputAction"), "/ShooterExplorer/Input/Actions/IA_Toggle" + suffix + ".IA_Toggle" + suffix)
        self.row = dict(native_type_preserved=all(value.get_class().get_path_name() == CLASSES[self.target] for value in self.current_abilities),
            profile_selected=all(str(ue.get_mixin_profile(value)) == self.profile for value in self.current_abilities),
            original_config_preserved=all(value.call_function(policy.CLASS_PATH) == WIDGETS[self.target] and int(value.get_property("NetExecutionPolicy")) == 1 for value in self.current_abilities),
            native_instance_count=len(self.current_abilities), input_injections=0, foreign_native_events=0,
            ordinary_end_preserved_native_ui=False, profile_teardown_ended_all=False, inactive_handoff_kept_ui=False,
            native_pause_observed=False, native_ui_active_during_pause=False)
        self.inject(True); self.enter("open")

    def opened(self):
        self.inject(False)
        require(time.monotonic() - self.phase_started < 12., "pressed native input/UI timeout")
        widget = self.active_layer()
        if not valid(widget) or widget.get_class().get_path_name() != WIDGETS[self.target] or not widget.call_function("IsActivated"): return
        if any(valid(value.get_property(policy.PENDING)) for value in self.current_abilities): return
        if time.monotonic() - self.phase_started < .3: return
        self.widget = widget
        self.row.update(native_widget_active=True, widget_class=widget.get_class().get_path_name(), native_original_layer=True,
            native_widget_owner=widget.call_function("GetOwningPlayer") == self.controller,
            native_tasks_during=self.tasks(), release_kept_ui=self.active() and widget.call_function("IsActivated"))
        if self.scope is None:
            self.scope = SubscriptionScope(); self.report["fixture_scopes_created"] += 1
            self.scope.bind_event(widget, "BP_OnWidgetDeactivated", lambda: self.row.__setitem__("foreign_native_events", self.row["foreign_native_events"] + 1))
        if not self.may_finish_open(): return
        if self.name == "paused-world-time":
            self.frozen_time = self.game_time()
            require(self.statics.call_function("SetGamePaused", self.world, True), "native pressed-widget pause refused")
            self.paused = True; self.enter("paused"); return
        self.perform_action()

    def may_finish_open(self): return True

    def perform_action(self):
        if self.name in ("native-cancel", "external-native-end", "inactive-profile-switch"):
            for ability in self.current_abilities:
                if ability.get_property("bIsActive"): ability.call_function("K2_CancelAbility" if self.name == "native-cancel" else "K2_EndAbility")
            self.row["ordinary_end_preserved_native_ui"] = not self.active() and self.widget.call_function("IsActivated") and self.active_layer() == self.widget
            if self.name == "inactive-profile-switch":
                for ability in self.current_abilities: ue.set_mixin_profile(ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
                self.row["inactive_handoff_kept_ui"] = self.widget.call_function("IsActivated") and self.active_layer() == self.widget
        elif self.name == "active-profile-switch":
            for ability in self.current_abilities: ue.set_mixin_profile(ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
            self.row["profile_teardown_ended_all"] = not self.active()
        if self.widget.call_function("IsActivated"): self.widget.call_function("DeactivateWidget")
        self.enter("closed")

    def closed(self):
        self.inject(False)
        require(time.monotonic() - self.phase_started < 8., "pressed native close/end/layer timeout")
        widget = self.active_layer()
        if valid(widget) and widget.call_function("IsActivated"): widget.call_function("DeactivateWidget")
        if self.active() or valid(self.active_layer()) or time.monotonic() - self.phase_started < .4: return
        self.row.update(native_ability_ended=True, layer_restored=True, specs_preserved=self.specs() == self.original_specs,
            native_tasks_after=self.tasks(), foreign_listener_preserved=self.row["foreign_native_events"] >= 1)
        self.at_end = policy.snapshot(); self.enter("settled")

    def settled(self):
        if time.monotonic() - self.phase_started < .25: return
        self.row.update(no_late_callbacks=policy.snapshot() == self.at_end, counters=self.counts())
        self.close_observer(); self.complete_trial()

    def complete_trial(self):
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(target=self.target, name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_WIDGET_PRESSED_CASE_OBSERVED " + self.target + "/" + self.name)
        self.index += 1
        if self.index < len(TARGETS) * len(self.plan) * 2: self.begin()
        elif self.extras: self.extra_index = 0; self.start_extra()
        else: self.finish()

    def handles(self):
        rows = [(spec.Handle, value) for spec in self.asc.get_property("ActivatableAbilities").Items
                if valid(spec.Ability) and spec.Ability.get_class().get_path_name() == CLASSES[self.target]
                for value in list(spec.NonReplicatedInstances) + list(spec.ReplicatedInstances) if valid(value)]
        require(len(rows) == 2, "existing original duplicate spec handles changed")
        return sorted(rows, key=lambda row: row[1].get_path_name())

    def start_extra(self):
        self.target = TARGETS[self.extra_index // 5]
        self.current_abilities = self.abilities[self.target]
        for ability in self.current_abilities: ue.set_mixin_profile(ability, "Python")
        self.before, self.rows = policy.snapshot(), self.handles()
        position = self.extra_index % 5
        self.extra = dict(target=self.target, native_asc_handle_activation_fixture=True, bp_parity_claimed=False)
        if position >= 3:
            self.extra["order"] = position - 3
            profiles = ("Python", "BlueprintFallback") if position == 3 else ("BlueprintFallback", "Python")
            for (_, ability), profile in zip(self.rows, profiles): ue.set_mixin_profile(ability, profile)
            self.extra["profiles_independent"] = [str(ue.get_mixin_profile(value)) for _, value in self.rows] == list(profiles)
            self.extra["native_type_preserved"] = all(value.get_class().get_path_name() == CLASSES[self.target] for _, value in self.rows)
            for handle, _ in self.rows: require(self.asc.call_function("TryActivateAbility", handle, False), "native mixed-profile spec activation refused")
            self.enter("extra-mixed-open"); return
        self.extra["name"] = ("cancel-pending", "profile-switch-pending", "other-spec-pending")[position]
        handle, ability = self.rows[0]
        require(self.asc.call_function("TryActivateAbility", handle, False), "native pending spec activation refused")
        action = ability.get_property(policy.PENDING)
        self.extra["native_pending_observed"] = valid(action) and not valid(ability.get_property(policy.WIDGET))
        require(self.extra["native_pending_observed"], "real pressed-widget pending window not observed")
        self.pending_path = action.get_path_name(); action = None
        if position == 1: ue.set_mixin_profile(ability, "BlueprintFallback")
        else:
            if position == 2: require(self.asc.call_function("TryActivateAbility", self.rows[1][0], False), "second existing spec activation refused")
            ability.call_function("K2_CancelAbility")
        self.enter("extra-pending-open" if position == 2 else "extra-ended")

    def extra_tick(self):
        require(time.monotonic() - self.phase_started < 8., "pressed-widget native extra lifetime timeout")
        if self.phase.endswith("-open"):
            widget = self.active_layer()
            if not valid(widget) or not widget.call_function("IsActivated") or time.monotonic() - self.phase_started < .25: return
            if self.phase == "extra-mixed-open": self.extra["native_ui_observed"] = widget.get_class().get_path_name() == WIDGETS[self.target]
            else: require(not self.rows[0][1].get_property("bIsActive") and self.rows[1][1].get_property("bIsActive"), "canceling one pending spec affected the other")
            widget.call_function("DeactivateWidget"); self.enter("extra-ended"); return
        widget = self.active_layer()
        if valid(widget) and widget.call_function("IsActivated"): widget.call_function("DeactivateWidget")
        if self.active() or valid(self.active_layer()) or time.monotonic() - self.phase_started < .4: return
        if self.phase == "extra-ended":
            self.at_end = policy.snapshot()
            ue.find_class("KismetSystemLibrary").get_cdo().call_function("CollectGarbage")
            self.enter("extra-gc"); return
        if time.monotonic() - self.phase_started < .3: return
        counts = self.counts()
        if "order" in self.extra:
            self.extra.update(native_layer_restored=True, scopes_balanced=counts["scopes_created"] == counts["scopes_closed"], counters=counts)
            self.report["mixed_profiles"].append(copy.deepcopy(self.extra))
        else:
            self.extra.update(native_scopes_balanced=counts["scopes_created"] == counts["scopes_closed"], native_layer_restored=True,
                native_abilities_ended=not self.active(), no_late_callbacks=policy.snapshot() == self.at_end,
                native_pending_proxy_collected=optional_object(self.pending_path) is None)
            self.report["pending_regressions"].append(copy.deepcopy(self.extra))
        self.extra_index += 1
        if self.extra_index == len(TARGETS) * 5: self.finish()
        else: self.start_extra()

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < self.timeout, "pressed-widget total timeout: " + self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "open": self.opened()
            elif self.phase == "closed": self.closed()
            elif self.phase == "settled": self.settled()
            elif self.phase.startswith("extra-"): self.extra_tick()
            elif self.phase == "paused" and time.monotonic() - self.phase_started > .3:
                self.row.update(native_pause_observed=self.game_time() == self.frozen_time,
                    native_ui_active_during_pause=self.active() and self.widget.call_function("IsActivated"))
                require(self.statics.call_function("SetGamePaused", self.world, False), "pressed-widget unpause refused")
                self.paused = False; self.perform_action()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            if hasattr(self, "action"): self.inject(False)
            if hasattr(self, "abilities"):
                for values in self.abilities.values():
                    for ability in values:
                        if ability.get_property("bIsActive"): ability.call_function("K2_EndAbility")
                        ue.set_mixin_profile(ability, self.original_profiles[ability.get_path_name()])
                widget = self.active_layer()
                if valid(widget) and widget.call_function("IsActivated"): widget.call_function("DeactivateWidget")
                self.report.update(original_specs_restored=self.specs() == self.original_specs,
                    original_profiles_restored=all(str(ue.get_mixin_profile(value)) == self.original_profiles[value.get_path_name()] for values in self.abilities.values() for value in values),
                    original_cdos_preserved=self.cdo_state() == self.original_cdos, native_layer_restored=not valid(self.active_layer()))
            self.close_observer(); self.report["fixture_observers_closed"] = self.scope is None
        except Exception: error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_WIDGET_PRESSED_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report, self.plan, self.extras)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_WIDGET_PRESSED_SHUTDOWN_" + self.report["status"].upper())


if any(value.startswith("-UEPWidgetPressedResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPWidgetPressedResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
