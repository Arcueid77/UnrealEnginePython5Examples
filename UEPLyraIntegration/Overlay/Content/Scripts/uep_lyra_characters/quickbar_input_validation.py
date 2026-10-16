"""Actual BP actor-reference call -> native GAS payload/task -> native equipment."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready, instances
from uep_lyra_abilities.quickslot_mixin import CLASS as ABILITY
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture, services, path
from . import quickbar_input_mixin as policy
from .quickbar_input_contract import CLASS, PLAN, validate

PROBE = "/Game/UEPValidation/BP_CharacterQuickbarCallProbe.BP_CharacterQuickbarCallProbe_C"


def fingerprint(controller):
    inventory, quickbar = services(controller)
    return dict(items=sorted(path(value) for value in inventory.call_function("GetAllItems")),
        slots=[path(value) for value in quickbar.call_function("GetSlots")], active=int(quickbar.call_function("GetActiveSlotIndex")))


def prepare(controller):
    inventory, quickbar = services(controller)
    for definition in ("/ShooterCore/Weapons/Rifle/ID_Rifle.ID_Rifle_C", "/ShooterCore/Weapons/Shotgun/ID_Shotgun.ID_Shotgun_C"):
        index = int(quickbar.call_function("GetNextFreeItemSlot")); require(index >= 0, "three-slot fixture unavailable")
        item = inventory.call_function("AddItemDefinition", ue.load_class(definition), 1)
        quickbar.call_function("AddItemToSlot", index, item)


def restore(controller, original):
    inventory, quickbar = services(controller)
    quickbar.call_function("SetActiveSlotIndex", original["active"])
    for index, item in enumerate(quickbar.call_function("GetSlots")):
        if valid(item) and path(item) not in original["items"]: quickbar.call_function("RemoveItemFromSlot", index)
    for item in list(inventory.call_function("GetAllItems")):
        if path(item) not in original["items"]: inventory.call_function("RemoveItemInstance", item)
    require(fingerprint(controller) == original, "Character slot fixture changed original native item/slot identities")


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result)
        self.initialized, self.scope, self.observer, self.slot_two = False, None, None, None
        self.report.update(scopes_created=0, scopes_closed=0, active_observation_scopes=0,
            physical_keyboard_tested=False, python_handler_replayed=False, inventory_properties_written=False,
            native_rpc_bypassed=False, gameplay_event_replication_claimed=False, whole_character_migrated=False,
            full_acceptance=False, original_fields_profile_cdo_restored=False, original_inventory_restored=False)

    def tasks(self):
        return sum(valid(task) and task.is_a(ue.find_class("AbilityTask_WaitGameplayEvent")) for task in self.quick_ability.get_property("ActiveTasks"))

    def initialize(self):
        self.inventory, self.quickbar = services(self.controller)
        found = instances(self.asc, ue.load_class(ABILITY)); require(len(found) == 1, "native Quickslot instance not unique")
        self.quick_ability = found[0]
        require(self.quick_ability.get_property("bIsActive") and self.tasks() == 3 and
            str(ue.get_mixin_profile(self.quick_ability)) == "Python", "natural Python Quickslot OnSpawn/tasks not active")
        require(self.pawn.get_class().get_path_name() == CLASS, "unexpected native Character type")
        self.original = fingerprint(self.controller); self.original_model = capture(self.controller)
        self.actor_before = (str(ue.get_mixin_profile(self.pawn)), path(self.pawn.Emote_AudioComponent))
        self.cdo = self.pawn.get_class().get_cdo(); self.cdo_before = (str(ue.get_mixin_profile(self.cdo)), path(self.cdo.Emote_AudioComponent))
        self.probe = ue.load_class(PROBE).get_cdo(); self.initialized = True
        self.report.update(player_id=int(self.controller.PlayerState.PlayerId), actor=self.pawn.get_path_name(),
            native_role=int(self.pawn.call_function("GetLocalRole")))
        if not getattr(self, "network_fixture", False): prepare(self.controller)

    def configure_authority_trial(self):
        empty, initial = self.spec[6], self.spec[2]
        if self.slot_two is None: self.slot_two = self.quickbar.call_function("GetSlots")[2]
        current = self.quickbar.call_function("GetSlots")[2]
        if not empty and not valid(current): self.quickbar.call_function("AddItemToSlot", 2, self.slot_two)
        self.quickbar.call_function("SetActiveSlotIndex", initial)
        if empty and valid(current): self.quickbar.call_function("RemoveItemFromSlot", 2)

    def begin(self):
        if not self.initialized: self.initialize()
        self.start_trial()

    def start_trial(self):
        self.spec = PLAN[self.index]
        if not getattr(self, "network_fixture", False): self.configure_authority_trial()
        name, profile, initial, index, tag, expected, empty = self.spec
        require(int(self.quickbar.call_function("GetActiveSlotIndex")) == initial, "Character slot native starting index differs")
        require((not valid(self.quickbar.call_function("GetSlots")[2])) == empty, "Character slot fixture empty state differs")
        self.inventory_ids = sorted(path(item) for item in self.inventory.call_function("GetAllItems"))
        self.events, self.callback_errors = [], []
        self.tasks_before = self.tasks(); require(self.tasks_before == 3, "original Quickslot tasks changed before Character call")
        ue.set_mixin_profile(self.pawn, profile); self.before = dict(policy.evidence(self.pawn))
        self.observer = ue.find_class("AbilityTask_WaitGameplayEvent").get_cdo().call_function(
            "WaitGameplayEvent", self.quick_ability, GameplayTag(TagName=tag), None, False, True)
        require(valid(self.observer), "native event observer task unavailable")
        self.scope = SubscriptionScope(); self.report["scopes_created"] += 1; self.report["active_observation_scopes"] += 1
        self.scope.bind_event(self.observer, "EventReceived", self.on_payload)
        self.observer.call_function("ReadyForActivation")
        self.probe.call_function("SelectSlot", self.pawn, index, GameplayTag(TagName=tag))
        self.enter("equipment")

    def on_payload(self, payload):
        try:
            self.events.append(dict(tag=str(payload.EventTag.TagName), magnitude=float(payload.EventMagnitude),
                instigator_null=payload.Instigator is None, target_null=payload.Target is None,
                optional_objects_null=payload.OptionalObject is None and payload.OptionalObject2 is None))
        except Exception: self.callback_errors.append(traceback.format_exc())

    def close_observer(self):
        if self.scope is not None:
            self.scope.close(); self.scope = None
            self.report["scopes_closed"] += 1; self.report["active_observation_scopes"] -= 1
        if valid(self.observer): self.observer.call_function("EndTask")
        self.observer = None

    def observe(self):
        model = capture(self.controller)
        if model is None or model["active"] != self.spec[5]:
            require(time.monotonic()-self.phase_started < 6., "Character slot native equipment result timeout: "+repr(model)); return
        self.close_observer()
        name, profile, initial, index, tag, expected, empty = self.spec
        row = dict(name=name, profile=profile, initial=initial, slot=index, tag=tag, empty_slot=empty, bp_reference_call=True,
            native_character_class=self.pawn.get_class().get_path_name(), inventory=copy.deepcopy(model),
            inventory_items_unchanged=sorted(path(item) for item in self.inventory.call_function("GetAllItems")) == self.inventory_ids,
            counters={key: value-self.before[key] for key, value in policy.evidence(self.pawn).items()},
            events=copy.deepcopy(self.events), callback_errors=list(self.callback_errors), native_tasks_before=self.tasks_before,
            native_tasks_after=self.tasks(), task_scope_closed=self.scope is None)
        self.report["cases"].append(row); self.record_trial(row)
        ue.log("UEP_CHARACTER_QUICKBAR_CASE_PASSED "+name+"/"+profile)
        self.index += 1
        if self.index == len(PLAN): self.finish()
        else: self.begin()

    def record_trial(self, row): pass

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240, "Character slot native timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "equipment" and time.monotonic()-self.phase_started >= .2: self.observe()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def restore_actor(self):
        self.close_observer()
        if self.initialized:
            ue.set_mixin_profile(self.pawn, self.actor_before[0])
            self.report["original_fields_profile_cdo_restored"] = (str(ue.get_mixin_profile(self.pawn)), path(self.pawn.Emote_AudioComponent)) == self.actor_before and (
                str(ue.get_mixin_profile(self.cdo)), path(self.cdo.Emote_AudioComponent)) == self.cdo_before
            self.report["native_quickslot_ability_active_with_three_tasks"] = bool(self.quick_ability.get_property("bIsActive")) and self.tasks() == 3

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            self.restore_actor()
            if self.initialized:
                restore(self.controller, self.original)
                self.report["original_inventory_restored"] = capture(self.controller) == self.original_model
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_QUICKBAR_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_QUICKBAR_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterQuickbarResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
