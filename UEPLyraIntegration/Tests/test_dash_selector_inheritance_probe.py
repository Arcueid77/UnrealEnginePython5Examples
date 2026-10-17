"""Literal-only fixture policies/guards; native class hierarchy needs UE proof."""
import ast
import importlib.util
from pathlib import Path
import types
import unittest
import sys
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("dash_inheritance_model", ROOT/"Overlay/Content/Scripts/uep_lyra_abilities/dash_selector_probe_policy.py")
policy = importlib.util.module_from_spec(spec)
native = types.ModuleType("unreal_engine"); native.call_function_by_class = lambda *args: {"ReturnValue": 1023}
with patch.dict(sys.modules, {"unreal_engine": native}): spec.loader.exec_module(policy)


class DashInheritanceControlModels(unittest.TestCase):
    def check(self, profile, method, original, expected):
        calls = []
        obj = types.SimpleNamespace(call_mixin_original=lambda name: calls.append(name) or original)
        self.assertEqual(getattr(profile, method)(obj), expected); self.assertEqual(calls, [method])
    def test_ancestor_python_original_is_required(self): self.check(policy.AncestorPython, "AncestorValue", 17, 117)
    def test_child_python_original_is_required(self): self.check(policy.ChildPython, "ChildValue", 11, 211)
    def test_ancestor_fallback_retains_literal(self): self.check(policy.AncestorBlueprintFallback, "AncestorValue", 17, 17)
    def test_child_fallback_retains_literal(self): self.check(policy.ChildBlueprintFallback, "ChildValue", 11, 11)
    def test_parent_shared_original_is_lexical(self): self.check(policy.AncestorPython, "SharedValue", 23, 1023)
    def test_owned_shared_nested_shape(self):
        calls = []; obj = types.SimpleNamespace(call_mixin_original=lambda name: calls.append(name) or 37,
            get_class=lambda: types.SimpleNamespace(get_super_class=lambda: "parent"))
        self.assertEqual(policy.ChildPython.SharedValue(obj), 3097); self.assertEqual(calls, ["SharedValue", "SharedValue"])
    def test_inherited_shared_nested_shape(self):
        obj = types.SimpleNamespace(call_mixin_original=lambda name: 23, get_class=lambda: types.SimpleNamespace(get_super_class=lambda: "parent"))
        self.assertEqual(policy.ChildPython.SharedValue(obj), 3069)
    def test_parent_lifecycle_uses_its_shared_original(self):
        obj = types.SimpleNamespace(call_mixin_original=lambda name: 23)
        policy.AncestorPython.__init__(obj); policy.AncestorPython.__uep_mixin_teardown__(obj)
        self.assertEqual((obj._uep_probe_parent_init, obj._uep_probe_parent_teardown), (23, 23))
    def test_child_lifecycle_uses_its_shared_original(self):
        obj = types.SimpleNamespace(call_mixin_original=lambda name: 37)
        policy.ChildPython.__init__(obj); policy.ChildPython.__uep_mixin_teardown__(obj)
        self.assertEqual((obj._uep_probe_child_init, obj._uep_probe_child_teardown), (37, 37))
    def test_native_probe_checks_both_orders_and_rejections_without_gameplay_objects(self):
        text = (ROOT/"Tools/generate_mixin_inheritance_probe.py").read_text(encoding="utf-8"); ast.parse(text)
        for key in ("owned_shared_function_verified", "inherited_original_unwrapped", "ordinary_inherited_sibling_rejected", "reverse_order_values", "unregister_order_values"):
            self.assertIn(key, text)
        for forbidden in ("spawn_actor", "add_to_root", "GameplayEffect", "get_world"):
            self.assertNotIn(forbidden, text)
    def test_native_override_reuses_parent_signature_instead_of_new_output(self):
        tree = ast.parse((ROOT/"Tools/generate_mixin_inheritance_probe.py").read_text(encoding="utf-8"))
        constant = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "constant")
        source = ast.unparse(constant)
        self.assertIn("MemberParent=bp.ParentClass", source)
        self.assertIn("result.FunctionReference = entry.FunctionReference", source)
        create = next(node for node in ast.walk(constant) if isinstance(node, ast.If) and node.orelse)
        self.assertNotIn("node_create_pin", ast.unparse(ast.Module(body=create.body, type_ignores=[])))
        self.assertIn("node_create_pin", ast.unparse(ast.Module(body=create.orelse, type_ignores=[])))
