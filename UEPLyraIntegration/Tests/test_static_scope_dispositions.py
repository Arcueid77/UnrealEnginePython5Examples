import copy
import importlib.util
from pathlib import Path
import sys
import json
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
spec = importlib.util.spec_from_file_location("static_scope", Path(__file__).resolve().parents[1] / "Tools/audit_static_scope_dispositions.py")
scope = importlib.util.module_from_spec(spec); spec.loader.exec_module(scope)


def blueprint(index, business=False, interface=False):
    path = f"/Game/Scope/B{index}.B{index}"
    return dict(path=path, generated_class=path + "_C", parent_class="/Script/Engine.Actor", asset_class="Blueprint",
        blueprint_type=3 if interface else 0, graphs=[dict(id=f"graph{index}", name="Run",
            nodes=[{"id": f"node{index}", "class": "K2Node_CallFunction"}] if business else [{"id": f"entry{index}", "class": "K2Node_FunctionEntry"}])])


def fixture():
    blueprints = [blueprint(i, business=i < 246, interface=i >= 428) for i in range(471)]
    audit = dict(status="passed", errors=[], blueprints=blueprints,
        retained=[dict(path=f"/Game/Anim/ABP_{i}.ABP_{i}", reason="ABP retained by user scope") for i in range(20)])
    manifest = dict(runtime_candidates=246, configuration_only=182, retained=63, scope_review_candidates=11,
        migration_complete=False, assets=[dict(path=bp["path"], version="original") for bp in blueprints[:246]])
    return audit, manifest, copy.deepcopy(manifest)


class StaticScopeDispositionTests(unittest.TestCase):
    def test_every_exclusion_has_a_reason_without_accepting_runtime(self):
        report = scope.inspect(*fixture())
        self.assertEqual(report["disposition_counts"], {"configuration-only": 182, "retained": 63})
        self.assertEqual(len(report["dispositions"]), 245)
        self.assertTrue(all(row["reason"] for row in report["dispositions"]))
        self.assertFalse(report["runtime_acceptance"])
        self.assertFalse(report["full_acceptance"])

    def test_new_business_in_a_configuration_shell_changes_scope_and_fails(self):
        audit, manifest, initial = fixture()
        audit["blueprints"][246]["graphs"][0]["nodes"].append({"class": "K2Node_CallFunction"})
        with self.assertRaisesRegex(ValueError, "Runtime classification"):
            scope.inspect(audit, manifest, initial)

    def test_retained_configuration_child_keeps_its_runtime_parent_visible(self):
        audit, manifest, initial = fixture()
        audit["blueprints"][246]["parent_class"] = audit["blueprints"][0]["generated_class"]
        row = next(r for r in scope.inspect(audit, manifest, initial)["dispositions"] if r["asset"] == audit["blueprints"][246]["path"])
        self.assertEqual(row["inherited_runtime_candidate"], manifest["assets"][0]["path"])

    def test_duplicate_or_missing_asset_is_not_hidden_by_counts(self):
        for mutation in ("duplicate", "missing"):
            audit, manifest, initial = fixture()
            if mutation == "duplicate": audit["retained"][0]["path"] = audit["blueprints"][0]["path"]
            else: audit["blueprints"].pop()
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "491 assets"):
                scope.inspect(audit, manifest, initial)

    def test_cross_version_swap_fails_even_when_counts_are_preserved(self):
        audit, manifest, initial = fixture()
        manifest["assets"][0]["version"] = "changed"
        with self.assertRaisesRegex(ValueError, "paths/order/versions"):
            scope.inspect(audit, manifest, initial)

    def test_audit_errors_and_unexplained_abp_exemptions_fail(self):
        for mutation in ("errors", "reason"):
            audit, manifest, initial = fixture()
            if mutation == "errors": audit["errors"] = ["missing graph"]
            else: audit["retained"][0]["reason"] = "ignore"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                scope.inspect(audit, manifest, initial)

    def test_cyclic_shell_parent_chain_fails(self):
        audit, manifest, initial = fixture()
        shell = audit["blueprints"][246]; shell["parent_class"] = shell["generated_class"]
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            scope.inspect(audit, manifest, initial)

    def test_a_pass_flag_cannot_stand_in_for_frozen_source_inputs(self):
        _, manifest, initial = fixture()
        with self.assertRaisesRegex(ValueError, "Frozen original"):
            scope.verify_documentation(dict(status="passed", configuration_and_retained_reasons_documented=True), manifest, initial)

    def test_mismatched_excluded_asset_fails_without_modifying_either_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); reference = root / "reference"; stage = root / "stage"
            for folder in (reference, stage): (folder / "Content").mkdir(parents=True)
            original = reference / "Content/Shell.uasset"; copied = stage / "Content/Shell.uasset"
            original.write_bytes(b"original"); copied.write_bytes(b"changed")
            (stage / ".uep-lyra-full-stage.json").write_text(json.dumps(dict(source=str(reference / "Project.uproject"))), encoding="utf-8")
            report = dict(dispositions=[dict(asset="/Game/Shell.Shell")])
            with self.assertRaisesRegex(ValueError, "differs from reference"):
                scope.compare_source_copies(report, reference, stage)
            self.assertEqual(original.read_bytes(), b"original")
            self.assertEqual(copied.read_bytes(), b"changed")
