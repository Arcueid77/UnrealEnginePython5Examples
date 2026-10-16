"""Synthetic retained-Character ingress/effect/lifetime evidence rejection."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_auto_respawn_activation_contract import report as natural_report
from uep_lyra_characters import inventory_clear_contract as gate

PISTOL = "/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C"


def state(item="old-item"):
    return dict(controller_valid=True, quickbar_valid=True, inventory_valid=True, slots=[item, None, None],
        active=0 if item else -1, items=[dict(path=item, definition=PISTOL)] if item else [])


def add_row(row, profile, *, authority=True, avatar=False):
    before, after, empty = state(), state("new-item"), state(None)
    if avatar: after = copy.deepcopy(before)
    counters = dict(python_calls=int(profile == "Python" and not avatar), fallback_calls=int(profile == "BlueprintFallback" and not avatar),
        authority_noops=int(not authority and profile == "Python" and not avatar), missing_controller_noops=0,
        missing_quickbar_noops=0, missing_inventory_noops=0, slots_removed=3*int(authority and profile == "Python" and not avatar),
        items_removed=int(authority and profile == "Python" and not avatar))
    last = None if avatar else dict(profile=profile, actor=row["old_pawn"], authority=authority, native_role=3 if authority else 2,
        before=copy.deepcopy(before), after=copy.deepcopy(empty if authority else before))
    raw = copy.deepcopy(after)
    cleanup = dict(required=False, removed_items=[])
    if avatar:
        extra = dict(path="new-orphan", definition=PISTOL); raw["items"].append(extra)
        cleanup = dict(required=True, removed_items=[extra])
    row["character_inventory"] = dict(old_character=row["old_pawn"], profile=profile, counters=counters, last_call=last,
        before=before, after=after, native_empty_before_new_pawn=empty if authority and not avatar else None,
        native_signals=[dict(channel="Lyra.QuickBar.Message.SlotsChanged", state=empty)] if not avatar else [], observer_closed=True,
        new_character_class=gate.CLASS, new_character_profile="Python", raw_after_before_fixture_cleanup=raw, native_orphan_cleanup=cleanup)


def add_peer(value):
    value.update(character_clear_business_migrated=True, other_character_business_migrated=False, character_clear_called_by_fixture=False,
        inventory_properties_written=False, native_inventory_setup_by_fixture=False, signal_payload_owner_claimed=False, character_profile_switch_tested=False)


def report():
    value = natural_report(); add_peer(value)
    for case in value["cases"]:
        for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")): add_row(case[key], profile)
    for row in value["avatar_endplay_cases"]: add_row(row, row["profile"], avatar=True)
    value["inventory_fixture_shutdown"] = dict(created=10, closed=10, active=0)
    return value


class CharacterInventoryEvidenceModels(unittest.TestCase):
    def test_bounded_natural_shape(self): self.assertTrue(gate.validate(report())["character_clear_inventory_native_bp_ingress"])

    def test_two_matching_but_wrong_native_inventory_results_fail(self):
        value = report()
        for side in ("blueprint", "python"): value["cases"][0][side]["character_inventory"]["after"]["items"] = []
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_actual_selected_helper_and_no_double_bp_execution_required(self):
        for fields in (dict(python_calls=0), dict(fallback_calls=1), dict(items_removed=0), dict(slots_removed=2)):
            value = report(); value["cases"][0]["python"]["character_inventory"]["counters"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_independent_empty_window_cannot_be_replaced_by_policy_snapshot(self):
        value = report(); value["cases"][0]["python"]["character_inventory"]["native_empty_before_new_pawn"] = None
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_retained_character_type_actual_native_role_and_new_item_ids_required(self):
        for mutate in (lambda v: v.update(new_character_class="PythonSubclass"), lambda v: v["last_call"].update(native_role=2),
            lambda v: v.update(after=copy.deepcopy(v["before"]))):
            value = report(); mutate(value["cases"][0]["python"]["character_inventory"])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_avatar_must_preserve_raw_orphan_and_remove_only_that_item(self):
        for mutate in (lambda v: v["raw_after_before_fixture_cleanup"]["items"].pop(), lambda v: v["native_orphan_cleanup"].update(removed_items=[]),
            lambda v: v["raw_after_before_fixture_cleanup"]["slots"].__setitem__(1, "new-orphan"), lambda v: v["counters"].update(python_calls=1)):
            value = report(); mutate(value["avatar_endplay_cases"][1]["character_inventory"])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_natural_death_cannot_use_fixture_inventory_cleanup(self):
        value = report(); value["cases"][0]["python"]["character_inventory"]["native_orphan_cleanup"]["required"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_observer_scope_and_narrow_business_claim_required(self):
        for fields in (dict(character_clear_called_by_fixture=True), dict(other_character_business_migrated=True),
            dict(signal_payload_owner_claimed=True), dict(inventory_fixture_shutdown=dict(created=10, closed=9, active=1))):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_parent_activation_module_must_not_start_duplicate_character_fixture(self):
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_activation_validation.py"
        footer = ast.parse(path.read_text(encoding="utf-8")).body[-1]
        def unexpected(*args): raise AssertionError("duplicate parent fixture")
        scope = dict(result="x", sys=types.SimpleNamespace(argv=["-UEPAutoRespawnHelpersResult=x", "-UEPAutoRespawnActivation", "-UEPCharacterInventory"]), Validation=unexpected)
        exec(compile(ast.Module(body=[footer], type_ignores=[]), str(path), "exec"), scope)
