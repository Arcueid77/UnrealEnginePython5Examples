"""Keep the agreed animation/editor/test exclusions out of runtime batches."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
from blueprint_model import retained_reason


def asset(path, **values):
    return {"path": path, "asset_class": "Blueprint", "parent_class": "UserWidget", **values}


class BlueprintScopeTests(unittest.TestCase):
    def test_named_test_gameplay_cues_stay_out(self):
        for name in ("GCN_Test_Burst", "GCN_Test_BurstLatent", "GCNL_Test_Looping"):
            with self.subTest(name=name):
                self.assertEqual(retained_reason(asset("/Game/GameplayCueNotifies/" + name + "." + name)),
                                 "test tooling retained")

    def test_performance_bot_spawner_stays_out(self):
        self.assertEqual(retained_reason(asset("/ShooterCore/Bot/B_ShooterBotSpawner_Perf.B_ShooterBotSpawner_Perf")),
                         "test tooling retained")

    def test_animation_and_editor_tools_stay_out(self):
        self.assertEqual(retained_reason(asset("/Game/AnimationNotifies/AN_Footstep.AN_Footstep")),
                         "animation system retained")
        self.assertEqual(retained_reason(asset("/LyraExtTool/SomeUtility.SomeUtility")),
                         "editor tooling retained")

    def test_real_runtime_cues_and_widgets_are_not_excluded(self):
        for path in ("/ShooterCore/Weapons/GCN_WeaponFire.GCN_WeaponFire",
                     "/ShooterCore/UserInterface/HUD/W_WeaponAmmoAndName.W_WeaponAmmoAndName"):
            self.assertIsNone(retained_reason(asset(path)))
