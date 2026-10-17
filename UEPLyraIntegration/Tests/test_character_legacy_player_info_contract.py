"""Native typed legacy helper evidence; notification provenance must stay explicit."""
import unittest
from test_character_team_observer_contract import report as observer_report
from uep_lyra_characters.legacy_player_info_contract import validate


def upgrade(value):
    value.update(callback_replayed=True, legacy_repnotify_manually_called_by_typed_bp=True, real_legacy_repnotify_ingress_tested=False, native_net_mode=value.get("native_net_mode", "Standalone"))
    for item in value["cases"]:
        calls, py = item["calls"], item["profile"] == "Python"
        item.update(typed_bp_refresh_calls=calls, counters=dict(python_calls=calls*int(py), fallback_calls=calls*int(not py), team_forwards=calls*int(py)),
            team_counters=dict(python_calls=calls*int(py), fallback_calls=calls*int(not py)),
            helper_payload=dict(team_id=0, display_asset=None), native_team_state_unchanged=True, native_listener_proxy_set_unchanged=True,
            visual=dict(outline=dict(scalar=0, vector=[.645833, 0., .568715, 1.])), expected_outline_color=[.645833, 0., .568715, 1.])
    return value


class CharacterLegacyPlayerInfoReportModels(unittest.TestCase):
    def setUp(self): self.report = upgrade(observer_report())
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(self.report)
    def test_shape_is_host_model_not_runtime(self): self.assertEqual(validate(self.report)["typed_bp_legacy_calls"], 8)
    def test_not_actual_replicated_notification(self): self.report["real_legacy_repnotify_ingress_tested"] = True; self.reject()
    def test_replayed_notification_must_be_disclosed(self): self.report["callback_replayed"] = False; self.reject()
    def test_typed_bp_call_required(self): self.report["cases"][0]["typed_bp_refresh_calls"] = 0; self.reject()
    def test_current_team_cannot_replace_literal_zero(self): self.report["cases"][0]["helper_payload"]["team_id"] = 2; self.reject()
    def test_actual_native_team_must_not_change(self): self.report["cases"][1]["native_team_state_unchanged"] = False; self.reject()
    def test_observer_creation_not_part_of_this_function(self): self.report["cases"][1]["native_listener_proxy_set_unchanged"] = False; self.reject()
    def test_native_outline_value_required(self): self.report["cases"][1]["visual"]["outline"]["scalar"] = 2; self.reject()
    def test_device_roots_must_close(self): self.report["cleanup"]["device_roots_released"] = 21; self.reject()
    def test_standalone_actual_mode(self): self.report["native_net_mode"] = "Client"; self.reject()
    def test_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterLegacyResult=x"]), "uep_lyra_characters.legacy_player_info_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterLegacyResult=x"]))
