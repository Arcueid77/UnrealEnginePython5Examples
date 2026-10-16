"""Negative gates for bounded mounted-UMG proof; not runtime results."""
import copy
import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/action_touch_contract.py"
spec = importlib.util.spec_from_file_location("action_touch_contract_model", file)
contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)


class ActionTouchContract(unittest.TestCase):
    def setUp(self):
        self.report = dict(status="passed", test_owned_mounted_pairs=True, direct_bp_functions_called_by_probe=True,
            native_commonui_state_changes=True, synthetic_typed_duration_producer=True, widgets_created=4,
            widgets_removed=4, widget_roots_released=4, owned_listeners_closed=True, native_widget_reconstruction_tested=True,
            shutdown=dict(active_count=0, errors=[], scopes_created=4, scopes_closed=4), cases=[])
        self.report["native_widget_scheduling"] = [dict(kind=kind, cdo=dict(TickFrequency=1, bHasScriptImplementedTick=kind == "base"),
            widgets=[dict(TickFrequency=1, bHasScriptImplementedTick=kind == "base")]*2) for kind in ("base", "mobile")]
        for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_touch_tested",
                     "native_input_action_effect_tested", "widget_tick_called_by_probe", "production_placement_tested"):
            self.report[flag] = False
        for kind in ("base", "mobile"):
            for name in contract.cases_for(kind):
                self.report["cases"].append(dict(kind=kind, name=name, same_class=True, automatic_ticks=3 if kind == "base" else 0,
                    python=dict(cooldown=.5), blueprint=dict(cooldown=.5)))

    def test_full_bounded_native_matrix(self):
        self.assertEqual(contract.validate(self.report)["cases"], 30)

    def test_wrong_material_state_missing_ticks_or_class_change_rejected(self):
        for field, value in (("python", dict(cooldown=.6)), ("automatic_ticks", 1), ("same_class", False)):
            report = copy.deepcopy(self.report); report["cases"][0][field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_root_or_listener_leak_and_missing_reconstruct_rejected(self):
        for field, value in (("widget_roots_released", 3), ("owned_listeners_closed", False), ("native_widget_reconstruction_tested", False)):
            report = copy.deepcopy(self.report); report[field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)
        self.report["shutdown"]["scopes_closed"] = 3
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_physical_touch_claim_and_manual_tick_rejected(self):
        for field in ("physical_touch_tested", "widget_tick_called_by_probe", "network_acceptance"):
            report = copy.deepcopy(self.report); report[field] = True
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_partial_or_duplicate_matrix_rejected(self):
        self.report["cases"][-1] = self.report["cases"][0]
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_enabling_original_mobile_tick_or_inventing_tick_evidence_rejected(self):
        report = copy.deepcopy(self.report); report["native_widget_scheduling"][1]["cdo"]["bHasScriptImplementedTick"] = True
        with self.assertRaises(RuntimeError):
            contract.validate(report)
        self.report["cases"][15]["automatic_ticks"] = 3
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
