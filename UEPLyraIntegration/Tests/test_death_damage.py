"""Native producer call-order model; not runtime acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class DeathDamage(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.native, structs = types.ModuleType("unreal_engine"), types.ModuleType("unreal_engine.structs")
        self.native.load_class = lambda path: path
        structs.GameplayTag = lambda **values: types.SimpleNamespace(**values)
        factory = types.SimpleNamespace(call_function=self.call)
        self.native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: factory)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/death_damage.py"
        spec = importlib.util.spec_from_file_location("death_damage_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": self.native, "unreal_engine.structs": structs}):
            spec.loader.exec_module(self.module)
        self.asc = types.SimpleNamespace(call_function=self.call)

    def call(self, name, *args):
        self.calls.append((name, args))
        return {"MakeEffectContext": "context", "MakeOutgoingSpec": "spec", "AssignTagSetByCallerMagnitude": "assigned"}.get(name)

    def test_only_native_gas_spec_produces_death(self):
        self.module.apply(self.asc, 100.)
        self.assertEqual([name for name, args in self.calls], ["MakeEffectContext", "MakeOutgoingSpec",
            "AssignTagSetByCallerMagnitude", "BP_ApplyGameplayEffectSpecToSelf"])
        self.assertEqual(self.calls[1][1], (self.module.DAMAGE, 1., "context"))
        self.assertEqual(self.calls[2][1][1].TagName, "SetByCaller.Damage")
        self.assertEqual(self.calls[2][1][2], 100.)
        self.assertEqual(self.calls[3][1], ("assigned",))

    def test_dead_pawn_rejected_before_native_calls(self):
        with self.assertRaises(RuntimeError): self.module.apply(self.asc, 0.)
        self.assertEqual(self.calls, [])
