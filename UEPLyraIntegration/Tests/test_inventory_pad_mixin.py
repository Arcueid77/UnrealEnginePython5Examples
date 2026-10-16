"""Isolated inventory policy checks; not native actor/overlap acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Object:
    def __init__(self, name, callback=None):
        self.name, self.callback, self.calls = name, callback, []

    def is_valid(self):
        return True

    def is_a(self, cls):
        return self.name == "pawn" and cls == "Pawn"

    def call_function(self, name, *args, **kwargs):
        self.calls.append((name, *args, kwargs) if kwargs else (name, *args))
        return self.callback(name, *args, **kwargs) if self.callback else None


class InventoryPadPolicy(unittest.TestCase):
    def setUp(self):
        self.slot, self.authority = 1, True
        self.item, self.mesh, self.fragment = Object("item"), Object("mesh"), Object("fragment")
        self.fragment.DisplayName, self.fragment.SkeletalMesh, self.fragment.PadColor = "Rifle", self.mesh, "color"
        self.quickbar = Object("quickbar", lambda name, *args: self.slot if name == "GetNextFreeItemSlot" else None)
        self.inventory = Object("inventory", lambda *args: self.item)
        self.controller = Object("controller")
        self.controller.get_component_by_type = lambda cls: self.quickbar if cls == "LyraQuickBarComponent" else self.inventory
        self.pawn = Object("pawn", lambda *args: self.controller)
        self.library_calls = []

        def native_call(cls, function, *args):
            self.library_calls.append((cls, function, *args))
            if function == "FindItemDefinitionFragment":
                return self.fragment
            if function == "Conv_LinearColorToVector":
                return "native-vector"
            if function == "Conv_StringToText":
                return args[0]

        native = types.ModuleType("unreal_engine")
        native.find_class = lambda name: name
        native.FVector, native.FRotator = lambda *values: values, lambda *values: values
        dependency = types.ModuleType("uep_lyra_world.effect_pad_mixin")
        dependency.valid = lambda value: value is not None and value.is_valid()
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world/inventory_pad_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_world._inventory_policy_test", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_lyra_world.effect_pad_mixin": dependency}):
            spec.loader.exec_module(self.module)
        self.module.library = lambda name: Object(name, lambda function, *args: native_call(name, function, *args))
        self.actor = Object("pad", lambda name, *args: self.authority if name == "HasAuthority" else None)
        self.actor.ItemDefinition, self.actor.PickUpSound, self.actor.bDestroyOnPickup = "rifle-definition", "sound", True
        self.actor.Text, self.actor.Pad, self.actor.SkeletalMesh = Object("text"), Object("pad-mesh"), Object("skeletal")
        self.actor.PickUpMesh = self.mesh
        self.actor.set_property = lambda name, value: setattr(self.actor, name, value)

    def test_construction_uses_fragment_native_text_mesh_and_color(self):
        self.assertIs(self.module.guarded(self.module.construct, self.actor), False)
        self.assertEqual(self.actor.Text.calls, [("K2_SetText", "Rifle")])
        self.assertEqual(self.actor.Pad.calls, [("SetVectorParameterValueOnMaterials", "Color", "native-vector")])
        self.assertIs(self.actor.PickUpMesh, self.mesh)

    def test_missing_fragment_retains_k2_zero_defaults(self):
        self.fragment = None
        self.module.construct(self.actor)
        self.assertEqual(self.actor.Text.calls, [("K2_SetText", "")])
        self.assertIsNone(self.actor.PickUpMesh)

    def test_authority_grants_one_item_selects_native_slot_and_destroys(self):
        self.module.overlap(self.actor, self.pawn)
        self.assertEqual(self.inventory.calls, [("AddItemDefinition", "rifle-definition", 1)])
        self.assertEqual(self.quickbar.calls, [("GetNextFreeItemSlot",), ("AddItemToSlot", 1, self.item), ("SetActiveSlotIndex", 1)])
        self.assertIn(("K2_DestroyActor",), self.actor.calls)

    def test_full_quickbar_does_not_grant_select_or_destroy(self):
        self.slot = -1
        self.module.overlap(self.actor, self.pawn)
        self.assertEqual(self.inventory.calls, [])
        self.assertEqual(self.actor.calls, [("HasAuthority",)])

    def test_non_pawn_and_uncontrolled_pawn_have_no_business(self):
        self.module.overlap(self.actor, Object("actor"))
        self.pawn.callback = lambda *args: None
        self.module.overlap(self.actor, self.pawn)
        self.assertEqual(self.actor.calls, [])

    def test_client_only_requests_original_local_audio_without_inventory_write(self):
        self.authority = False
        self.module.overlap(self.actor, self.pawn)
        self.assertEqual(self.inventory.calls, [])
        self.assertEqual(self.quickbar.calls, [])
        self.assertEqual(self.library_calls, [("GameplayStatics", "PlaySound2D", self.actor, "sound", 1.0, 1.0, 0.0, None, None, True)])

    def test_no_destroy_option_retains_actor(self):
        self.actor.bDestroyOnPickup = False
        self.module.overlap(self.actor, self.pawn)
        self.assertNotIn(("K2_DestroyActor",), self.actor.calls)

    def test_mesh_tick_uses_legacy_rotator_yaw_and_returns_no_original(self):
        result = self.module.LyraInventoryPadPythonProfile.MeshTick(self.actor, .2)
        self.assertIs(result, False)
        self.assertEqual(self.actor.SkeletalMesh.calls, [("K2_AddRelativeRotation", (0.0, 0.0, 5.0), False, {"bTeleport": False})])

    def test_policy_exception_is_not_converted_to_original_fallback(self):
        with self.assertRaisesRegex(RuntimeError, "native failed"):
            self.module.guarded(lambda actor: (_ for _ in ()).throw(RuntimeError("native failed")), self.actor)
        self.assertEqual(self.module.snapshot()["errors"], ["native failed"])
