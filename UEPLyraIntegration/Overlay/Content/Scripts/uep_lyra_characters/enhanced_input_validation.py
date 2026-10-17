"""Actual engine input injection -> retained receiver -> GAS -> native equipment."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture, path
from .quickbar_input_validation import Validation as NativeSlots, fingerprint, restore
from . import enhanced_input_mixin as policy, quickbar_input_mixin as helper
from .enhanced_input_contract import ACTIONS, PLAN, require, validate
from .enhanced_input_bindings import function_names


def fill_slots(quickbar, items):
    for index, item in enumerate(items):
        current = quickbar.call_function("GetSlots")[index]
        if not valid(current): quickbar.call_function("AddItemToSlot", index, item)
        elif current != item: raise RuntimeError("input fixture would overwrite an unrelated native slot item")


class Validation(NativeSlots):
    def __init__(self, result):
        super().__init__(result)
        self.prepared_slots = None; self.action = self.input = None
        self.report.update(bp_receiver_called_by_fixture=False)

    def initialize(self):
        super().initialize()
        self.input = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetLocalPlayerSubsystem", self.controller, ue.find_class("EnhancedInputLocalPlayerSubsystem"))
        require(valid(self.input), "actual owner EnhancedInput subsystem missing")
        self.receiver_names = function_names(self.pawn.get_class()); self.report["native_input_bindings"] = dict(self.receiver_names)
        registered, = [value for value in ue.get_registered_mixins() if value["target_class"] == self.pawn.get_class()]
        self.report["native_profile_method_counts"] = {name: len(value["functions"]) for name, value in registered["profiles"].items()}
        if not getattr(self, "network_fixture", False): self.prepared_slots = list(self.quickbar.call_function("GetSlots"))

    def configure_authority_trial(self):
        name, action, initial, expected, empty, profile = self.spec
        fill_slots(self.quickbar, self.prepared_slots)
        self.quickbar.call_function("SetActiveSlotIndex", initial)
        if empty is not None: self.quickbar.call_function("RemoveItemFromSlot", empty)

    def start_trial(self):
        self.spec = PLAN[self.index]
        if not getattr(self, "network_fixture", False): self.configure_authority_trial()
        name, action, initial, expected, empty, profile = self.spec
        require(int(self.quickbar.call_function("GetActiveSlotIndex")) == initial and
            all((not valid(value)) == (index == empty) for index, value in enumerate(self.quickbar.call_function("GetSlots"))), "input native initial slots differ")
        self.events, self.callback_errors = [], []; self.inventory_ids = sorted(path(item) for item in self.inventory.call_function("GetAllItems"))
        ue.set_mixin_profile(self.pawn, profile)
        self.before, self.helper_before = dict(policy.evidence(self.pawn)), dict(helper.evidence(self.pawn))
        self.tasks_before = self.tasks(); require(self.tasks_before == 3, "original Quickslot wait tasks not active before input")
        tag = ACTIONS[action][3]
        self.observer = ue.find_class("AbilityTask_WaitGameplayEvent").get_cdo().call_function("WaitGameplayEvent", self.quick_ability, GameplayTag(TagName=tag), None, False, True)
        require(valid(self.observer), "input native GAS payload observer unavailable")
        self.scope = SubscriptionScope(); self.report["scopes_created"] += 1; self.report["active_observation_scopes"] += 1
        self.scope.bind_event(self.observer, "EventReceived", self.on_payload); self.observer.call_function("ReadyForActivation")
        asset = ACTIONS[action][0]
        self.action = ue.load_object(ue.find_class("InputAction"), "/ShooterCore/Input/Actions/"+asset+"."+asset)
        # Native input dispatch, never a receiver/Profile method or BP probe call.
        self.input.call_function("InjectInputVectorForAction", self.action, ue.FVector(1., 0., 0.))
        self.release_sent = False; self.enter("input")

    def observe_input(self):
        if not self.release_sent:
            self.input.call_function("InjectInputVectorForAction", self.action, ue.FVector(0., 0., 0.)); self.release_sent = True
        elapsed = time.monotonic()-self.phase_started
        counts = {key: value-self.before[key] for key, value in policy.evidence(self.pawn).items()}
        nested = {key: value-self.helper_before[key] for key, value in helper.evidence(self.pawn).items()}
        # Native Original fallback intentionally never enters a Python receiver;
        # the original graph must still invoke its selected virtual helper once.
        entries = nested["python_calls"]+nested["fallback_calls"]
        require(entries <= 1, "native input repeated a Triggered receiver unexpectedly")
        model = capture(self.controller)
        if entries != 1 or model is None or model["active"] != self.spec[3] or elapsed < .3:
            require(elapsed < 8, "native EnhancedInput receiver/equipment timeout: "+repr(counts)+"/"+repr(model)); return
        self.close_observer()
        name, action, initial, expected, empty, profile = self.spec
        row = dict(name=name, action=action, initial=initial, empty_slot=empty, profile=profile,
            native_character_class=self.pawn.get_class().get_path_name(), native_input_subsystem_used=True,
            positive_native_injections=1, native_bound_receiver=self.receiver_names[action], input_counters=counts,
            helper_counters=nested, native_original_input_fallback=profile == "BlueprintFallback",
            receiver_is_native_router=self.pawn.find_function(self.receiver_names[action]).get_class().get_name() == "PythonFunction",
            inventory=copy.deepcopy(model), inventory_items_unchanged=sorted(path(item) for item in self.inventory.call_function("GetAllItems")) == self.inventory_ids,
            events=copy.deepcopy(self.events), callback_errors=list(self.callback_errors), native_tasks_before=self.tasks_before,
            native_tasks_after=self.tasks(), task_scope_closed=self.scope is None, no_repeated_or_release_handler=entries == 1)
        self.report["cases"].append(row); self.record_trial(row)
        ue.log("UEP_CHARACTER_INPUT_CASE_PASSED "+name+"/"+profile)
        self.index += 1
        if self.index == len(PLAN): self.finish()
        else: self.begin()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300, "native input standalone timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "input": self.observe_input()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def restore_actor(self):
        if valid(self.input) and valid(self.action): self.input.call_function("InjectInputVectorForAction", self.action, ue.FVector(0., 0., 0.))
        super().restore_actor()

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            self.restore_actor()
            if self.initialized:
                fill_slots(self.quickbar, self.prepared_slots); restore(self.controller, self.original)
                self.report["original_inventory_restored"] = capture(self.controller) == self.original_model
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_INPUT_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_INPUT_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterInputResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
