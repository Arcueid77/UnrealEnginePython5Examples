"""Reject genuine routing gaps while retaining explicit source-only dispositions."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("coverage_review", Path(__file__).resolve().parents[1]/"Tools/review_runtime_mixin_coverage.py")
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)


def row(asset="/Game/Example.Example"):
    return dict(asset=asset, version="0.11.0", original_class=asset+"_C", class_identity_preserved=True,
        native_router_class=asset+"_C", effective_cdo_profile="Python", profiles=dict(Python=dict(functions=["Run"])),
        unimplemented_union_methods=[], staged_wired_entries=[], all_ancestor_bindings=[], typed_dispatch_bridges=[])


def family_rows():
    parent = row(gate.WIDGET)
    parent["unimplemented_union_methods"] = list(gate.ADS_GATES | gate.EMOTE_GATES)
    parent["staged_wired_entries"] = [dict(entry=name, calls=[], reachable_node_classes=["K2Node_FunctionResult"])
        for name in parent["unimplemented_union_methods"]]
    ads = row(gate.ADS); ads.update(effective_cdo_profile="ADSPython", profiles=dict(ADSPython=dict(functions=list(gate.ADS_GATES))),
        unimplemented_union_methods=list(gate.EMOTE_GATES))
    ads["staged_wired_entries"] = [dict(entry="Activate", calls=list(gate.ADS_GATES), reachable_node_classes=["K2Node_CallFunction"])]
    return {gate.WIDGET: parent, gate.ADS: ads}


class CoverageReview(unittest.TestCase):
    def test_unused_family_stubs_use_effective_child_profile(self):
        values = family_rows()
        for value in values.values():
            self.assertEqual(gate.classify(value, values), "native-python-router-with-reviewed-family-stubs")

    def test_reject_referenced_missing_gate_nonempty_stub_and_new_missing_business(self):
        for change in ("referenced", "nonempty", "new-business", "wrong-profile"):
            values = family_rows(); ads = values[gate.ADS]
            if change == "referenced": ads["staged_wired_entries"][0]["calls"].append(next(iter(gate.EMOTE_GATES)))
            elif change == "nonempty": values[gate.WIDGET]["staged_wired_entries"][0]["reachable_node_classes"] = ["K2Node_VariableSet"]
            elif change == "new-business": ads["unimplemented_union_methods"].append("CheckAmmoState")
            else: ads["effective_cdo_profile"] = "Python"
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.classify(ads if change != "nonempty" else values[gate.WIDGET], values)

    def test_static_dispatch_requires_every_actual_registered_python_target(self):
        asset = "/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions"
        value = row(asset); value["native_router_class"] = None
        value["typed_dispatch_bridges"] = [dict(method=method, target=target, default_profile="Python",
            profiles=dict(Python=dict(functions=[method]))) for method, target in gate.static_targets(asset).items()]
        self.assertEqual(gate.classify(value, {}), "typed-static-python-forwarding")
        for change in ("missing", "wrong-target", "fallback", "unimplemented"):
            bad = copy.deepcopy(value)
            if change == "missing": bad["typed_dispatch_bridges"].pop()
            elif change == "wrong-target": bad["typed_dispatch_bridges"][0]["target"] = "/Game/Foreign.Foreign_C"
            elif change == "fallback": bad["typed_dispatch_bridges"][0]["default_profile"] = "BlueprintFallback"
            else: bad["typed_dispatch_bridges"][0]["profiles"]["Python"]["functions"] = []
            with self.subTest(change=change), self.assertRaises(ValueError): gate.classify(bad, {})

    def test_retained_shell_rejects_independent_business(self):
        value = row(gate.CHARACTER); value["native_router_class"] = None
        value["staged_wired_entries"] = [dict(entry="UserConstructionScript", calls=["UserConstructionScript"],
            reachable_node_classes=["K2Node_CallParentFunction"])]
        self.assertEqual(gate.classify(value, {}), "retained-empty-native-parent-shell")
        value["staged_wired_entries"][0]["reachable_node_classes"].append("K2Node_VariableSet")
        with self.assertRaises(ValueError): gate.classify(value, {})
        value = row(gate.PROMPT); value["native_router_class"] = None
        value["staged_wired_entries"] = [dict(entry="BindIndicator", calls=[], reachable_node_classes=["K2Node_DynamicCast"])]
        self.assertEqual(gate.classify(value, {}), "retained-unobservable-prompt-shell")
        value["staged_wired_entries"][0]["calls"] = ["SetVisibility"]
        with self.assertRaises(ValueError): gate.classify(value, {})

    def test_inherited_forwarder_needs_complete_parent_methods(self):
        value = row(next(iter(gate.FORWARDERS)))
        value["all_ancestor_bindings"] = [dict(target_class=gate.PARENT, profiles=dict(Python=list(gate.PARENT_METHODS)))]
        self.assertEqual(gate.classify(value, {}), "retained-forwarder-inherited-python-parent")
        value["all_ancestor_bindings"][0]["profiles"]["Python"].pop()
        with self.assertRaises(ValueError): gate.classify(value, {})

    def test_unknown_unrouted_candidate_and_changed_identity_are_rejected(self):
        value = row(); value["native_router_class"] = None
        with self.assertRaises(ValueError): gate.classify(value, {})
        value = row(); value["original_class"] = "/Game/Replacement.Replacement_C"
        with self.assertRaises(ValueError): gate.classify(value, {})

    def test_complete_inventory_review_never_claims_gameplay_completion(self):
        rows = [row(f"/Game/A{i}.A{i}") for i in range(246)]
        coverage = dict(status="passed", all_original_candidates=True, coverage_is_registration_not_gameplay=True,
            runtime_acceptance=False, full_acceptance=False, assets=rows)
        manifest = dict(assets=[dict(path=value["asset"], version=value["version"]) for value in rows])
        result = gate.review(coverage, manifest)
        self.assertFalse(result["full_migration_acceptance_proven"])
        self.assertFalse(result["native_business_executed"])
        self.assertTrue(all(not value["gameplay_completion_proven"] for value in result["candidates"]))
        manifest["assets"].reverse()
        with self.assertRaises(ValueError): gate.review(coverage, manifest)
