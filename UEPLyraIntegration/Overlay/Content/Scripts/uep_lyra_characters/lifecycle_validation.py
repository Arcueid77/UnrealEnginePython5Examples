"""Native lethal damage/Avatar removal with old-Actor POD event evidence."""
import atexit
import copy
import sys
import unreal_engine as ue
from .inventory_clear_validation import CharacterEvidence
from uep_lyra_abilities.auto_respawn_activation_validation import Validation as Natural
from . import lifecycle_mixin as policy
from .lifecycle_contract import validate


class LifecycleEvidence(CharacterEvidence):
    def __init__(self, *args):
        super().__init__(*args)
        self.report.pop("other_character_business_migrated", None)
        self.report.update(character_lifecycle_events_migrated=True, other_remaining_character_business_migrated=False,
            character_events_called_by_fixture=False)

    def start_inventory_evidence(self):
        super().start_inventory_evidence()
        self.lifecycle_counts = policy.evidence(self.pawn); self.lifecycle_before = copy.deepcopy(self.lifecycle_counts)

    def end_inventory_evidence(self, row):
        super().end_inventory_evidence(row)
        # The original Actor can already be destroyed/collected. Retain only
        # its ordinary dict, never a rooted Actor/GAS instance or dead wrapper.
        after = copy.deepcopy(self.lifecycle_counts)
        row["character_lifecycle"] = dict(old_character=self.character_path, profile=self.profile,
            counters={key: after[key]-self.lifecycle_before[key] for key in after if key != "last_event"},
            last_event=after["last_event"], pod_only_after_actor_destruction=True)

    def trial_begin_evidence(self):
        super().trial_begin_evidence()
        if self.report.get("peer") == "server":
            self.foreign_server_lifecycle = policy.evidence(self.other.get_controlled_pawn())
            self.foreign_server_lifecycle_before = copy.deepcopy(self.foreign_server_lifecycle)

    def trial_end_evidence(self):
        super().trial_end_evidence()
        if self.report.get("peer") == "server":
            self.row["server_foreign_character_lifecycle"] = dict(before=self.foreign_server_lifecycle_before,
                after=copy.deepcopy(self.foreign_server_lifecycle))

    def foreign_begin_evidence(self):
        super().foreign_begin_evidence()
        self.foreign_lifecycle = policy.evidence(self.controller.get_controlled_pawn())
        self.foreign_lifecycle_before = copy.deepcopy(self.foreign_lifecycle)

    def foreign_end_evidence(self, row):
        super().foreign_end_evidence(row)
        row["foreign_character_lifecycle"] = dict(before=self.foreign_lifecycle_before, after=copy.deepcopy(self.foreign_lifecycle))

    def validate_report(self): return validate(self.report)


class Validation(LifecycleEvidence, Natural): pass


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterLifecycleResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
