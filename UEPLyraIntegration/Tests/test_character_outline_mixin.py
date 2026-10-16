"""Local outline orchestration models; no renderer or native interface proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterOutlineModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.material, self.local = [], None, True
        self.created = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("material", *args)))
        self.camera = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("camera", *args)))
        library = types.SimpleNamespace(call_function=self.create)
        engine = types.ModuleType("unreal_engine"); engine.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: library) if name == "KismetMaterialLibrary" else name
        engine.load_object = lambda cls, path: (cls, path)
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        loadout = types.ModuleType("uep_lyra_characters.initial_inventory_mixin")
        class Parent:
            def ClearInventory(self): pass
            def GetEmoteAudioComponent(self): pass
            def SetEmoteAudioComponent(self, AudioComponent): pass
            def ChangeQuickbarSlot(self, NewSlotIndex, SlotActionTag): pass
            def AddInitialInventory(self): pass
        loadout.LyraCharacterLoadoutPythonProfile = loadout.LyraCharacterLoadoutBlueprintFallbackProfile = Parent
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/outline_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._outline_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": engine, native.__name__: native, loadout.__name__: loadout}): spec.loader.exec_module(self.module)
        self.parent, self.python = Parent, self.module.LyraCharacterOutlinePythonProfile
        self.actor = types.SimpleNamespace(call_function=lambda name: self.local, get_property=self.get, set_property=self.set,
            call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def get(self, name): return self.camera if name == "CameraComponent" else self.material
    def set(self, name, value): self.assertEqual(name, "MPP_outlineMaterial"); self.material = value; self.calls.append(("field", name, value))
    def create(self, *args): self.calls.append(("create", *args)); return self.created
    def invoke(self, team=1, color=None): self.python.CreateOrUpdateOutlineIfNeeded(self.actor, team, color)

    def test_nonlocal_guard_precedes_asset_material_camera_and_parameter_mutation(self):
        self.local = False; self.invoke(); self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["nonlocal_noops"], 1)

    def test_create_uses_original_native_parent_context_name_and_flags(self):
        self.invoke(); self.assertEqual(self.calls[0], ("create", "CreateDynamicMaterialInstance", self.actor,
            ("MaterialInterface", self.module.PARENT), "None", 0))

    def test_new_material_is_stored_before_native_interface_camera_add(self):
        self.invoke(); self.assertEqual(self.calls[1], ("field", "MPP_outlineMaterial", self.created))
        self.assertEqual(self.calls[2], ("camera", "AddOrUpdateBlendable", self.created, 1.0))

    def test_scalar_then_vector_follow_original_sequence_order(self):
        color = object(); self.invoke(2, color)
        self.assertEqual(self.calls[-2:], [("material", "SetScalarParameterValue", "TeamID", 2.0), ("material", "SetVectorParameterValue", "TeamColor", color)])

    def test_existing_material_is_reused_without_readding_blendable(self):
        self.material = self.created; self.invoke()
        self.assertEqual(len(self.calls), 2); self.assertTrue(all(call[0] == "material" for call in self.calls))

    def test_detached_valid_material_is_not_automatically_attached(self):
        self.material = self.created; self.invoke(); self.assertFalse(any(call[0] == "camera" for call in self.calls))

    def test_repeated_updates_do_not_create_or_add_duplicate_materials(self):
        self.invoke(); self.invoke()
        self.assertEqual(sum(call[0] == "create" for call in self.calls), 1); self.assertEqual(sum(call[0] == "camera" for call in self.calls), 1)
        self.assertEqual(self.module.evidence(self.actor)["scalar_updates"], 2)

    def test_negative_team_id_uses_original_signed_double_conversion(self):
        self.invoke(-1); self.assertEqual(self.calls[-2], ("material", "SetScalarParameterValue", "TeamID", -1.0))

    def test_hdr_linear_color_is_forwarded_opaque_without_clamp_or_string_roundtrip(self):
        color = types.SimpleNamespace(r=-.25, g=2., b=.3, a=.5); self.invoke(3, color); self.assertIs(self.calls[-1][-1], color)

    def test_native_creation_failure_is_explicit_not_a_fake_parameter_pass(self):
        self.created = None
        with self.assertRaisesRegex(RuntimeError, "native outline material creation failed"): self.invoke()

    def test_fallback_calls_only_original_once(self):
        color = object(); self.module.LyraCharacterOutlineBlueprintFallbackProfile.CreateOrUpdateOutlineIfNeeded(self.actor, 2, color)
        self.assertEqual(self.calls, [("original", "CreateOrUpdateOutlineIfNeeded", 2, color)])

    def test_all_five_accepted_helpers_are_explicit_local_aliases(self):
        for profile in (self.python, self.module.LyraCharacterOutlineBlueprintFallbackProfile):
            for name in ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot", "AddInitialInventory"):
                self.assertIs(profile.__dict__[name], getattr(self.parent, name))

    def test_evidence_is_per_actor_pod_and_production_does_not_root_objects(self):
        value = self.module.evidence(self.actor); self.invoke()
        self.assertIs(value, self.module.evidence(self.actor)); self.assertEqual(value["materials_created"], 1)
        self.assertEqual(self.module.evidence(types.SimpleNamespace())["materials_created"], 0)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/outline_mixin.py"
        source = file.read_text(encoding="utf-8")
        for forbidden in ("add_to_root", "_actors =", "PostProcessSettings", "set_actor_role"):
            self.assertNotIn(forbidden, source)
