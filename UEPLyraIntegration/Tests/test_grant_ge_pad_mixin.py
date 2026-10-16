"""Isolated policy assertions only, not real GAS/Timeline execution."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object

class GrantGEPolicy(unittest.TestCase):
    def setUp(self):
        native = types.ModuleType("unreal_engine")
        native.FVector = native.FRotator = lambda *values: values
        native.load_object = lambda *args: "timer-material"
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: Object(name,
            lambda method, *args: "native-color" if method == "Conv_LinearColorToVector" else args[0]/args[1]))
        dependency = types.ModuleType("uep_lyra_world.effect_pad_mixin")
        dependency.valid = lambda value: value is not None and value.is_valid()
        dependency.ability_system = lambda value: getattr(value, "asc", None)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world/grant_ge_pad_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_world._grant_ge_policy", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_lyra_world.effect_pad_mixin": dependency}):
            spec.loader.exec_module(self.module)
        self.actor = Object("pad")
        for name in ("Pad", "Text", "ItemMesh", "PointLight", "TL_Charge", "Scene", "MID_TimerIndicator"):
            setattr(self.actor, name, Object(name))
        self.actor.TimerIndicator = Object("timer", lambda *args: self.actor.MID_TimerIndicator)
        self.actor.Mesh, self.actor.PadColor, self.actor.GameplayEffectToApply = "mesh", "color", "effect"
        self.actor.Duration, self.actor.bActive = 2.0, True
        self.actor.set_property = lambda name, value: setattr(self.actor, name, value)
        self.actor.callback = lambda name, *args: self.module.active(self.actor) if name == "Active" else None
        self.other = Object("pawn")
        self.other.asc = Object("asc")

    def test_construction_uses_ftext_transport_and_native_components(self):
        self.assertFalse(self.module.LyraGrantGEPythonProfile.Construction(self.actor))
        self.assertIn((self.module.TEXT,), self.actor.calls)
        self.assertEqual(self.actor.ItemMesh.calls, [("SetStaticMesh", "mesh")])
        self.assertEqual(self.actor.PointLight.calls, [("SetLightColor", "color", True)])

    def test_begin_preserves_zero_effect_level_and_does_not_start_cooldown(self):
        self.module.begin(self.actor, self.other)
        self.assertEqual(self.other.asc.calls, [("BP_ApplyGameplayEffectToSelf", "effect", 0.0)])
        self.assertTrue(self.actor.bActive)
        self.assertEqual(self.actor.TL_Charge.calls, [])

    def test_inactive_begin_and_missing_asc_do_not_apply(self):
        self.actor.bActive = False
        self.module.begin(self.actor, self.other)
        self.module.end(self.actor, Object("no-asc"))
        self.assertEqual(self.other.asc.calls, [])
        self.assertEqual(self.actor.TL_Charge.calls, [])

    def test_end_removes_by_source_then_native_timeline_starts(self):
        self.module.end(self.actor, self.other)
        self.assertEqual(self.other.asc.calls, [("RemoveActiveGameplayEffectBySourceEffect", "effect", None, -1)])
        self.assertFalse(self.actor.bActive)
        self.assertEqual(self.actor.Text.calls, [("K2_SetText", "Charging")])
        self.assertEqual(self.actor.TL_Charge.calls, [("SetPlayRate", .5), ("PlayFromStart",)])

    def test_tick_skips_native_out_struct_with_named_later_input(self):
        self.assertFalse(self.module.LyraGrantGEPythonProfile.Tick(self.actor, .2))
        self.assertEqual(self.actor.Scene.calls, [("K2_AddLocalRotation", (0.0, 0.0, 10.0), False, {"bTeleport": False})])

    def test_update_and_finish_restore_authored_state(self):
        self.module.LyraGrantGEPythonProfile.Update(self.actor, .3)
        self.module.finish(self.actor)
        self.assertEqual(self.actor.MID_TimerIndicator.calls, [("SetScalarParameterValue", "Percent", .3), ("SetScalarParameterValue", "Percent", 0.0)])
        self.assertTrue(self.actor.bActive)
        self.assertIn((self.module.TEXT,), self.actor.calls)
        self.assertIn(("SetActorTickEnabled", True), self.actor.calls)

    def test_exception_does_not_return_original_branch_true(self):
        with self.assertRaisesRegex(RuntimeError, "native failed"):
            self.module.guarded(lambda actor: (_ for _ in ()).throw(RuntimeError("native failed")), self.actor)
        self.assertEqual(self.module.snapshot()["errors"], ["native failed"])
