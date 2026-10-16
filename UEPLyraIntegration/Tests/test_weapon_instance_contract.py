"""Equipment report gate models, not native animation/lifecycle evidence."""
import copy
import ast
from pathlib import Path
import types
import unittest
from uep_lyra_weapons import weapon_instance_contract as gate


def report():
    result = dict(status="passed", error=None, cases=[], original_player_restored=True, original_cdo_selectors_restored=True,
        observer_profiles_restored=True, read_only_profile_observer=True, fixture_cdo_profile_selector_written=True,
        policy_shutdown=dict(errors=[], active_count=0, script_subscriptions_created=0))
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "lifecycle_called_by_probe",
        "animation_state_written_by_probe", "animation_assets_modified", "native_cpp_time_written", "death_branch_native_tested", "gc_stress_tested"): result[field] = False
    state = dict(tags=["native-style"], selected_layer="native-layer", linked_layer="native-layer", montage="native-montage", montage_playing=True, dead_or_dying=False)
    for name in gate.PLAN:
        row = dict(native_class="original-"+name, native_type_preserved=True, native_equipment_item_source_matches=True,
            native_outer_cpp_equip_time_observed=True, fixture_inventory_restored=True, instance_profile_switch_preserved_state=True,
            native_equip_callbacks=1, native_unequip_callbacks=1, equip=copy.deepcopy(state), unequip=copy.deepcopy(state),
            counters=dict(equips=1, unequips=1, tag_queries=1, layer_picks=2, montage_calls=2, fallback_equips=1, fallback_unequips=1, fallback_tag_queries=1))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(row), python=copy.deepcopy(row)))
    return result


class WeaponInstanceGate(unittest.TestCase):
    def test_missing_collected_proxy_is_optional_but_other_lookup_errors_propagate(self):
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_instance_validation.py"
        node = next(node for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef) and node.name == "optional_object")
        def missing(path): raise Exception("unable to find object "+path)
        native = types.SimpleNamespace(find_object=missing); namespace = dict(ue=native)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), "exec"), namespace)
        self.assertIsNone(namespace["optional_object"]("native-proxy"))
        def unexpected(path): raise RuntimeError("unexpected lookup failure")
        native.find_object = unexpected
        with self.assertRaisesRegex(RuntimeError, "unexpected lookup failure"): namespace["optional_object"]("native-proxy")

    def test_complete_matrix(self): self.assertEqual(gate.validate(report())["alive_native_family_pairs"], 4)

    def test_native_gc_requires_real_collection_and_exact_paused_state(self):
        value = report(); value["gc_stress_tested"] = True
        value["native_gc_cases"] = [dict(weapon=name, native_proxy_collected=True, paused_state_preserved=True,
            before=dict(playing=name != "netshooter"), after=dict(playing=name != "netshooter")) for name in gate.PLAN]
        self.assertTrue(gate.validate(value)["gc_stress_tested"])
        value["native_gc_cases"][0]["native_proxy_collected"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        value["native_gc_cases"][0]["native_proxy_collected"] = True
        value["native_gc_cases"][0]["after"]["playing"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_manual_lifecycle_and_animation_write(self):
        for field in ("lifecycle_called_by_probe", "animation_state_written_by_probe", "native_cpp_time_written"):
            value = report(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_native_layer_montage_and_outer_cpp_time(self):
        value = report(); value["cases"][0]["python"]["equip"]["linked_layer"] = None
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["python"]["unequip"]["montage_playing"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["python"]["native_outer_cpp_equip_time_observed"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_policy_path_duplicate_callback_and_cdo_restore(self):
        value = report(); value["cases"][0]["python"]["counters"]["equips"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["python"]["native_unequip_callbacks"] = 2
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["original_cdo_selectors_restored"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
