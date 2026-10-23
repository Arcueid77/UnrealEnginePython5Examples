"""Original entry coverage uses the native effective Profile and typed target."""
import importlib.util
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Tools"))
spec = importlib.util.spec_from_file_location("entry_coverage", Path(__file__).resolve().parents[1]/"Tools/audit_runtime_entrypoint_coverage.py")
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)


def fixture():
    entry = dict(id="entry", **{"class": "K2Node_FunctionEntry"}, properties={},
        pins=[dict(direction=1, category="exec", links=[dict(node="business")])])
    business = dict(id="business", **{"class": "K2Node_CallFunction"}, title="Native behavior", pins=[])
    original = dict(blueprints=[dict(path="/Game/Example.Example", graphs=[dict(name="Run", nodes=[entry, business])])])
    native = dict(assets=[dict(asset="/Game/Example.Example", version="0.11.0", profiles=dict(Python=dict(functions=[]), ADSPython=dict(functions=["Run"])),
        default_profile="Python", effective_cdo_profile="ADSPython", staged_wired_entries=[], typed_dispatch_bridges=[])])
    return original, native


class RuntimeEntryCoverage(unittest.TestCase):
    def test_effective_profile_not_shared_router_default_owns_original_entry(self):
        original, native = fixture()
        self.assertEqual(gate.audit(original, native)["entrypoints"][0]["disposition"], "python-routed")

    def test_actual_typed_static_target_is_visible_without_an_instance_router(self):
        original, native = fixture(); row = native["assets"][0]
        row.update(profiles={}, effective_cdo_profile=None, typed_dispatch_bridges=[dict(entry="Run", default_profile="Python",
            method="TypedRun", profiles=dict(Python=dict(functions=["TypedRun"])))])
        self.assertEqual(gate.audit(original, native)["entrypoints"][0]["disposition"], "staged-typed-script-dispatch-forwarder-review")
        row["typed_dispatch_bridges"][0]["default_profile"] = "BlueprintFallback"
        self.assertEqual(gate.audit(original, native)["entrypoints"][0]["disposition"], "unrouted-business-review")

    def test_original_business_without_an_effective_owner_remains_a_named_gap(self):
        original, native = fixture(); native["assets"][0]["effective_cdo_profile"] = "Python"
        value = gate.audit(original, native)
        self.assertEqual(value["counts"], {"unrouted-business-review": 1})
        self.assertFalse(value["runtime_acceptance"])
        self.assertFalse(value["full_acceptance"])


def graph(name, *targets):
    return dict(entry=name, graph=name, calls=[target["method"] for target in targets],
        call_targets=list(targets), calls_python_dispatch=[], reachable_execution_nodes=len(targets))


def call(method, owner=None, target=None):
    return dict(method=method, owner_class=owner, default_target_class=target)


class TransitiveEntryCoverage(unittest.TestCase):
    def setUp(self):
        self.original, self.native = fixture()
        self.asset = self.native["assets"][0]
        self.name = self.asset["asset"] + "_C"
        self.asset.update(original_class=self.name, ancestry=[self.name], effective_cdo_profile="Python",
            profiles=dict(Python=dict(functions=["Dispatch"])),
            staged_wired_entries=[graph("Run", call("Update")), graph("Update", call("Dispatch"))])

    def report(self):
        return gate.audit(self.original, self.native)["entrypoints"][0]

    def test_two_hops_record_qualified_witness_without_promoting_runtime_acceptance(self):
        row = self.report()
        self.assertEqual(row["disposition"], "staged-transitive-script-dispatch-review")
        self.assertEqual([s["method"] for s in row["transitive_python_routes"][0]["path"]], ["Run", "Update", "Dispatch"])
        self.assertFalse(gate.audit(self.original, self.native)["runtime_acceptance"])

    def test_cycle_does_not_hide_a_real_route_or_create_one(self):
        self.asset["staged_wired_entries"][1]["call_targets"].append(call("Run"))
        self.assertEqual(len(self.report()["transitive_python_routes"]), 1)
        self.asset["profiles"]["Python"]["functions"] = []
        self.assertEqual(self.report()["disposition"], "unrouted-business-review")

    def test_explicit_unknown_owner_does_not_borrow_self_method(self):
        self.asset["staged_wired_entries"][0]["call_targets"] = [call("Dispatch", "/Script/Other.Widget")]
        self.assertEqual(self.report()["disposition"], "unrouted-business-review")

    def test_missing_qualified_targets_cannot_use_legacy_call_names(self):
        del self.asset["staged_wired_entries"][0]["call_targets"]
        self.assertEqual(self.report()["disposition"], "unrouted-business-review")

    def test_inherited_body_is_followed_but_an_empty_child_override_stops_it(self):
        parent = dict(self.asset, asset="/Game/Parent.Parent", original_class="/Game/Parent.Parent_C",
            ancestry=["/Game/Parent.Parent_C"], profiles={}, staged_wired_entries=[graph("Update", call("Dispatch"))])
        self.native["assets"].append(parent)
        self.original["blueprints"].append(dict(path=parent["asset"], graphs=[]))
        self.asset["ancestry"].append(parent["original_class"])
        self.asset["staged_wired_entries"] = [graph("Run", call("Update"))]
        self.assertEqual(self.report()["disposition"], "staged-transitive-script-dispatch-review")
        self.asset["staged_wired_entries"].append(graph("Update"))
        self.assertEqual(self.report()["disposition"], "unrouted-business-review")

    def test_effective_profile_applies_to_ancestor_bindings_not_its_default(self):
        self.asset["profiles"] = {}
        self.asset["all_ancestor_bindings"] = [dict(target_class=self.name, default_profile="Python",
            profiles=dict(Python=["Dispatch"], ADSPython=[]))]
        self.asset["effective_cdo_profile"] = "ADSPython"
        self.assertEqual(self.report()["disposition"], "unrouted-business-review")
        self.asset["all_ancestor_bindings"][0]["profiles"]["ADSPython"] = ["Dispatch"]
        self.assertEqual(self.report()["transitive_python_routes"][0]["profile"], "ADSPython")

    def test_ambiguous_own_definition_does_not_select_an_arbitrary_body(self):
        self.asset["staged_wired_entries"].append(graph("Update"))
        self.assertEqual(self.report()["disposition"], "unrouted-business-review")

    def test_explicit_default_receiver_takes_priority_over_self_or_declared_owner(self):
        self.asset["staged_wired_entries"][0]["call_targets"] = [call("Dispatch", self.name, "/Script/Other.Object")]
        self.assertEqual(self.report()["disposition"], "unrouted-business-review")

    def test_duplicate_native_class_fails_instead_of_overwriting_evidence(self):
        self.native["assets"].append(dict(self.asset))
        with self.assertRaisesRegex(ValueError, "Duplicate native class"):
            gate.audit(self.original, self.native)


class RetainedNativeEntryReview(unittest.TestCase):
    def setUp(self):
        self.original, self.native = fixture()
        self.asset = self.native["assets"][0]
        self.asset.update(effective_cdo_profile="Python", staged_wired_entries=[graph("Run", call("NativeTransport", "/Script/Native.Type"))])
        self.asset["staged_wired_entries"][0]["reachable_node_classes"] = ["K2Node_CallFunction"]
        row = gate.audit(self.original, self.native)["entrypoints"][0]
        self.review = dict(asset=row["asset"], graph=row["graph"], entry=row["entry"],
            reason="Typed native transport remains intentionally unmixed.", historical_evidence_ledger="accepted.json",
            execution_shape=gate.execution_shape(row))

    def test_individual_source_review_stays_separate_from_runtime_acceptance(self):
        report = gate.audit(self.original, self.native, [self.review])
        self.assertEqual(report["counts"], {"retained-native-source-review": 1})
        self.assertFalse(report["runtime_acceptance"])
        self.assertFalse(report["full_acceptance"])

    def test_new_body_or_changed_owner_is_not_covered_by_old_source_review(self):
        for field, value in (("owner_class", "/Script/Different.Type"), ("method", "NewBusiness")):
            with self.subTest(field=field):
                native = copy.deepcopy(self.native)
                native["assets"][0]["staged_wired_entries"][0]["call_targets"][0][field] = value
                with self.assertRaisesRegex(ValueError, "body changed"):
                    gate.audit(self.original, native, [self.review])

    def test_duplicate_stale_or_undocumented_exemptions_fail(self):
        for reviews in ([self.review, self.review], [dict(self.review, entry="Missing")], [dict(self.review, reason="")]):
            with self.subTest(reviews=reviews):
                with self.assertRaises(ValueError):
                    gate.audit(self.original, self.native, reviews)
