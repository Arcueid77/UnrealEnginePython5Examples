"""Character choice native-call models; no claim of native part replication."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CosmeticPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.added, self.actor_count, self.random_value = [], [], 5, False
        native, structs = types.ModuleType("unreal_engine"), types.ModuleType("unreal_engine.structs")
        structs.LyraCharacterPart = lambda **values: types.SimpleNamespace(**values)
        native.load_class = lambda path: path
        def call(name, *args):
            self.calls.append((name, args))
            if name == "GetAllActorsOfClass": return ([object() for _ in range(self.actor_count)],)
            if name == "Percent_IntInt": return args[0] % args[1] if args[1] else 0
            if name == "RandomBool": return self.random_value
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=call)) if name != "LyraCharacter" else "native-LyraCharacter"
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/cosmetics_mixin.py"
        spec = importlib.util.spec_from_file_location("cosmetic_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs}): spec.loader.exec_module(self.module)
        self.component = types.SimpleNamespace(AvailableCharacterParts=["part0", "part1", "part2"],
            call_function=lambda name, part: self.added.append((name, part)))

    def test_native_actor_count_remainder_selects_original_class(self):
        self.module.select(self.component)
        self.assertEqual(self.calls[0][1], (self.component, "native-LyraCharacter"))
        self.assertEqual(self.calls[1], ("Percent_IntInt", (5, 3)))
        self.assertEqual((self.added[0][0], self.added[0][1].PartClass, self.added[0][1].CollisionMode), ("AddCharacterPart", "part2", 0))

    def test_random_both_original_boolean_branches_use_native_rng(self):
        for value, cls in ((False, self.module.MANNY), (True, self.module.QUINN)):
            self.random_value = value; self.module.random_select(self.component)
            self.assertEqual(self.added[-1][1].PartClass, cls)
        self.assertEqual([name for name, args in self.calls], ["RandomBool", "RandomBool"])

    def test_empty_parts_use_native_diagnostic_default_without_python_exception(self):
        self.component.AvailableCharacterParts = []
        self.module.select(self.component)
        self.assertEqual(self.calls[-1], ("Percent_IntInt", (5, 0)))
        self.assertIsNone(self.added[-1][1].PartClass)

    def test_fallback_runs_retained_original_beginplay(self):
        calls = []; obj = types.SimpleNamespace(call_mixin_original=lambda name: calls.append(name))
        self.module.LyraCharacterSelectionBlueprintFallbackProfile.ReceiveBeginPlay(obj)
        self.module.LyraRandomCharacterBlueprintFallbackProfile.ReceiveBeginPlay(obj)
        self.assertEqual(calls, ["ReceiveBeginPlay", "ReceiveBeginPlay"])
