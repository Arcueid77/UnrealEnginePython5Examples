"""Original ShooterExplorer input/UI preflight before any parent migration."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from .widget_held_validation import instances
from .widget_pressed_context_contract import PLAN, CLASSES, WIDGETS, require, validate


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index, self.finished = Path(result), time.monotonic(), "ready", 0, False
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.mode = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPWidgetPressedContextMode=")), "OriginalBP")
        require(self.mode in ("OriginalBP", "PythonSmoke"), "unknown pressed-widget context mode")
        self.report = dict(status="running", error=None, cases=[], last_readiness="waiting for actual Inventory Experience/input/grants/layout",
            source_mode=self.mode,
            runtime_migration_acceptance=False, full_acceptance=False, physical_input_tested=False, fixture_granted_abilities=0,
            activation_handler_replayed=False, widgets_created_by_probe=False, original_specs_restored=False, original_layer_restored=False)
        if self.mode == "PythonSmoke":
            from . import widget_pressed_mixin as policy
            self.report["policy_before"] = policy.snapshot()

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def specs(self):
        return sorted(value.get_path_name() for spec in self.asc.get_property("ActivatableAbilities").Items
                      for value in list(spec.NonReplicatedInstances) + list(spec.ReplicatedInstances) if valid(value))
    def active_layer(self): return self.layer.call_function("GetActiveWidget")
    def inject(self, pressed):
        self.controller.inject_enhanced_input_for_action(self.action, pressed)
        if pressed: self.row["input_injections"] += 1

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3) or "L_InventoryTestMap" not in world.get_name(): continue
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if not valid(controller): continue
            pawn = controller.get_controlled_pawn()
            if not valid(pawn): continue
            asc = ability_system(pawn)
            if not valid(asc): continue
            found = {name: instances(asc, ue.load_class(path)) for name, path in CLASSES.items()}
            self.report["last_readiness"] = dict(pawn=pawn.get_path_name(), abilities={name: len(values) for name, values in found.items()})
            if not all(len(values) == 2 and len({value.get_path_name() for value in values}) == 2 and
                       not any(value.get_property("bIsActive") for value in values) for values in found.values()): continue
            layouts = [obj for obj in world.all_objects() if valid(obj) and obj.is_a(ue.find_class("PrimaryGameLayout"))
                       and obj.call_function("GetOwningPlayer") == controller]
            if len(layouts) != 1: continue
            layer = layouts[0].get_property("GameMenu_Stack")
            if not valid(layer) or valid(layer.call_function("GetActiveWidget")): continue
            self.world, self.controller, self.pawn, self.asc, self.layer = world, controller, pawn, asc, layer
            self.abilities = found
            if self.mode == "PythonSmoke":
                require(all(str(ue.get_mixin_profile(value)) == "Python" for values in found.values() for value in values),
                        "candidate smoke requires each original native instance's default Python Profile")
            specs = self.specs()
            if specs != getattr(self, "stable_specs", None):
                self.stable_specs, self.specs_stable_since = specs, time.monotonic(); return
            if time.monotonic() - self.specs_stable_since < 1.: return
            self.original_specs = specs; self.begin(); return

    def begin(self):
        self.target = PLAN[self.index]; self.current_abilities = self.abilities[self.target]
        suffix = "Inventory" if self.target == "inventory" else "Map"
        self.action = ue.load_object(ue.find_class("InputAction"), "/ShooterExplorer/Input/Actions/IA_Toggle" + suffix + ".IA_Toggle" + suffix)
        self.row = dict(target=self.target, input_injections=0,
            original_native_type=all(value.get_class().get_path_name() == CLASSES[self.target] for value in self.current_abilities),
            native_net_policy=int(self.current_abilities[0].get_property("NetExecutionPolicy")), native_input_activated_ability=False,
            original_instance_paths=[value.get_path_name() for value in self.current_abilities], native_close_calls=0)
        self.inject(True); self.enter("open")

    def opened(self):
        require(time.monotonic() - self.phase_started < 10., "original pressed input did not open native UI")
        # One press only: repeated Triggered values can reactivate an already
        # ended duplicate spec while another asynchronous panel is still loading.
        self.inject(False)
        self.row["native_input_activated_ability"] |= any(value.get_property("bIsActive") for value in self.current_abilities)
        widget = self.active_layer()
        if not valid(widget) or widget.get_class().get_path_name() != WIDGETS[self.target] or not widget.call_function("IsActivated"): return
        self.widget = widget
        self.row.update(widget_active=True, widget_class=widget.get_class().get_path_name(), original_menu_layer=True,
            widget_owner_correct=widget.call_function("GetOwningPlayer") == self.controller,
            native_tasks=sum(len(value.get_property("ActiveTasks")) for value in self.current_abilities))
        self.inject(False); self.enter("released")

    def released(self):
        self.inject(False)
        if time.monotonic() - self.phase_started < .3: return
        self.row["release_does_not_end_ability"] = any(value.get_property("bIsActive") for value in self.current_abilities) and self.widget.call_function("IsActivated")
        self.row["active_instances_after_release"] = [value.get_path_name() for value in self.current_abilities if value.get_property("bIsActive")]
        self.widget.call_function("DeactivateWidget"); self.row["native_close_calls"] += 1; self.enter("closed")

    def closed(self):
        require(time.monotonic() - self.phase_started < 5., "native original close did not end ability/restore layer")
        widget = self.active_layer()
        if valid(widget) and widget.call_function("IsActivated"):
            widget.call_function("DeactivateWidget"); self.row["native_close_calls"] += 1
        if any(value.get_property("bIsActive") for value in self.current_abilities) or valid(self.active_layer()): return
        if time.monotonic() - self.phase_started < .35: return
        self.row.update(native_close_ended_ability=True, layer_restored=True)
        self.report["cases"].append(self.row.copy()); self.index += 1
        if self.index == len(PLAN): self.finish()
        else: self.begin()

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < 100., "original pressed-widget readiness/total timeout: " + str(self.report["last_readiness"]))
            if self.phase == "ready": self.ready()
            elif self.phase == "open": self.opened()
            elif self.phase == "released": self.released()
            else: self.closed()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if hasattr(self, "action"): self.inject(False)
            if hasattr(self, "widget") and valid(self.widget): self.widget.call_function("DeactivateWidget")
            if hasattr(self, "abilities"):
                for values in self.abilities.values():
                    for ability in values:
                        if ability.get_property("bIsActive"): ability.call_function("K2_EndAbility")
                self.report.update(original_specs_restored=self.specs() == self.original_specs,
                    original_layer_restored=not valid(self.active_layer()), original_specs=self.original_specs, final_specs=self.specs())
        except Exception: error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_WIDGET_PRESSED_CONTEXT_" + ("FAILED " + error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        if self.mode == "PythonSmoke":
            from . import widget_pressed_mixin as policy
            self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_WIDGET_PRESSED_CONTEXT_SHUTDOWN_" + self.report["status"].upper())


if any(value.startswith("-UEPWidgetPressedContextResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPWidgetPressedContextResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
