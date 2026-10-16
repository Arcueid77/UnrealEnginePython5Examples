"""Effect-pad intent contracts; fakes are not native GAS/overlap evidence."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"
sys.path.insert(0, str(SCRIPTS))


class Object:
    def __init__(self):
        self.calls = []

    def call_function(self, *values):
        self.calls.append(values)


class EffectPadContracts(unittest.TestCase):
    def setUp(self):
        self.asc = Object()
        self.library_calls = []
        self.context = object()
        native = types.ModuleType("unreal_engine")
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: self)
        native.find_struct = lambda name: lambda: self.context
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        spec = importlib.util.spec_from_file_location("_effect_pad_contract", SCRIPTS / "uep_lyra_world" / "effect_pad_mixin.py")
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)
        self.pad = self.module.LyraEffectPadPythonProfile()
        self.pad.GE_Damage, self.pad.GE_Heal = object(), object()
        self.pad.MAT_DamagePad, self.pad.MAT_HealPad, self.pad.MAT_SpecialPad = object(), object(), object()
        self.pad.GameplayEffectToApply = self.pad.GE_Heal
        self.pad.Pad, self.pad.Text = Object(), Object()

    def call_function(self, name, argument):
        self.library_calls.append((name, argument))
        return self.asc if name == "GetAbilitySystemComponent" else "Special Effect"

    def test_construct_heal_and_damage_preserves_material_and_text(self):
        for effect, material, text in ((self.pad.GE_Heal, self.pad.MAT_HealPad, "HEAL"),
                                       (self.pad.GE_Damage, self.pad.MAT_DamagePad, "DAMAGE")):
            self.pad.GameplayEffectToApply = effect
            self.pad.UserConstructionScript()
            self.assertEqual(self.pad.Pad.calls[-1], ("CreateDynamicMaterialInstance", 0, material))
            self.assertEqual(self.pad.Text.calls[-1], ("K2_SetText", text))
        self.assertEqual(self.pad._uep_effect_pad_constructions, 2)

    def test_special_branch_alone_sets_world_size(self):
        self.pad.GameplayEffectToApply = object()
        self.pad.UserConstructionScript()
        self.assertEqual(self.pad.Text.calls, [("K2_SetText", "Special Effect"), ("SetWorldSize", 20.0)])

    def test_invalid_effect_construction_is_an_authored_noop(self):
        self.pad.GameplayEffectToApply = None
        self.pad.UserConstructionScript()
        self.assertEqual(self.pad.Pad.calls + self.pad.Text.calls, [])
        self.assertEqual(self.pad._uep_effect_pad_constructions, 0)

    def test_begin_uses_authored_zero_level_and_empty_context(self):
        actor = object()
        self.pad.BeginOverlap(None, actor, None, 0, False, None)
        self.assertEqual(self.library_calls, [("GetAbilitySystemComponent", actor)])
        self.assertEqual(self.asc.calls, [("BP_ApplyGameplayEffectToSelf", self.pad.GE_Heal, 0.0, self.context)])
        self.assertEqual(self.pad._uep_effect_pad_begin_intents, 1)

    def test_end_removes_by_class_without_source_filter_and_all_stacks(self):
        self.pad.EndOverlap(None, object(), None, 0)
        self.assertEqual(self.asc.calls, [("RemoveActiveGameplayEffectBySourceEffect", self.pad.GE_Heal, None, -1)])
        self.assertEqual(self.pad._uep_effect_pad_end_intents, 1)

    def test_actor_without_asc_does_not_apply_or_remove(self):
        self.asc = None
        self.pad.BeginOverlap(None, object(), None, 0, False, None)
        self.pad.EndOverlap(None, object(), None, 0)
        self.assertEqual(self.pad._uep_effect_pad_begin_intents, 0)
        self.assertEqual(self.pad._uep_effect_pad_end_intents, 0)

    def test_fallback_forwards_each_saved_entry_exactly_once(self):
        pad = self.module.LyraEffectPadBlueprintFallbackProfile()
        calls = []
        pad.call_mixin_original = lambda *values: calls.append(values)
        pad.UserConstructionScript()
        pad.BeginOverlap(1, 2, 3, 4, True, 6)
        pad.EndOverlap(1, 2, 3, 4)
        self.assertEqual(calls, [(self.module.CONSTRUCT_FUNCTION,), (self.module.BEGIN_EVENT, 1, 2, 3, 4, True, 6),
                                 (self.module.END_EVENT, 1, 2, 3, 4)])

    def test_construction_profiles_target_virtual_helper_not_parent_pointer(self):
        for cls in (self.module.LyraEffectPadPythonProfile, self.module.LyraEffectPadBlueprintFallbackProfile):
            self.assertEqual(cls.UserConstructionScript.override, self.module.CONSTRUCT_FUNCTION)


if __name__ == "__main__":
    unittest.main()
