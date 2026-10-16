"""Observe reflected ChildActor property, not the C++-only GetChildActor getter."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Object:
    def __init__(self, name, props=None, calls=None): self.name, self.props, self.calls = name, props or {}, calls or {}
    def get_path_name(self): return self.name
    def get_property(self, key): return self.props[key]
    def call_function(self, key): return self.calls[key]
    def get_class(self): return Object("native-part-class")


class CosmeticState(unittest.TestCase):
    def test_reflected_native_child_actor_and_attachment(self):
        native, helpers = types.ModuleType("unreal_engine"), types.ModuleType("uep_lyra_world.effect_pad_mixin")
        native.find_class = lambda name: name; helpers.valid = lambda value: value is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/cosmetic_state.py"
        spec = importlib.util.spec_from_file_location("cosmetic_state_model", file); module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_lyra_world.effect_pad_mixin": helpers}): spec.loader.exec_module(module)
        pawn = Object("pawn")
        actor = Object("native-body", calls={"GetActorEnableCollision": False, "GetAttachParentActor": pawn})
        child = Object("native-child", props={"ChildActor": actor})
        entry = types.SimpleNamespace(SpawnedComponent=child, PartHandle=17,
            Part=types.SimpleNamespace(PartClass=Object("native-part-class"), SocketName="None", CollisionMode=0))
        component = Object("native-customizer", props={"CharacterPartList": types.SimpleNamespace(Entries=[entry])})
        pawn.get_component_by_type = lambda cls: component
        value = module.capture(pawn)[0]
        self.assertEqual((value["handle"], value["actor"], value["actor_class"], value["attached_pawn"]), (17, "native-body", "native-part-class", "pawn"))
        self.assertFalse(value["actor_collision"])
