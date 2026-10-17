"""Input acceptance rejects direct method calls, missed events and identical wrong results."""
import copy
import unittest
from uep_lyra_characters.enhanced_input_contract import ACTIONS, PLAN, CLASS, DEFINITIONS, validate


def trial(spec):
    name, action, initial, selected, empty, profile = spec
    _, function, slot, tag = ACTIONS[action]; py = profile == "Python"; sent = empty is None
    return dict(name=name, action=action, initial=initial, empty_slot=empty, profile=profile, native_character_class=CLASS,
        native_input_subsystem_used=True, positive_native_injections=1, native_bound_receiver=function,
        input_counters=dict(python_calls=int(py), fallback_calls=0, **{key: int(py and key == action) for key in ACTIONS}),
        native_original_input_fallback=not py, receiver_is_native_router=True,
        helper_counters=dict(python_calls=int(py), fallback_calls=int(not py), events_sent=int(py and sent), empty_slot_noops=int(py and not sent), invalid_index_noops=0, missing_controller_noops=0, missing_quickbar_noops=0),
        inventory=dict(active=selected, items=sorted(DEFINITIONS), slots=[None if index == empty else value for index, value in enumerate(DEFINITIONS)], definition=DEFINITIONS[selected],
            equipment_instigator_matches=True, equipment_class=DEFINITIONS[selected].replace("/ID_", "/B_WeaponInstance_").replace(".ID_", ".B_WeaponInstance_")),
        inventory_items_unchanged=True, native_tasks_before=3, native_tasks_after=3, task_scope_closed=True, callback_errors=[], no_repeated_or_release_handler=True,
        events=[dict(tag=tag, magnitude=float(slot), instigator_null=True, target_null=True, optional_objects_null=True)] if sent else [])


def report():
    return dict(status="passed", error=None, cases=[trial(spec) for spec in PLAN], native_profile_method_counts=dict(Python=17, BlueprintFallback=12), native_input_bindings={key: value[1] for key, value in ACTIONS.items()}, scopes_created=16, scopes_closed=16, active_observation_scopes=0,
        original_fields_profile_cdo_restored=True, original_inventory_restored=True, native_quickslot_ability_active_with_three_tasks=True,
        **dict.fromkeys(("physical_keyboard_tested", "python_handler_replayed", "bp_receiver_called_by_fixture", "inventory_properties_written", "native_rpc_bypassed", "gameplay_event_replication_claimed", "whole_character_migrated", "full_acceptance"), False))


class CharacterEnhancedInputReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(self.report)
    def test_complete_shape_is_model_only_not_actual_acceptance(self): self.assertEqual(validate(self.report)["native_enhanced_input_trials"], 16)
    def test_exit_alone_cannot_replace_input_matrix(self): self.report["cases"] = []; self.reject()
    def test_direct_receiver_call_rejected(self): self.report["bp_receiver_called_by_fixture"] = True; self.reject()
    def test_native_input_subsystem_required(self): self.report["cases"][0]["native_input_subsystem_used"] = False; self.reject()
    def test_exact_generated_receiver_required(self): self.report["cases"][0]["native_bound_receiver"] = "ChangeQuickbarSlot"; self.reject()
    def test_input_not_only_nested_helper_counts(self): self.report["cases"][1]["input_counters"]["python_calls"] = 0; self.reject()
    def test_wrong_action_cannot_match_selected_slot_by_chance(self): self.report["cases"][0]["input_counters"]["slot-1"] = 1; self.reject()
    def test_nested_virtual_helper_must_use_selected_profile(self): self.report["cases"][1]["helper_counters"]["python_calls"] = 0; self.reject()
    def test_independent_gas_event_required(self): self.report["cases"][0]["events"] = []; self.reject()
    def test_cycle_keeps_raw_zero_index_not_result_slot_magnitude(self): self.report["cases"][6]["events"][0]["magnitude"] = 2.; self.reject()
    def test_empty_default_cycle_keeps_original_noop(self): self.report["cases"][-1]["inventory"]["active"] = 2; self.reject()
    def test_identical_but_wrong_equipment_rejected(self):
        for row in self.report["cases"][:2]: row["inventory"]["equipment_class"] = "wrong"
        self.reject()
    def test_native_item_identities_cannot_change(self): self.report["cases"][0]["inventory_items_unchanged"] = False; self.reject()
    def test_release_must_not_repeat_triggered_receiver(self): self.report["cases"][0]["no_repeated_or_release_handler"] = False; self.reject()
    def test_native_ability_tasks_restore(self): self.report["cases"][0]["native_tasks_after"] = 4; self.reject()
    def test_subscription_scope_must_close(self): self.report["active_observation_scopes"] = 1; self.reject()
    def test_physical_keyboard_not_certified_by_software_injection(self): self.report["physical_keyboard_tested"] = True; self.reject()
    def test_private_input_selector_does_not_quit_normal_play_or_commandlets(self):
        from uep_lyra_hud.startup import validation_module
        self.assertIsNone(validation_module([])); self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterInputResult=x"]))
        self.assertEqual(validation_module(["-UEPCharacterInputResult=x"]), "uep_lyra_characters.enhanced_input_validation")

    def test_fixture_uses_native_injection_never_bp_probe_or_receiver_call(self):
        import ast
        from pathlib import Path
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/enhanced_input_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "call_function" and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertTrue(any(node.args[0].value == "InjectInputVectorForAction" for node in calls))
        self.assertFalse(any(node.args[0].value in {"SelectSlot", "ChangeQuickbarSlot", *(value[1] for value in ACTIONS.values())} for node in calls))

    def test_dynamic_binding_snapshot_copies_original_action_trigger_function_pod(self):
        import ast
        from pathlib import Path
        import types
        file = Path(__file__).resolve().parents[1]/"Tools/generate_character_inventory_assets.py"
        fn = next(node for node in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef) and node.name == "input_bindings")
        row = types.SimpleNamespace(InputAction=types.SimpleNamespace(get_path_name=lambda: "native-action"), TriggerEvent=1, FunctionNameToBind="native-receiver")
        cls = object()
        binding = types.SimpleNamespace(get_outer=lambda: cls, get_property=lambda name: [row])
        foreign = types.SimpleNamespace(get_outer=lambda: object(), get_property=lambda name: (_ for _ in ()).throw(AssertionError("another class's native input bindings were read")))
        namespace = dict(ue=types.SimpleNamespace(find_class=lambda name: name, tobject_iterator=lambda kind: [binding, foreign]))
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(file), "exec"), namespace)
        result = namespace["input_bindings"](cls); row.FunctionNameToBind = "changed"
        self.assertEqual(result, [dict(action="native-action", trigger=1, function="native-receiver")])
