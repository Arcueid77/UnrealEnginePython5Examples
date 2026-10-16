"""Independent stencil golden values and real nested/direct native boundaries."""
import ast
from pathlib import Path
import types
import unittest
from test_character_team_cosmetics_contract import report as team
from uep_lyra_characters import stencil_contract as gate
from uep_lyra_hud.startup import validation_module


def counts(profile, calls, component_count, local):
    py = profile == "Python"
    return dict(python_calls=calls*int(py), fallback_calls=calls*int(not py), component_queries=calls*int(py),
        component_writes=calls*component_count*int(py), local_player_zeroes=calls*int(py and local))


def report(local_owner=True):
    value = team(local_owner)
    for row in value["cases"]:
        row["stencil_counters"] = counts(row["profile"], row["calls"], len(row["actual"]["primitives"]), row["locally_controlled"] and row["player_controlled"])
    value.update(natural_startup_stencil_python_dispatch=dict(python_calls=2, fallback_calls=0, component_queries=2), stencil_cases=[],
        native_child_actor_created_destroyed=True, native_child_component_recursive_discovery=True, native_fixture_extra_component_created=True,
        fixture_actor_replication_disabled=True, stencil_caller_roots_created=1, stencil_caller_roots_released=1,
        parent_bp_asset_modified=False, whole_parent_class_family_migrated=False)
    for name, profile, target, number, calls in gate.PLAN:
        local = local_owner and target == "owner"; size = 1 if target == "owner" else 3
        result = 0 if local else min(255, max(0, number))
        value["stencil_cases"].append(dict(name=name, profile=profile, target=target, team_id=number, calls=calls, bp_reference_call=True,
            locally_controlled=local, player_controlled=target == "owner", child_components=0 if target == "owner" else 1,
            components=[dict(component=str(index), value=result, render_custom_depth_unchanged=True) for index in range(size)],
            counters=counts(profile, calls, size, local), native_gc_held_components_and_callers_survived=True, original_visual_camera_profile_restored=True))
    return value


class CharacterStencilReportModels(unittest.TestCase):
    def test_team_regression_plus_twelve_direct_bp_python_pairs_with_native_clamping(self):
        result = gate.validate(report()); self.assertEqual((result["native_direct_stencil_pairs"], result["native_direct_stencil_bp_calls"], result["native_case_trials"]), (12, 32, 40))

    def test_dedicated_server_nonlocal_values_and_absent_device_subsystem_are_valid(self): gate.validate(report(False))

    def test_missing_or_reordered_direct_call_plan_fails(self):
        for mutate in (lambda r: r["stencil_cases"].pop(), lambda r: r["stencil_cases"].reverse()):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_identical_wrong_native_clamp_and_local_control_results_fail(self):
        for index in (0, 18, 20):
            value = report()
            for row in value["stencil_cases"][index:index+2]: row["components"][0]["value"] = 999
            with self.subTest(index=index), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_child_recursion_and_render_toggle_invariant_required(self):
        for mutate in (lambda r: r["stencil_cases"][12].update(child_components=0),
                lambda r: r["stencil_cases"][0]["components"][0].update(render_custom_depth_unchanged=False)):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_direct_and_python_nested_dispatch_cannot_silently_run_original_bp(self):
        for mutate in (lambda r: r["stencil_cases"][1]["counters"].update(python_calls=0),
                lambda r: r["cases"][1]["stencil_counters"].update(python_calls=0)):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["stencil_counters"]["fallback_calls"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_gc_actor_lifetime_and_original_state_restore_required(self):
        for fields in (dict(native_gc_held_components_and_callers_survived=False), dict(original_visual_camera_profile_restored=False)):
            value = report(); value["stencil_cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        for fields in (dict(native_child_actor_created_destroyed=False), dict(stencil_caller_roots_released=0), dict(native_child_component_recursive_discovery=False)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_unchanged_parent_and_bounded_character_family_scope_required(self):
        for fields in (dict(parent_bp_asset_modified=True), dict(whole_parent_class_family_migrated=True)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_actual_natural_team_to_stencil_startup_required(self):
        value = report(); value["natural_startup_stencil_python_dispatch"]["python_calls"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_explicit_stencil_startup_is_disabled_for_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterStencilResult=x"]), "uep_lyra_characters.stencil_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterStencilResult=x"]))

    def test_direct_phase_failure_cleans_up_and_never_logs_a_success_marker(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/stencil_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Validation")
        node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "finish")
        events = []; engine = types.SimpleNamespace(log=lambda text: events.append(("log", text)), log_error=lambda text: events.append(("error", text)), request_exit=lambda: events.append(("exit", None)))
        namespace = dict(ue=engine, traceback=types.SimpleNamespace(format_exc=lambda: "direct probe failed"))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), "exec"), namespace)
        def fail(): raise RuntimeError("native probe failed")
        fixture = types.SimpleNamespace(finished=False, direct_complete=False, direct_trials=fail, cleanup=lambda: events.append(("cleanup", None)), report={}, write=lambda: None)
        namespace["finish"](fixture)
        self.assertEqual(fixture.report["status"], "failed"); self.assertEqual(events[0], ("cleanup", None))
        self.assertEqual([kind for kind, text in events], ["cleanup", "error", "exit"])

    def test_added_stencil_caller_root_releases_even_when_base_cleanup_fails(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/stencil_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Validation")
        class Base:
            def cleanup(self): raise RuntimeError("original visual restore failed")
        namespace = dict(TeamNative=Base, valid=lambda value: False, traceback=types.SimpleNamespace(format_exc=lambda: "original visual restore failed"))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), "exec"), namespace)
        fixture = namespace["Validation"].__new__(namespace["Validation"]); released = []
        fixture.stencil_caller_root, fixture.stencil_caller_released = True, False
        fixture.stencil_caller = types.SimpleNamespace(remove_from_root=lambda: released.append(True)); fixture.child, fixture.report = "destroyed", {}
        for number in range(2):
            with self.assertRaisesRegex(RuntimeError, "original visual restore failed"): fixture.cleanup()
        self.assertEqual(released, [True]); self.assertEqual(fixture.report["stencil_caller_roots_released"], 1)
