"""Keep the cold observer free of explicit audio/Cue loading and registration."""
import ast
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_audio_cold_validation.py"


class TestWeaponAudioColdProbe(unittest.TestCase):
    def test_no_direct_class_load_registration_profile_override_or_cue_replay(self):
        tree=ast.parse(SOURCE.read_text(encoding="utf-8"));forbidden={"register_declared_mixin","register_mixin_profile","set_mixin_profile","ExecuteGameplayCueOnActor"}
        calls=[node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)]
        self.assertFalse(forbidden.intersection(calls))
        loads=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=="load_class"]
        self.assertEqual({ast.unparse(node.args[0]) for node in loads},{"'/Game/Weapons/B_Weapon.B_Weapon_C'","firing.policy.CLASS"})
    def test_does_not_import_audio_production_modules_to_warm_them(self):
        tree=ast.parse(SOURCE.read_text(encoding="utf-8"))
        imports=[node.module or "" for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
        self.assertFalse(any("weapon_audio_" in name and name.endswith("_mixin") for name in imports))
    def test_skips_cross_weapon_montage_fixture_before_first_input(self):
        tree=ast.parse(SOURCE.read_text(encoding="utf-8"));method,=[node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name=="montage_trials"]
        self.assertTrue(all(isinstance(node,ast.Pass) for node in method.body))
