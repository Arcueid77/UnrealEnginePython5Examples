"""Inherited native iteration policy; host fake calls are not gameplay proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_begin_play_mixin as begin_models


class CharacterEquipmentHidePolicyModels(unittest.TestCase):
    def setUp(self):
        setup = begin_models.CharacterBeginPlayPolicyModels(); setup.setUp(); self.parent = setup.module
        self.calls, self.actors = [], []
        self.weapon = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.instance = types.SimpleNamespace(call_function=lambda name: self.actors)
        self.instances = [self.instance]; self.manager = types.SimpleNamespace(call_function=lambda *args: self.instances)
        self.actor = types.SimpleNamespace(call_function=lambda *args: self.manager, call_mixin_original=lambda *args: self.calls.append(("original",)+args))
        engine = types.ModuleType("unreal_engine"); engine.find_class = lambda name: name
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/equipment_hide_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._equipment_hide_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"uep_lyra_characters.begin_play_mixin": self.parent, "unreal_engine": engine, native.__name__: native}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterEquipmentHidePythonProfile, self.module.LyraCharacterEquipmentHideBlueprintFallbackProfile
    def start(self): self.python.HideEquippedWeapons(self.actor)
    def test_native_spawned_actor_is_hidden(self): self.actors = [self.weapon]; self.start(); self.assertEqual(self.calls, [("SetActorHiddenInGame", True)])
    def test_missing_manager_noop(self): self.manager = None; self.start(); self.assertEqual(self.module.evidence(self.actor)["missing_manager_noops"], 1)
    def test_empty_equipment_noop(self): self.instances = []; self.start(); self.assertEqual(self.module.evidence(self.actor)["instances"], 0)
    def test_empty_actor_list_noop(self): self.start(); self.assertFalse(self.calls)
    def test_each_native_equipment_instance_and_actor_visited(self): self.instances = [self.instance]*2; self.actors = [self.weapon]*3; self.start(); self.assertEqual(len(self.calls), 6)
    def test_repeated_requests_do_not_skip_native_calls(self): self.actors = [self.weapon]; self.start(); self.start(); self.assertEqual(len(self.calls), 2)
    def test_null_reference_keeps_bp_noop_effect(self): self.actors = [None, self.weapon]; self.start(); self.assertEqual(self.module.evidence(self.actor)["null_actor_noops"], 1); self.assertEqual(len(self.calls), 1)
    def test_python_never_runs_original(self): self.start(); self.assertFalse(any(value[0] == "original" for value in self.calls))
    def test_fallback_calls_exact_inherited_original(self): self.fallback.HideEquippedWeapons(self.actor); self.assertEqual(self.calls, [("original", "HideEquippedWeapons")])
    def test_no_additional_authority_guard(self):
        calls = []
        self.actor.call_function = lambda *args: calls.append(args) or self.manager
        self.start(); self.assertEqual(calls, [("GetComponentByClass", "LyraEquipmentManagerComponent")])
    def test_previous_twenty_six_methods_raw_aliases(self):
        for name, method in self.parent.LyraCharacterBeginPlayPythonProfile.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], method)
