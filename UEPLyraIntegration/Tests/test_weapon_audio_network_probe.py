"""Resident audio snapshots must not warm or register an absent class."""
import ast
from pathlib import Path
import unittest


class TestWeaponAudioNetworkProbe(unittest.TestCase):
    def test_audio_observer_only_reads_existing_registry(self):
        file=Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_fire_cue_network_validation.py"
        tree=ast.parse(file.read_text(encoding="utf-8"));method,=[node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name=="read_audio"]
        calls={node.func.attr for node in ast.walk(method) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)}
        self.assertTrue({"get_registered_mixins","get_cdo","get_mixin_profile"}.issubset(calls))
        self.assertFalse({"load_class","register_declared_mixin","register_mixin_profile","set_mixin_profile"}.intersection(calls))
