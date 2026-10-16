"""Software material evidence rejects wrong matches, leaks and visual claims."""
import ast
import copy
from pathlib import Path
import sys
import types
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_characters import outline_contract as gate
from uep_lyra_hud.startup import validation_module


def report(local=True):
    rows = []
    for name, profile, kind, team, color, calls, target in gate.PLAN:
        controlled = local if target == "owner" else False
        exists = controlled or kind != "new"
        attached = kind == "attached" or (controlled and kind == "new")
        counters = dict(python_calls=calls*int(profile == "Python"), fallback_calls=calls*int(profile == "BlueprintFallback"),
            nonlocal_noops=calls*int(profile == "Python" and not controlled), materials_created=int(profile == "Python" and controlled and kind == "new"),
            blendables_added=int(profile == "Python" and controlled and kind == "new"), scalar_updates=calls*int(profile == "Python" and controlled),
            vector_updates=calls*int(profile == "Python" and controlled))
        rows.append(dict(name=name, profile=profile, kind=kind, team=team, color=list(color), calls=calls, target=target,
            locally_controlled=controlled, bp_reference_call=True, material_exists=exists,
            native_material_class="/Script/Engine.MaterialInstanceDynamic" if exists else None, material_parent=gate.PARENT if exists else None,
            scalar=float(team) if controlled else gate.SEED_TEAM if exists else None, vector=list(color) if controlled else list(gate.SEED_COLOR) if exists else None,
            same_material_across_repeats=True, native_gc_held_reference_survived=True, native_probe_class_cdo_survived_gc=True, blendable_count=int(attached),
            blendable_references_match=True, blendable_weights=[1.] if attached else [], counters=counters, original_field_camera_profile_restored=True))
    return dict(status="passed", retained_character_class=gate.CLASS, native_unpossessed_actor_created_destroyed=True,
        native_unpossessed_actor_local_control=False, native_owner_local_control=local, cases=rows,
        original_actor_camera_profile_cdo_inventory_restored=True, fixture_material_roots_created=1, fixture_material_roots_released=1,
        native_original_material_references_valid_after_gc=True, fixture_probe_class_roots_created=1, fixture_probe_class_roots_released=1,
        natural_startup_python_dispatch=dict(python_calls=1, fallback_calls=0, materials_created=int(local), blendables_added=int(local),
            scalar_updates=int(local), vector_updates=int(local), nonlocal_noops=int(not local)), natural_startup_material_exists=local,
        **{key: False for key in ("pixels_verified", "outline_rendering_verified", "material_replication_claimed", "whole_character_migrated", "full_acceptance", "production_roots_objects")})


class CharacterOutlineReportModels(unittest.TestCase):
    def test_eight_software_pairs_for_local_and_true_nonlocal_native_worlds(self):
        for local in (True, False): self.assertEqual(gate.validate(report(local))["native_bp_call_pairs"], 8)

    def test_missing_reordered_or_failed_cases_rejected(self):
        for mutate in (lambda r: r["cases"].pop(), lambda r: r["cases"].reverse(), lambda r: r.update(status="failed")):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_two_identically_wrong_native_parameters_fail(self):
        for field, actual in (("scalar", 9.), ("vector", [0., 0., 0., 0.]), ("material_parent", "wrong"), ("native_material_class", "wrong")):
            value = report()
            for row in value["cases"][:2]: row[field] = actual
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_nonlocal_material_updates_or_creation_are_rejected(self):
        for fields in (dict(material_exists=True), dict(locally_controlled=True)):
            value = report(); value["cases"][12].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][14]["scalar"] = 8.
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_detached_valid_mid_is_not_readded_and_repeated_call_does_not_duplicate(self):
        for index, fields in ((4, dict(blendable_count=1)), (6, dict(blendable_count=2)), (6, dict(same_material_across_repeats=False))):
            value = report(); value["cases"][index].update(fields)
            with self.subTest(index=index, fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_gc_camera_interface_refs_and_exact_selected_dispatch_required(self):
        for fields in (dict(native_gc_held_reference_survived=False), dict(blendable_references_match=False), dict(bp_reference_call=False), dict(blendable_weights=[.5])):
            value = report(); value["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][1]["counters"]["python_calls"] = 2
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_all_original_native_state_fixture_roots_and_owned_actor_restore_required(self):
        for fields in (dict(original_actor_camera_profile_cdo_inventory_restored=False), dict(fixture_material_roots_released=0),
                dict(native_original_material_references_valid_after_gc=False), dict(native_unpossessed_actor_created_destroyed=False)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_pixel_rendering_replication_and_whole_asset_claims_rejected(self):
        for key in ("pixels_verified", "outline_rendering_verified", "material_replication_claimed", "whole_character_migrated", "full_acceptance", "production_roots_objects"):
            value = report(); value[key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_ordinary_fixture_material_roots_release_even_if_camera_restore_fails(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/outline_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Trial")
        namespace = {}; exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        trial = namespace["Trial"].__new__(namespace["Trial"]); released = []
        trial.native_roots = [types.SimpleNamespace(is_rooted=lambda: True, remove_from_root=lambda: released.append(True))]
        trial.roots_released = 0
        def failed_restore(): raise RuntimeError("camera restore failed")
        trial.restore = failed_restore
        with self.assertRaisesRegex(RuntimeError, "camera restore failed"): trial.close()
        self.assertEqual((released, trial.roots_released), ([True], 1))

    def test_explicit_software_selector_is_disabled_for_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterOutlineResult=x"]), "uep_lyra_characters.outline_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterOutlineResult=x"]))

    def test_probe_class_is_owned_across_native_gc_and_root_released_once(self):
        for already_rooted in (False, True):
            actions = []
            cls = types.SimpleNamespace(get_cdo=lambda: "cdo", is_rooted=lambda: already_rooted,
                add_to_root=lambda: actions.append("add"), remove_from_root=lambda: actions.append("remove"))
            file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/outline_validation.py"
            tree = ast.parse(file.read_text(encoding="utf-8")); node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Caller")
            namespace = dict(ue=types.SimpleNamespace(load_class=lambda path: cls), PROBE="caller")
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), "exec"), namespace)
            caller = namespace["Caller"](); self.assertIs(caller.cls, cls); self.assertEqual(caller.object, "cdo")
            caller.close(); caller.close(); self.assertEqual(actions, [] if already_rooted else ["add", "remove"])

    def test_native_probe_gc_loss_or_unreleased_class_root_fails(self):
        value = report(); value["cases"][0]["native_probe_class_cdo_survived_gc"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_natural_original_bp_startup_cannot_be_replaced_by_manual_case_passes(self):
        for fields in (dict(python_calls=0), dict(fallback_calls=1), dict(materials_created=0)):
            value = report(); value["natural_startup_python_dispatch"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["fixture_probe_class_roots_released"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
