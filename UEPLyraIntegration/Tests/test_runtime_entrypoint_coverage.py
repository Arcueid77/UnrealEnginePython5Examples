"""Original entry coverage uses the native effective Profile and typed target."""
import importlib.util
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
