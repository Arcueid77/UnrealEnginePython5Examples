"""Team report semantics, actual nested entry and owned scheduler lifetime."""
import ast
import copy
import types
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_characters import team_cosmetics_contract as gate
from uep_lyra_hud.startup import validation_module


def report(local_owner=True):
    rows = []; total = 0
    for name, profile, source, team, calls, target in gate.PLAN:
        number = 0 if team == "current" else team; controlled = target == "owner" and local_owner; user = controlled
        py = profile == "Python"; devices = calls if user else 0; total += devices
        counters = dict(python_calls=calls*int(py), fallback_calls=calls*int(not py), color_queries=calls*int(py),
            outline_calls=calls*int(py), stencil_calls=calls*int(py), display_applies=calls*int(py and source == "current"),
            invalid_platform_noops=calls*int(py and not user), device_activation_attempts=calls*int(py and user))
        rows.append(dict(name=name, profile=profile, source=source, team_id=number, calls=calls, target=target, bp_reference_call=True,
            expected_color=[.645833, 0., .568715, 1.], locally_controlled=controlled, player_controlled=target == "owner", platform_user_valid=user,
            counters=counters, outline_counters=dict(python_calls=calls*int(py), fallback_calls=calls*int(not py)),
            actual=dict(primitives=[dict(component="Actor.Mesh", stencil=0 if controlled else number, materials=[])],
                outline=dict(scalar=float(number), vector=[.645833, 0., .568715, 1.]) if controlled else None),
            native_device_properties_created=devices, native_scheduler_removed_owned_properties=True,
            native_device_properties=[dict(native_type=gate.DEVICE, counters=dict(evaluations=1, valid_controllers=1, colors_written=1, fallback_evaluations=0),
                color=dict(enabled=True, reset=False, rgba=[1, 2, 3, 255])) for _ in range(devices)], original_visual_camera_profile_restored=True))
    markers = len(gate.PLAN)*2 if local_owner else 0
    return dict(status="passed", retained_character_class=gate.CLASS, current_display_asset_valid=True, original_team_id=0,
        natural_startup_python_dispatch=dict(python_calls=2, fallback_calls=0), cases=rows,
        native_device_subsystem_available=local_owner, native_observation_markers=markers, native_observation_markers_removed=True, native_handle_queries_read_only=True, native_active_set_written=False,
        device_roots_created=total+markers, device_roots_released=total+markers,
        caller_roots_created=1, caller_roots_released=1, owned_unpossessed_actor_destroyed=True, original_visual_camera_profile_cdo_inventory_restored=True,
        **{key: False for key in ("hardware_output_tested", "pixels_verified", "whole_character_migrated", "full_acceptance", "device_mapping_written", "callbacks_replayed", "all_device_properties_removed")})


class CharacterTeamReportModels(unittest.TestCase):
    def test_eight_native_bp_python_pairs_and_real_scheduler_rows(self): self.assertEqual(gate.validate(report())["native_bp_python_pairs"], 8)

    def test_missing_reordered_and_failed_case_matrix_rejected(self):
        for mutate in (lambda r: r["cases"].pop(), lambda r: r["cases"].reverse(), lambda r: r.update(status="failed")):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_identically_wrong_stencil_and_outline_values_fail(self):
        for mutate in (lambda r: r["actual"]["primitives"][0].update(stencil=99),
            lambda r: r["actual"]["outline"].update(scalar=99.), lambda r: r["actual"]["outline"].update(vector=[])):
            value = report()
            for row in value["cases"][:2]: mutate(row)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_function_argument_plan_and_typed_bp_reference_required(self):
        for fields in (dict(team_id=7), dict(calls=2), dict(bp_reference_call=False)):
            value = report(); value["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_selected_outer_and_nested_outline_dispatch_counts_required(self):
        for field in ("python_calls", "color_queries", "outline_calls", "stencil_calls", "display_applies", "device_activation_attempts"):
            value = report(); value["cases"][1]["counters"][field] = 0
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][1]["outline_counters"]["python_calls"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_actual_native_scheduler_properties_evaluate_and_finish_not_callback_replay(self):
        for fields in (dict(native_device_properties_created=0), dict(native_scheduler_removed_owned_properties=False)):
            value = report(); value["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["native_device_properties"][0]["counters"]["evaluations"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_invalid_user_cannot_create_native_properties(self):
        value = report(); value["cases"][12]["native_device_properties_created"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_roots_original_visual_state_owned_actor_and_cdo_restore_required(self):
        for fields in (dict(device_roots_released=0), dict(caller_roots_released=0), dict(owned_unpossessed_actor_destroyed=False),
            dict(original_visual_camera_profile_cdo_inventory_restored=False)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_natural_actor_team_entry_and_current_asset_are_actual_requirements(self):
        for fields in (dict(current_display_asset_valid=False), dict(natural_startup_python_dispatch=dict(python_calls=0, fallback_calls=1))):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_hardware_pixels_mapping_mutation_and_global_device_cleanup_not_claimed(self):
        for key in ("hardware_output_tested", "pixels_verified", "whole_character_migrated", "full_acceptance", "device_mapping_written", "callbacks_replayed", "all_device_properties_removed"):
            value = report(); value[key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_fixture_startup_explicit_and_not_a_commandlet_action(self):
        self.assertEqual(validation_module(["-UEPCharacterTeamResult=x"]), "uep_lyra_characters.team_cosmetics_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterTeamResult=x"]))

    def test_marker_completion_readonly_queries_and_no_global_set_mutation_required(self):
        for fields in (dict(native_observation_markers=0), dict(native_observation_markers_removed=False),
                dict(native_handle_queries_read_only=False), dict(native_active_set_written=True)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_observer_requires_actual_handle_removal_and_native_evaluation(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/team_cosmetics_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DeviceObserver")
        namespace = dict(valid=bool, device_policy=types.SimpleNamespace(instance_snapshot=lambda v: dict(evaluations=v)))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), "exec"), namespace)
        observer = namespace["DeviceObserver"].__new__(namespace["DeviceObserver"])
        for active, pointer, evaluations, expected in ((True, None, 1, False), (False, "live", 1, False), (False, None, 0, False), (False, None, 1, True)):
            observer.subsystem = types.SimpleNamespace(call_function=lambda name, h: active if name == "IsPropertyActive" else pointer)
            with self.subTest(active=active, pointer=pointer, evaluations=evaluations):
                self.assertEqual(observer.observed([("actual-handle", evaluations)]), expected)

    def test_dedicated_server_subsystem_absence_is_native_noop_not_fake_activation(self):
        self.assertEqual(gate.validate(report(False))["native_device_scheduler_properties"], 0)
        value = report(); value["native_device_subsystem_available"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/team_cosmetics_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DeviceObserver")
        namespace = dict(valid=bool, require=gate.require)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), "exec"), namespace)
        observer = namespace["DeviceObserver"].__new__(namespace["DeviceObserver"]); observer.subsystem = None
        self.assertIsNone(observer.marker()); self.assertEqual(observer.collect(None), [])
