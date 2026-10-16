"""Device report gate negatives; these models are not runtime/hardware evidence."""
import copy
import unittest
import ast
from pathlib import Path
from uep_lyra_devices import team_color_contract as gate
from uep_lyra_hud.startup import validation_module


def report():
    color = dict(enabled=True, reset=False, rgba=[20, 80, 160, 255]); white = dict(enabled=True, reset=False, rgba=[255]*4)
    result = dict(status="passed", error=None, native_default_profile_observed=True, original_player_restored=True,
        owned_handles_removed=True, roots_created=15, roots_removed=15, invalid_user_public_bp_entry_used=True,
        same_instance_native_reactivation_tested=False,
        invalid_user_submitted_to_scheduler=False, native_default_color=color, cases=[],
        policy_shutdown=dict(errors=[], active_count=0, script_subscriptions_created=0))
    for key in ("direct_python_handler_replayed", "native_apply_called_by_probe", "hardware_output_tested", "full_acceptance", "network_acceptance",
        "packaged_runtime", "animation_assets_modified", "device_mapping_written", "cdo_profile_written"): result[key] = False
    for name in gate.PLAN:
        invalid, switched = name == "public-invalid-user", name == "same-instance-profile-switch"
        looped = name in ("native-looping", "native-paused-loop") or switched
        pair = dict(name=name)
        for side in ("blueprint", "python"):
            count = 6 if looped else (2 if name == "native-repeat" else 1)
            py_count, bp_count = (3, 3) if switched else ((count, 0) if side == "python" else (0, count))
            pair[side] = dict(native_type_preserved=True, native_profile_selected=True, original_player_restored=True,
                native_class="/ShooterCore/Game/B_TeamColor_DeviceProperty.B_TeamColor_DeviceProperty_C", native_scheduler_used=not invalid,
                native_activation_count=0 if invalid else (2 if name == "native-repeat" else 1),
                same_instance_profile_switch_preserved=switched, native_pause_observed=name == "native-paused-loop",
                before=copy.deepcopy(white), after=copy.deepcopy(white if invalid else color),
                counters=dict(evaluations=py_count, valid_controllers=0 if invalid else py_count,
                    colors_written=0 if invalid else py_count, fallback_evaluations=bp_count))
        result["cases"].append(pair)
    return result


class TeamColorGate(unittest.TestCase):
    def test_complete_native_software_matrix(self): self.assertEqual(gate.validate(report())["pairs"], 6)

    def test_explicit_fixture_only(self):
        self.assertEqual(validation_module(["-UEPDeviceColorResult=report.json"]), "uep_lyra_devices.team_color_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPDeviceColorResult=report.json"]))

    def test_probe_uses_only_reflected_class_factory_not_instance_activation(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_devices/team_color_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8"))
        strings = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        self.assertIn("ActivateDevicePropertyOfClass", strings); self.assertNotIn("ActivateDeviceProperty", strings)

    def test_reject_wrong_color_profile_switch_and_native_pause(self):
        value = report(); value["cases"][0]["python"]["after"]["rgba"] = [0]*4
        with self.assertRaises(RuntimeError): gate.validate(value)
        for index, field in ((3, "same_instance_profile_switch_preserved"), (4, "native_pause_observed")):
            value = report(); value["cases"][index]["python"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_invalid_user_mutation_and_scheduler_claim(self):
        value = report(); value["cases"][-1]["python"]["after"]["enabled"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["invalid_user_submitted_to_scheduler"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_owned_handle_root_leaks_and_false_hardware_claim(self):
        for field, replacement in (("owned_handles_removed", False), ("roots_removed", 12), ("hardware_output_tested", True)):
            value = report(); value[field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
