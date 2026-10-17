"""Reuse native inventory identity/undo proofs; change only the typed ingress."""
import copy
import unreal_engine as ue
from .initial_inventory_validation import Trial as LoadoutTrial
from . import inventory_ready_mixin as policy
from . import initial_inventory_mixin as loadout
from .initial_inventory_contract import PLAN, require
from .initial_inventory_validation import state, path, valid

PROBE = "/Game/UEPValidation/BP_CharacterInventoryReadyProbe.BP_CharacterInventoryReadyProbe_C"


class Probe:
    def __init__(self, trial, native): self.trial, self.native, self.owned = trial, native, []

    def live(self):
        return {path(value): value for value in ue.tobject_iterator(ue.find_class("AsyncAction_ExperienceReady")) if valid(value)}

    def call_function(self, name, actor):
        self.before = copy.deepcopy(policy.evidence(actor)); self.before_loadout = copy.deepcopy(loadout.evidence(actor))
        before = set(self.live())
        result = self.native.call_function(name, actor)
        added = [value for key, value in self.live().items() if key not in before]
        require(len(added) == 1, "typed factory transport did not create one actual native ExperienceReady proxy")
        self.owned.extend(added)
        return result

    def capture(self, actor, require_grant=True):
        delta = {key: value-self.before[key] for key, value in policy.evidence(actor).items()}
        if delta["python_calls"]+delta["fallback_calls"] != 1: return False
        after = loadout.evidence(actor)
        if require_grant and sum(after[key]-self.before_loadout[key] for key in ("python_calls", "fallback_calls")) != 1: return False
        self.trial.last_ready_delta = delta
        return True

    def collected(self): return all(not valid(value) for value in self.owned)


class Trial(LoadoutTrial):
    probe_path = PROBE

    def __init__(self, controller):
        super().__init__(controller)
        self.ready_class = ue.load_class(PROBE); self.root_owned = not self.ready_class.is_rooted(); self.root_released = False
        if self.root_owned: self.ready_class.add_to_root()
        self.probe = Probe(self, self.probe)

    def execute(self, index):
        name, profile, definitions, occupied = PLAN[index]
        for slot in range(len(self.quickbar.call_function("GetSlots"))):
            if not (occupied and slot == 0): self.quickbar.call_function("RemoveItemFromSlot", slot)
        self.pawn.set_property("InitialInventoryItems", [ue.load_class(value) for value in definitions]); ue.set_mixin_profile(self.pawn, profile)
        self.probe.call_function("Grant", self.pawn)
        self.row = dict(name=name, profile=profile, configured_definitions=list(definitions), occupied_first=occupied, bp_reference_call=True,
            native_character_class=self.pawn.get_class().get_path_name(), real_experience_factory_signal=True)
        return self.row

    def capture(self):
        if not self.probe.capture(self.pawn): return False
        after = loadout.evidence(self.pawn)
        added = [dict(path=path(value), definition=path(value.ItemDef)) for value in self.inventory.call_function("GetAllItems") if path(value) not in self.original["items"]]
        self.row.update(native_model=state(self.controller), added_items=added,
            original_item_retained=all(value in self.inventory.call_function("GetAllItems") for value in self.original_items),
            new_items_are_new_identities=all(item["path"] not in self.original["items"] for item in added),
            counters={key: after[key]-self.probe.before_loadout[key] for key in after if key != "last_call"}, readiness_counters=copy.deepcopy(self.last_ready_delta))
        return True

    def close_probe(self):
        if self.root_owned and not self.root_released:
            self.ready_class.remove_from_root(); self.root_released = True
        return dict(created=int(self.root_owned), released=int(self.root_released))
