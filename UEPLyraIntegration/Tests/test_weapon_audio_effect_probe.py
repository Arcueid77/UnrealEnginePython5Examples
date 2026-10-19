"""Observe the authored native preset without initialization or replacement APIs."""
import ast
from pathlib import Path
import unittest


class TestWeaponAudioEffectProbe(unittest.TestCase):
    def test_no_preset_bootstrap_asset_load_or_probe_audio_creation(self):
        file=Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_audio_effect_validation.py"
        tree=ast.parse(file.read_text(encoding="utf-8"));calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)]
        names={node.func.attr for node in calls};self.assertFalse({"load_object","load_class","new_object","create_asset","add_actor_component","set_property","save_package"}.intersection(names))
        functions={node.args[0].value for node in calls if node.func.attr=="call_function" and node.args and isinstance(node.args[0],ast.Constant)}
        self.assertFalse({"AddTap","RemoveTap","SetTap","SetSettings","Init","SpawnSoundAtLocation","CreateSound2D"}.intersection(functions))
