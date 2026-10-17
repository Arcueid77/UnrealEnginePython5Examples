"""Immediate readiness checks preserve original ordering and deferred fallback."""
import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_legacy_player_info_mixin as legacy_models


class CharacterInventoryReadyPolicyModels(unittest.TestCase):
    def setUp(self):
        setup = legacy_models.CharacterLegacyPlayerInfoPolicyModels(); setup.setUp()
        parent = types.ModuleType("uep_lyra_characters.legacy_player_info_mixin")
        self.parent, self.fallback_parent = setup.python, setup.fallback
        parent.LyraCharacterLegacyPlayerInfoPythonProfile, parent.LyraCharacterLegacyPlayerInfoBlueprintFallbackProfile = self.parent, self.fallback_parent
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        engine = types.ModuleType("unreal_engine"); engine.find_class = lambda name: name
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/inventory_ready_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._inventory_ready_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {parent.__name__: parent, native.__name__: native, "unreal_engine": engine}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterInventoryReadyPythonProfile, self.module.LyraCharacterInventoryReadyBlueprintFallbackProfile
        self.calls = []; self.inventory, self.quickbar = object(), object()
        def component(name, cls):
            self.calls.append((name, cls)); return self.inventory if cls == "LyraInventoryManagerComponent" else self.quickbar
        self.controller = types.SimpleNamespace(call_function=component)
        def actor_call(name):
            self.calls.append((name,)); return self.controller if name == "GetController" else None
        self.actor = types.SimpleNamespace(call_function=actor_call, call_mixin_original=lambda name: self.calls.append(("original", name)))

    def test_immediate_controller_inventory_quickbar_then_virtual_grant(self):
        self.python.PythonExperienceReady(self.actor)
        self.assertEqual(self.calls, [("GetController",), ("GetComponentByClass", "LyraInventoryManagerComponent"), ("GetComponentByClass", "LyraQuickBarComponent"), ("AddInitialInventory",)])
    def test_missing_controller_preserves_original_deferred_wait(self):
        self.controller = None; self.python.PythonExperienceReady(self.actor)
        self.assertEqual(self.calls, [("GetController",), ("original", self.module.READY)])
    def test_missing_inventory_never_probes_quickbar_early(self):
        self.inventory = None; self.python.PythonExperienceReady(self.actor)
        self.assertEqual(len(self.calls), 3); self.assertEqual(self.module.evidence(self.actor)["missing_inventory"], 1)
    def test_missing_quickbar_falls_back_not_early_grant(self):
        self.quickbar = None; self.python.PythonExperienceReady(self.actor)
        self.assertEqual(self.calls[-1], ("original", self.module.READY)); self.assertEqual(self.module.evidence(self.actor)["immediate_grants"], 0)
    def test_repeated_ready_notifications_each_forward(self):
        self.python.PythonExperienceReady(self.actor); self.python.PythonExperienceReady(self.actor)
        self.assertEqual(self.calls.count(("AddInitialInventory",)), 2)
    def test_original_exact_no_argument_receiver_signature(self):
        for profile in (self.python, self.fallback):
            self.assertEqual(profile.PythonExperienceReady.override, self.module.READY)
            self.assertEqual(list(inspect.signature(profile.PythonExperienceReady).parameters), ["self"])
    def test_fallback_does_not_reimplement_readiness(self):
        self.fallback.PythonExperienceReady(self.actor); self.assertEqual(self.calls, [("original", self.module.READY)])
    def test_no_authority_guard_added_to_generated_callback(self):
        self.python.PythonExperienceReady(self.actor); self.assertNotIn(("HasAuthority",), self.calls)
    def test_no_original_call_after_immediate_python_forward(self):
        self.python.PythonExperienceReady(self.actor); self.assertFalse(any(value[0] == "original" for value in self.calls))
    def test_all_twenty_accepted_raw_aliases(self):
        for name, value in self.parent.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], value)
    def test_all_fifteen_prior_fallback_aliases(self):
        for name, value in self.fallback_parent.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.fallback.__dict__[name], value)
    def test_no_python_ticker_or_actor_root_for_original_deferred_wait(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/inventory_ready_mixin.py"
        source = file.read_text(encoding="utf-8"); self.assertNotIn("add_ticker", source); self.assertNotIn("add_to_root", source)
    def test_counters_retain_only_pod(self):
        self.python.PythonExperienceReady(self.actor); self.assertTrue(all(type(value) is int for value in self.module.evidence(self.actor).values()))
