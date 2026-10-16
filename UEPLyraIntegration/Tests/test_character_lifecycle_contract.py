"""Reject duplicate events, forged forwards, Avatar callbacks and old scope claims."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_character_inventory_clear_contract import report as death_report
from test_character_inventory_clear_reset_contract import report as reset_report
from uep_lyra_characters import lifecycle_contract as gate
from uep_lyra_hud.startup import validation_module


def header(value):
    value.pop("other_character_business_migrated", None)
    value.update(character_lifecycle_events_migrated=True, other_remaining_character_business_migrated=False, character_events_called_by_fixture=False)


def add_row(row, profile, *, avatar=False, reset=False):
    counts = {key: 0 for key in gate.COUNTERS}
    if not avatar:
        counts[("reset" if reset else "death")+("_python" if profile == "Python" else "_fallback")] = 1
        counts["clear_forwards"] = int(profile == "Python")
    row["character_lifecycle"] = dict(old_character=row["old_pawn"], profile=profile, counters=counts,
        last_event=None if avatar else "K2_OnReset" if reset else "K2_OnDeathFinished", pod_only_after_actor_destruction=True)


def report(reset=False):
    value = (reset_report if reset else death_report)(); header(value)
    if reset:
        for row in value["cases"]: add_row(row, row["profile"], reset=True)
    else:
        for case in value["cases"]:
            for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")): add_row(case[key], profile)
        for row in value["avatar_endplay_cases"]: add_row(row, row["profile"], avatar=True)
    return value


class CharacterLifecycleReportModels(unittest.TestCase):
    def test_native_death_and_bare_avatar_regression_requires_selected_event_and_helper(self):
        self.assertTrue(gate.validate(report())["native_cpp_character_event_to_selected_python_and_inventory"])

    def test_eight_native_reset_requests_require_reset_not_death_event(self):
        self.assertTrue(gate.validate(report(True), reset=True)["native_reset_event_tested"])

    def test_no_event_duplicate_or_implicit_original_fallthrough(self):
        for fields in (dict(death_python=0), dict(death_fallback=1), dict(clear_forwards=2)):
            value = report(); value["cases"][0]["python"]["character_lifecycle"]["counters"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_wrong_event_on_reset_and_fabricated_bare_avatar_callback_fail(self):
        value = report(True); value["cases"][1]["character_lifecycle"]["last_event"] = "K2_OnDeathFinished"
        with self.assertRaises(RuntimeError): gate.validate(value, reset=True)
        value = report(); value["avatar_endplay_cases"][0]["character_lifecycle"]["counters"]["death_fallback"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_inventory_empty_window_and_replica_definition_model_still_required(self):
        value = report(); value["cases"][0]["python"]["character_inventory"]["native_empty_before_new_pawn"] = None
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_dead_actor_evidence_cannot_be_relabelled_or_require_a_native_pointer(self):
        for fields in (dict(old_character="other"), dict(pod_only_after_actor_destruction=False)):
            value = report(); value["cases"][0]["python"]["character_lifecycle"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_old_helper_only_claim_or_broader_migration_or_manual_event_is_rejected(self):
        for fields in (dict(other_character_business_migrated=False), dict(other_remaining_character_business_migrated=True),
                dict(character_events_called_by_fixture=True), dict(character_lifecycle_events_migrated=False)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_one_listener_scope_leak_fails_even_when_all_event_rows_match(self):
        value = report(); value["inventory_fixture_shutdown"]["closed"] -= 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_private_selectors_do_not_start_legacy_parent_fixtures(self):
        root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"
        files = ("uep_lyra_abilities/auto_respawn_activation_validation.py", "uep_lyra_abilities/auto_respawn_reset_validation.py", "uep_lyra_characters/inventory_clear_validation.py")
        def unexpected(*args): raise AssertionError("duplicate legacy fixture")
        for relative in files:
            file = root/relative; tail = ast.parse(file.read_text(encoding="utf-8")).body[-2:]
            for flag in ("-UEPCharacterLifecycleResult=x", "-UEPCharacterLifecycleResetResult=x"):
                namespace = dict(sys=types.SimpleNamespace(argv=[flag, "-UEPAutoRespawnActivation"]), Validation=unexpected, ResetTrials=unexpected)
                with self.subTest(relative=relative, flag=flag): exec(compile(ast.Module(body=tail, type_ignores=[]), str(file), "exec"), namespace)

    def test_event_evidence_only_reads_retained_pod_after_native_old_actor_is_gone(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/lifecycle_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "LifecycleEvidence")
        class Base:
            def end_inventory_evidence(self, row): pass
        namespace = dict(CharacterEvidence=Base, copy=copy)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        fixture = namespace["LifecycleEvidence"].__new__(namespace["LifecycleEvidence"])
        fixture.lifecycle_before = dict(death_python=0, last_event=None); fixture.lifecycle_counts = dict(death_python=1, last_event="K2_OnDeathFinished")
        fixture.character_path, fixture.profile = "destroyed-character", "Python"; row = {}
        fixture.end_inventory_evidence(row); self.assertEqual(row["character_lifecycle"]["counters"], dict(death_python=1))

    def test_explicit_natural_and_reset_selectors_are_disabled_in_commandlet(self):
        for flag, module in (("-UEPCharacterLifecycleResult=x", "lifecycle_validation"), ("-UEPCharacterLifecycleResetResult=x", "lifecycle_reset_validation")):
            self.assertEqual(validation_module([flag]), "uep_lyra_characters."+module)
            self.assertIsNone(validation_module(["-run=Py", flag]))
