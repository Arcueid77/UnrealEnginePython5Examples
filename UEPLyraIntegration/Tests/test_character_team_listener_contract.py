"""Existing native matrix plus script-owned factory ordering and natural ingress."""
import unittest
from test_character_team_observer_contract import report as observer_report
from uep_lyra_characters.team_listener_contract import validate


def upgrade(value):
    value["listener_factory_orchestration_migrated"] = True
    for item in value["cases"]:
        calls, py = item["calls"], item["profile"] == "Python"
        item["listener_counters"] = dict(python_calls=calls*int(py), fallback_calls=calls*int(not py), factories=calls*int(py), binds=calls*int(py), activations=calls*int(py), null_factories=0)
    value["natural_startup_python_dispatch"] = {key: dict(listener_factory_counters=dict(python_calls=1, fallback_calls=0, factories=1, binds=1, activations=1, null_factories=0)) for key in ("owner", "unassigned")}
    return value


class CharacterTeamListenerReportModels(unittest.TestCase):
    def setUp(self): self.report = upgrade(observer_report())
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(self.report)
    def test_complete_shape_is_model_not_native_acceptance(self): self.assertTrue(validate(self.report)["listener_factory_orchestration_migrated"])
    def test_cannot_relabel_previous_bp_factory_as_python(self): self.report["listener_factory_orchestration_migrated"] = False; self.reject()
    def test_python_factory_counts_without_native_proxy_rejected(self): self.report["cases"][1]["native_proxies_created"] = 0; self.reject()
    def test_python_factory_must_bind_native_result(self): self.report["cases"][1]["listener_counters"]["binds"] = 0; self.reject()
    def test_python_factory_must_activate(self): self.report["cases"][1]["listener_counters"]["activations"] = 0; self.reject()
    def test_each_repeat_keeps_original_activation(self): self.report["cases"][3]["listener_counters"]["factories"] = 1; self.reject()
    def test_natural_beginplay_must_enter_python_factory(self): self.report["natural_startup_python_dispatch"]["owner"]["listener_factory_counters"]["python_calls"] = 0; self.reject()
    def test_no_gc_regression_hidden_by_new_factory_counters(self): self.report["cleanup"]["native_latest_cancelled_proxies_retained"] = 1; self.reject()
    def test_private_selector_and_commandlet_safety(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterListenerResult=x"]), "uep_lyra_characters.team_listener_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterListenerResult=x"]))
