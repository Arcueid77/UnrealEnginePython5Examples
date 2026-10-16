"""Equipment native-call models; not proof of actual linked layers/montages."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class WeaponInstancePolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.dead, self.layer, self.parts_present = [], False, "native-layer", True
        native, structs, helpers = (types.ModuleType(name) for name in ("unreal_engine", "unreal_engine.structs", "uep_lyra_world.effect_pad_mixin"))
        helpers.valid = lambda value: value is not None
        structs.GameplayTag = lambda **values: types.SimpleNamespace(**values)
        def factory(name, *args):
            self.calls.append((name, args))
            if name == "IsValidClass": return args[0] is not None
            return object()
        native.find_class = lambda name: name if name in ("Character", "LyraPawnComponent_CharacterParts") else types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=factory))
        native.load_class = lambda name: "native-hero-class"
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_instance_mixin.py"
        spec = importlib.util.spec_from_file_location("weapon_instance_model", path); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs, "uep_lyra_world.effect_pad_mixin": helpers}): spec.loader.exec_module(self.module)
        self.parts = types.SimpleNamespace(call_function=lambda name, tag: self.calls.append((name, tag.TagName)) or "native-style-tags")
        self.health = types.SimpleNamespace(call_function=lambda name: self.dead)
        self.pawn = types.SimpleNamespace(Mesh=types.SimpleNamespace(call_function=factory), HealthComponent=self.health,
            get_component_by_type=lambda cls: self.parts if self.parts_present else None)
        self.instance = types.SimpleNamespace(CosmeticAnimStyleTags="cached-tags", WeaponEquipMontage="original-equip", WeaponUnequipMontage="original-unequip",
            get_path_name=lambda: "native-instance", call_function=self.call, call_mixin_original=lambda *args: self.calls.append(("original", args)))

    def call(self, name, *args):
        self.calls.append((name, args))
        if name in ("GetPawn", "GetTypedPawn"): return self.pawn
        if name == "PickBestAnimLayer": return self.layer
        if name == "DetermineCosmeticTags": self.module.determine_tags(self.instance)

    def test_equip_uses_native_style_prefix_layer_and_original_proxy_pins(self):
        self.module.LyraWeaponInstancePythonProfile.K2_OnEquipped(self.instance)
        self.assertEqual(self.instance.CosmeticAnimStyleTags, "native-style-tags")
        self.assertIn(("GetCombinedTags", "Cosmetic.AnimationStyle"), self.calls)
        self.assertIn(("PickBestAnimLayer", (True, "native-style-tags")), self.calls)
        self.assertIn(("LinkAnimClassLayers", ("native-layer",)), self.calls)
        args = next(args for name, args in self.calls if name == "CreateProxyObjectForPlayMontage")
        self.assertEqual(args, (self.pawn.Mesh, "original-equip", 1., 0., "None", True))

    def test_invalid_parts_preserve_original_cached_tags(self):
        self.parts_present = False; self.module.determine_tags(self.instance)
        self.assertEqual(self.instance.CosmeticAnimStyleTags, "cached-tags")

    def test_missing_layer_still_calls_original_native_montage_factory(self):
        self.layer = None; self.module.LyraWeaponInstancePythonProfile.K2_OnUnequipped(self.instance)
        self.assertFalse(any(name == "LinkAnimClassLayers" for name, args in self.calls))
        self.assertTrue(any(name == "CreateProxyObjectForPlayMontage" and args[1] == "original-unequip" for name, args in self.calls))

    def test_dead_unequip_skips_layer_and_montage(self):
        self.dead = True; self.module.LyraWeaponInstancePythonProfile.K2_OnUnequipped(self.instance)
        self.assertFalse(any(name in ("PickBestAnimLayer", "CreateProxyObjectForPlayMontage") for name, args in self.calls))
        self.assertEqual(self.module.snapshot()["dead_unequips_skipped"], 1)

    def test_fallback_calls_retained_original_not_python_animation(self):
        self.module.LyraWeaponInstanceBlueprintFallbackProfile.K2_OnEquipped(self.instance)
        self.module.LyraWeaponInstanceBlueprintFallbackProfile.K2_OnUnequipped(self.instance)
        self.assertEqual([args for name, args in self.calls if name == "original"], [("K2_OnEquipped",), ("K2_OnUnequipped",)])
        self.assertEqual(self.module.snapshot()["montage_calls"], 0)

    def test_metadata_history_is_bounded_and_contains_no_uobject(self):
        for index in range(300): self.module.note(types.SimpleNamespace(get_path_name=lambda value=index: str(value)), "equips")
        self.assertEqual(len(self.module._counts), 256)
        self.assertEqual(self.module.snapshot()["script_subscriptions_created"], 0)
