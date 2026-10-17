"""Possession factory policy models; actual native ingress is a separate gate."""
import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_inventory_wait_mixin as wait_models


class CharacterPossessedPolicyModels(unittest.TestCase):
    def setUp(self):
        setup = wait_models.CharacterInventoryWaitPolicyModels(); setup.setUp(); self.parent = setup.module
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        self.calls, self.authority = [], True
        self.proxy = types.SimpleNamespace(get_path_name=lambda: "actual-proxy", call_function=lambda name: self.calls.append((name,)))
        self.controller = types.SimpleNamespace(get_path_name=lambda: "actual-controller")
        engine = types.ModuleType("unreal_engine"); engine.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=self.factory))
        self.actor = types.SimpleNamespace(call_function=self.actor_call, call_mixin_original=lambda *args: self.calls.append(("original",)+args))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/possessed_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._possessed_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"uep_lyra_characters.inventory_wait_mixin": self.parent, native.__name__: native, "unreal_engine": engine}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterPossessedPythonProfile, self.module.LyraCharacterPossessedBlueprintFallbackProfile

    def factory(self, name, actor): self.calls.append((name, actor)); return self.proxy
    def actor_call(self, name, *args):
        self.calls.append((name,)+args)
        return self.authority if name == "HasAuthority" else None
    def start(self): self.python.ReceivePossessed(self.actor, self.controller)
    def stats(self): return self.module.evidence(self.actor)
    def test_authority_factory_bind_activate_order(self):
        self.start(); self.assertEqual(self.calls, [("HasAuthority",), ("WaitForExperienceReady", self.actor), (self.module.BIND, self.proxy), ("Activate",)])
    def test_non_authority_no_factory(self): self.authority = False; self.start(); self.assertEqual(self.calls, [("HasAuthority",)]); self.assertEqual(self.stats()["authority_noops"], 1)
    def test_null_controller_not_an_extra_gate(self): self.controller = None; self.start(); self.assertEqual(self.stats()["factories"], 1)
    def test_null_factory_not_bound_or_activated(self): self.proxy = None; self.start(); self.assertEqual(self.stats()["null_factories"], 1); self.assertEqual(len(self.calls), 2)
    def test_repeated_native_event_creates_independent_requests(self): self.start(); self.start(); self.assertEqual(self.stats()["factories"], 2); self.assertEqual(self.calls.count(("Activate",)), 2)
    def test_python_never_calls_original_possession(self): self.start(); self.assertFalse(any(value[0] == "original" for value in self.calls))
    def test_payload_and_proxy_evidence_are_pod(self): self.start(); self.assertEqual((self.stats()["last_controller"], self.stats()["last_proxy"]), ("actual-controller", "actual-proxy"))
    def test_no_parent_possession_added(self): self.start(); self.assertFalse(any("Parent" in value[0] for value in self.calls))
    def test_fallback_forwards_exact_controller(self): self.fallback.ReceivePossessed(self.actor, self.controller); self.assertEqual(self.calls, [("original", "ReceivePossessed", self.controller)])
    def test_exact_native_parameter_name(self):
        for cls in (self.python, self.fallback): self.assertEqual(list(inspect.signature(cls.ReceivePossessed).parameters), ["self", "NewController"])
    def test_twenty_two_accepted_python_aliases(self):
        for name, value in self.parent.LyraCharacterInventoryWaitPythonProfile.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], value)
    def test_seventeen_accepted_fallback_aliases(self):
        for name, value in self.parent.LyraCharacterInventoryWaitBlueprintFallbackProfile.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.fallback.__dict__[name], value)
    def test_no_python_callback_ticker_or_proxy_root(self):
        source = inspect.getsource(self.module)
        for value in ("add_ticker", "add_to_root", "bind_event", "lambda", "CancelLatentActions"): self.assertNotIn(value, source)
