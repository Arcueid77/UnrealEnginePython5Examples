"""Original death/Reset BP calls ClearInventory; observe native state independently."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_activation_validation import Validation as Natural
from . import inventory_clear_mixin as policy
from .inventory_clear_contract import validate
from uep_lyra_abilities.auto_respawn_helpers_contract import require


class CharacterEvidence:
    def __init__(self, *args):
        super().__init__(*args)
        self.inventory_scope = None; self.inventory_scopes_created = self.inventory_scopes_closed = 0
        self.report.update(character_clear_business_migrated=True, other_character_business_migrated=False,
            character_clear_called_by_fixture=False, inventory_properties_written=False, character_profile_switch_tested=False,
            native_inventory_setup_by_fixture=False, signal_payload_owner_claimed=False)

    def start_inventory_evidence(self):
        self.close_inventory_observer()
        self.character_path = self.pawn.get_path_name()
        ue.set_mixin_profile(self.pawn, self.profile)
        self.character_counts = policy.evidence(self.pawn)
        self.character_before = copy.deepcopy(self.character_counts)
        self.inventory_before = policy.inventory_state(self.controller)
        self.inventory_signals, self.inventory_empty = [], None
        self.inventory_scope = SubscriptionScope(); self.inventory_scopes_created += 1
        for channel in ("Lyra.QuickBar.Message.SlotsChanged", "Lyra.Inventory.Message.StackChanged"):
            self.inventory_scope.listen_gameplay_signal(self.pawn, channel, self.inventory_signal)

    def inventory_signal(self, channel):
        self.inventory_signals.append(dict(channel=str(channel.TagName), state=policy.inventory_state(self.controller)))
        self.sample_inventory()

    def sample_inventory(self):
        if self.inventory_scope is None: return
        state = policy.inventory_state(self.controller)
        pawn = self.controller.get_controlled_pawn()
        if state["quickbar_valid"] and state["inventory_valid"] and not any(state["slots"]) and not state["items"] and state["active"] == -1 and (
            not valid(pawn) or pawn.get_path_name() == self.character_path) and self.inventory_empty is None:
            self.inventory_empty = copy.deepcopy(state)

    def close_inventory_observer(self):
        scope, self.inventory_scope = self.inventory_scope, None
        if scope is not None: scope.close(); self.inventory_scopes_closed += 1

    def end_inventory_evidence(self, row):
        self.sample_inventory()
        raw = policy.inventory_state(self.controller)
        cleanup = dict(required=False, removed_items=[])
        if getattr(self, "avatar_trial", False):
            # Bare K2_DestroyActor never calls ClearInventory. The native new
            # Pawn adds an un-slotted pistol while the original slot/item lives.
            # Preserve this raw behavior, then remove only that new orphan.
            old = {item["path"]: item for item in self.inventory_before["items"]}
            current = {item["path"]: item for item in raw["items"]}
            from uep_lyra_abilities.auto_respawn_helpers_contract import require
            require(all(current.get(path) == value for path, value in old.items()), "bare Avatar changed original inventory items")
            added = [item for path, item in current.items() if path not in old]
            require(len(added) == 1 and added[0]["path"] not in raw["slots"] and
                added[0]["definition"] == "/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C", "unexpected bare Avatar inventory delta")
            quick, inventory = policy.components(self.controller)
            for item in list(inventory.call_function("GetAllItems")):
                if item.get_path_name() == added[0]["path"]:
                    inventory.call_function("RemoveItemInstance", item); cleanup["removed_items"].append(added[0])
            cleanup["required"] = True
        self.close_inventory_observer()
        after = copy.deepcopy(self.character_counts)
        row["character_inventory"] = dict(old_character=self.character_path, profile=self.profile,
            counters={key: after[key]-self.character_before[key] for key in after if key != "last_call"}, last_call=after["last_call"],
            before=self.inventory_before, after=policy.inventory_state(self.controller),
            raw_after_before_fixture_cleanup=raw, native_orphan_cleanup=cleanup,
            native_empty_before_new_pawn=self.inventory_empty, native_signals=copy.deepcopy(self.inventory_signals), observer_closed=True,
            new_character_class=self.controller.get_controlled_pawn().get_class().get_path_name(),
            new_character_profile=str(ue.get_mixin_profile(self.controller.get_controlled_pawn())))

    def trial_begin_evidence(self):
        self.start_inventory_evidence(); super().trial_begin_evidence()
        if self.report.get("peer") == "server":
            self.server_foreign_inventory = policy.inventory_state(self.other)

    def trial_end_evidence(self):
        self.end_inventory_evidence(self.row); super().trial_end_evidence()
        if self.report.get("peer") == "server":
            self.row["server_foreign_inventory"] = dict(before=self.server_foreign_inventory, after=policy.inventory_state(self.other))

    def foreign_begin_evidence(self):
        self.foreign_inventory = policy.inventory_state(self.controller)
        super().foreign_begin_evidence()

    def foreign_end_evidence(self, row):
        row["foreign_character_inventory"] = dict(before=self.foreign_inventory, after=policy.inventory_state(self.controller))
        super().foreign_end_evidence(row)

    def tick(self, delta):
        try:
            if self.report.get("peer") == "server" and self.phase in ("respawn", "ack"):
                require(policy.inventory_state(self.other) == self.server_foreign_inventory, "foreign server inventory changed during Character clear")
            elif self.phase == "foreign":
                require(policy.inventory_state(self.controller) == self.foreign_inventory, "foreign client inventory changed during Character clear")
        except Exception:
            self.finish(traceback.format_exc()); return False
        return super().tick(delta)

    def observe(self): self.sample_inventory(); return super().observe()
    def observe_avatar(self): self.sample_inventory(); return super().observe_avatar()
    def observe_reset(self): self.sample_inventory(); return super().observe_reset()
    def finish(self, error=None): self.close_inventory_observer(); return super().finish(error)

    def finalize(self):
        self.close_inventory_observer()
        self.report["inventory_fixture_shutdown"] = dict(created=self.inventory_scopes_created, closed=self.inventory_scopes_closed, active=int(self.inventory_scope is not None))
        return super().finalize()

    def validate_report(self): return validate(self.report)


class Validation(CharacterEvidence, Natural): pass


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoRespawnHelpersResult=")), None)
if result and "-UEPCharacterInventory" in sys.argv:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
