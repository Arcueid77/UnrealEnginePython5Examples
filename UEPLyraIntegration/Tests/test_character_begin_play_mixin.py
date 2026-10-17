"""Ordered BeginPlay policy and synchronous test-CDO restoration models."""
import ast
from contextlib import contextmanager
import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_visibility_mixin as visibility_models


class CharacterBeginPlayPolicyModels(unittest.TestCase):
    def setUp(self):
        setup = visibility_models.CharacterVisibilityPolicyModels(); setup.setUp(); self.parent = setup.module; self.calls = []
        engine, structs = types.ModuleType("unreal_engine"), types.ModuleType("unreal_engine.structs")
        structs.GameplayTag = lambda **args: types.SimpleNamespace(**args)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/begin_play_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._begin_play_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"uep_lyra_characters.visibility_mixin": self.parent, "unreal_engine": engine, structs.__name__: structs}): spec.loader.exec_module(self.module)
        self.component = object(); self.actor = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args),
            get_property=lambda name: self.component, call_mixin_original=lambda *args: self.calls.append(("original",)+args))
        self.python, self.fallback = self.module.LyraCharacterBeginPlayPythonProfile, self.module.LyraCharacterBeginPlayBlueprintFallbackProfile
    def test_exact_parent_listener_hide_register_order(self):
        self.python.ReceiveBeginPlay(self.actor)
        self.assertEqual([value[0] for value in self.calls], [self.module.PARENT, "ListenForTeam", "SetActorHiddenInGame", self.parent.REGISTER])
        self.assertEqual(self.calls[2], ("SetActorHiddenInGame", True)); self.assertIs(self.calls[3][1], self.component)
        self.assertEqual(self.calls[3][2].TagName, "InitState.GameplayReady"); self.assertIs(self.calls[3][3], True)
    def test_no_original_fallthrough(self): self.python.ReceiveBeginPlay(self.actor); self.assertFalse(any(value[0] == "original" for value in self.calls))
    def test_fallback_calls_untouched_original_once(self): self.fallback.ReceiveBeginPlay(self.actor); self.assertEqual(self.calls, [("original", "ReceiveBeginPlay")])
    def test_native_zero_parameter_signature(self):
        for cls in (self.python, self.fallback): self.assertEqual(list(inspect.signature(cls.ReceiveBeginPlay).parameters), ["self"])
    def test_twenty_five_prior_methods_are_raw_aliases(self):
        for name, method in self.parent.LyraCharacterVisibilityPythonProfile.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], method)
    def test_no_ticker_root_or_callback_closure(self):
        source = inspect.getsource(self.module)
        for name in ("add_ticker", "add_to_root", "bind_event", "lambda"): self.assertNotIn(name, source)


class CharacterBeginPlayFixtureModels(unittest.TestCase):
    def setUp(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/begin_play_observation.py"
        fn = next(node for node in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef) and node.name == "default_profile")
        def require(value, message):
            if not value: raise RuntimeError(message)
        namespace = dict(contextmanager=contextmanager, require=require)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(file), "exec"), namespace); self.scope = namespace["default_profile"]
        self.fields = dict(PythonMixinProfile="Python")
        cdo = types.SimpleNamespace(get_property=lambda name: self.fields[name], set_property=lambda name, value: self.fields.__setitem__(name, value))
        self.cls = types.SimpleNamespace(get_cdo=lambda: cdo)
    def test_default_only_changes_inside_synchronous_spawn_scope(self):
        with self.scope(self.cls, "BlueprintFallback"): self.assertEqual(self.fields["PythonMixinProfile"], "BlueprintFallback")
        self.assertEqual(self.fields["PythonMixinProfile"], "Python")
    def test_default_restores_on_spawn_failure(self):
        with self.assertRaises(RuntimeError):
            with self.scope(self.cls, "BlueprintFallback"): raise RuntimeError("simulated native spawn failure")
        self.assertEqual(self.fields["PythonMixinProfile"], "Python")
