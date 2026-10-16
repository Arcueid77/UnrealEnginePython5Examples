"""Reject incomplete/fabricated held-widget report claims; no native proof."""
import copy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_abilities/widget_held_contract.py"
SPEC = importlib.util.spec_from_file_location("held_contract_model", PATH)
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


def fixture():
    report = dict(status="passed", error=None, cases=[], safety_regressions=[], targets=["tdm", "cp"],
        policy_shutdown=dict(active_count=0, scopes_created=31, scopes_closed=31, errors=[]))
    report.update({key: False for key in contract.FALSE_CLAIMS})
    report.update({key: True for key in ("original_player_restored", "original_profiles_restored",
        "original_ability_specs_restored", "original_cdos_untouched", "native_layer_restored")})
    for target in ("tdm", "cp"):
        for name in contract.PLAN:
            row = {key: True for key in ("native_type_preserved", "profile_selected", "native_widget_activated", "native_widget_owner_correct",
                "native_widget_in_original_layer", "native_widget_removed", "native_layer_restored", "ability_ended", "no_late_callbacks",
                "player_restored", "native_state_end_removed_while_active", "profile_teardown_ended_ability", "native_pause_observed", "active_during_pause")}
            row.update(native_widget_class=contract.WIDGETS[target], original_soft_class_path=contract.WIDGETS[target],
                native_tasks_during=2, native_tasks_after=0, input_injections=1,
                activation_source="existing-spec-enhanced-input", native_map="L_Expanse" if target == "tdm" else "L_Convolution_Blockout",
                native_action_triggers_when_paused=False, active_during_pause=False, native_widget_removed_during_pause=True, paused_input_injections=3,
                native_scoring_component="/ShooterCore/" + ("Elimination/B_TeamDeathMatchScoring.B_TeamDeathMatchScoring_C" if target == "tdm" else
                    "ControlPoint/B_ControlPointScoring.B_ControlPointScoring_C"))
            blueprint, python = copy.deepcopy(row), copy.deepcopy(row)
            blueprint["counters"] = dict(fallback_activations=1, activations=0)
            python["counters"] = dict(activations=1, pushes_requested=1, widgets_pushed=1, widgets_removed=1,
                tasks_created=2, scopes_created=2, scopes_closed=2, input_released=1, fallback_activations=0)
            report["cases"].append(dict(target=target, name=name, blueprint=blueprint, python=python))
    for name in ("cancel-pending", "repeat-pending", "profile-switch-pending"):
        row = {key: True for key in ("native_pending_observed", "native_layer_restored", "ability_ended", "no_late_callbacks",
            "owned_scopes_balanced", "direct_native_asc_activation_fixture", "pending_references_cleared", "pending_proxy_collected")}
        report["safety_regressions"].append(dict(row, name=name, bp_parity_claimed=False))
    return report


class HeldGate(unittest.TestCase):
    def test_complete_synthetic_report_passes_shape_only(self):
        self.assertEqual(contract.validate(fixture())["pairs"], 14)

    def test_missing_pair_is_rejected(self):
        value = fixture(); value["cases"].pop()
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reordered_pairs_are_rejected(self):
        value = fixture(); value["cases"].reverse()
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_identical_but_wrong_widget_is_rejected(self):
        value = fixture()
        for side in ("blueprint", "python"): value["cases"][0][side]["native_widget_class"] = "wrong"
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_localonly_authority_or_physical_claim_is_rejected(self):
        for field in contract.FALSE_CLAIMS:
            value = fixture(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_fixture_grant_cannot_replace_actual_experience_input(self):
        value = fixture(); value["cases"][-1]["python"]["activation_source"] = "fixture-grant-native-ASC-input"
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_controlpoint_requires_actual_scoring_context_not_elimination_fixture(self):
        value = fixture(); value["cases"][-1]["python"]["native_scoring_component"] = value["cases"][0]["python"]["native_scoring_component"]
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_original_bp_must_really_be_baseline(self):
        value = fixture(); value["cases"][0]["blueprint"]["counters"]["activations"] = 1
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_python_trial_must_not_reactivate_original_bp_after_handoff(self):
        value = fixture(); value["cases"][4]["python"]["counters"]["fallback_activations"] = 1
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_leaked_task_or_scope_rejected(self):
        for field in ("native_tasks_after", "native_tasks_during"):
            value = fixture(); value["cases"][0]["python"][field] = 4
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
        value = fixture(); value["cases"][0]["python"]["counters"]["scopes_closed"] = 1
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_state_end_must_keep_ability_active_and_remove_ui(self):
        value = fixture(); value["cases"][3]["python"]["native_state_end_removed_while_active"] = False
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_pending_cleanup_and_gc_are_required_not_bp_parity(self):
        for field, invalid in (("pending_proxy_collected", False), ("pending_references_cleared", False), ("bp_parity_claimed", True)):
            value = fixture(); value["safety_regressions"][0][field] = invalid
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_pause_must_release_non_pause_input_and_remove_actual_ui(self):
        for field, invalid in (("active_during_pause", True), ("native_action_triggers_when_paused", True),
                               ("native_widget_removed_during_pause", False), ("paused_input_injections", 0)):
            value = fixture(); value["cases"][6]["python"][field] = invalid
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_post_shutdown_active_or_error_is_rejected(self):
        for field, invalid in (("active_count", 1), ("scopes_closed", 0), ("errors", ["error"])):
            value = fixture(); value["policy_shutdown"][field] = invalid
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)


if __name__ == "__main__":
    unittest.main()
