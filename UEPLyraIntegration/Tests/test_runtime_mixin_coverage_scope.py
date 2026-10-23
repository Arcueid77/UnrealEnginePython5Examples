"""Exercise both native audit scopes without starting UE or gameplay policies."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

TOOL = Path(__file__).resolve().parents[1]/"Tools/audit_runtime_mixin_coverage.py"


class Profile:
    def __init__(self): raise AssertionError("a metadata audit must not instantiate gameplay policies")


class NativeClass:
    def __init__(self, name): self.name = name
    def get_path_name(self): return self.name
    def is_valid(self): return True
    def get_super_class(self): return None
    def get_cdo(self): return self
    def properties(self): return ["PythonMixinProfile"]


class RuntimeCoverageScope(unittest.TestCase):
    def run_audit(self, all_candidates, *, duplicate=False, drop=False, bridge=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); stage = root/"Stage"; stage.mkdir()
            script = root/"Tools/audit_runtime_mixin_coverage.py"; script.parent.mkdir()
            manifest = root/"Migration/batches.json"; manifest.parent.mkdir()
            assets = [dict(path=f"/Game/V{version}/Asset{i}.Asset{i}", version=version, status="bounded")
                for version, count in (("0.9.0", 5), ("0.10.0", 32), ("0.11.0", 37), ("0.12.0", 75), ("0.13.0", 57), ("0.14.0", 40))
                for i in range(count)]
            if duplicate: assets[1]["path"] = assets[0]["path"]
            if drop: assets.pop()
            manifest.write_text(json.dumps(dict(assets=assets)), encoding="utf-8")
            for asset in assets:
                file = stage/"Content"/(asset["path"].split(".", 1)[0].split("/", 2)[2]+".uasset")
                file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(b"original-asset")
            classes = {asset["path"]+"_C": NativeClass(asset["path"]+"_C") for asset in assets}
            first = classes[assets[0]["path"]+"_C"]; calls = []
            def effective(cdo): calls.append(cdo); return "ADSPython"
            binding = dict(target_class=first, default_profile="Python", mixin_set=None, functions=["BaseUI", "Slot"],
                profiles=dict(Python=dict(python_class=Profile, functions=["BaseUI"]),
                    ADSPython=dict(python_class=Profile, functions=["BaseUI", "Slot"])))
            ue = SimpleNamespace(convert_relative_path_to_full=lambda value: value, get_content_dir=lambda: str(stage/"Content"),
                load_class=classes.get, register_loaded_mixin_interfaces=lambda: None,
                get_registered_mixins=lambda: [binding], get_mixin_profile=effective)
            def wired(asset, functions, include_targets):
                if not bridge or asset != assets[0]["path"]: return []
                return [dict(entry="StaticCaller", call_targets=[dict(method="Slot", owner_class=first.get_path_name(), default_target_class=None)])]
            tree = ast.parse(TOOL.read_text(encoding="utf-8-sig"))
            functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ("relative_asset", "valid", "audit")]
            namespace = dict(Path=Path, hashlib=hashlib, json=json, ue=ue, script=str(script),
                sys=SimpleNamespace(argv=["audit", "-UEPCoverageAllCandidates"] if all_candidates else ["audit"]),
                arg=lambda name: str(stage), require_authoring_stage=lambda *args: stage,
                RETAINED=set(), wired_entries=wired)
            exec(compile(ast.Module(body=functions, type_ignores=[]), str(TOOL), "exec"), namespace)
            return namespace["audit"](), len(calls)

    def test_original_37_candidate_scope_does_not_resolve_instance_selectors(self):
        report, calls = self.run_audit(False)
        self.assertEqual(len(report["assets"]), 37)
        self.assertEqual(report["current_versions"], ["0.9.0", "0.10.0"])
        self.assertEqual(calls, 0)
        self.assertEqual(report["assets"][0]["unimplemented_union_methods"], ["Slot"])

    def test_all_246_candidates_preserve_scope_after_effective_profile_resolution(self):
        report, calls = self.run_audit(True)
        self.assertEqual(len(report["assets"]), 246)
        self.assertEqual(len(report["current_versions"]), 6)
        self.assertEqual(calls, 1)
        self.assertEqual(report["assets"][0]["effective_cdo_profile"], "ADSPython")
        self.assertEqual(report["assets"][0]["unimplemented_union_methods"], [])
        self.assertFalse(report["runtime_acceptance"])
        self.assertFalse(report["full_acceptance"])

    def test_duplicate_and_missing_candidates_fail_scope_check(self):
        for options in (dict(duplicate=True), dict(drop=True)):
            with self.subTest(options=options), self.assertRaisesRegex(RuntimeError, "coverage scope changed"):
                self.run_audit(True, **options)

    def test_static_call_records_actual_registered_helper_target(self):
        report, _ = self.run_audit(True, bridge=True)
        bridge, = report["assets"][0]["typed_dispatch_bridges"]
        self.assertEqual(bridge["entry"], "StaticCaller")
        self.assertEqual(bridge["method"], "Slot")
        self.assertEqual(bridge["target"], report["assets"][0]["original_class"])
