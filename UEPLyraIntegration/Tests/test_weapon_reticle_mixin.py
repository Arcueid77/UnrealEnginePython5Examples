import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class WeaponReticleContracts(unittest.TestCase):
    def setUp(self):
        native = types.ModuleType("unreal_engine")
        native.find_class = lambda name: name
        runtime = types.ModuleType("uep_runtime")
        runtime.SubscriptionScope = object
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/weapon_reticle_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._weapon_reticle_contract", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime,
                                     "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)

    def test_weapon_specific_geometry_and_boundaries(self):
        g = self.module.geometry
        self.assertEqual(g("Pistol", 0), (0, 40, 40))
        self.assertEqual(g("Pistol", 30), (30, 60, 60))
        self.assertEqual(g("Pistol", 100), (100, 80, 80))
        self.assertEqual(g("Rifle", 0), (0, 48, 48))
        self.assertEqual(g("Rifle", 36), (36, 72, 72))
        self.assertEqual(g("Rifle", 100), (100, 96, 96))
        self.assertEqual(g("Shotgun", 0), (0, 32, 56))
        self.assertEqual(g("Shotgun", 40), (40, 50, 80))
        self.assertEqual(g("Shotgun", 200), (96, 64, 160))
        for kind in ("Pistol", "Rifle", "Shotgun"):
            with self.subTest(kind=kind):
                value = g(kind, 24)
                self.assertTrue(value[1] >= 32 and value[2] >= 40)

    def test_unknown_configuration_fails_instead_of_guessing(self):
        with self.assertRaisesRegex(RuntimeError, "unknown"):
            self.module.geometry("Unknown", 10)

    def test_ads_keeps_authored_disconnected_animation_noop(self):
        widget = self.module.LyraWeaponReticlePythonProfile()
        widget.call_function = lambda *args: self.fail("ADS must not execute disconnected animation calls")
        widget.ADS(True)
        self.assertTrue(widget._uep_reticle_ads)

    def test_elimination_restarts_only_a_running_forward_animation(self):
        for running, expected in ((False, ["IsAnimationPlayingForward", "PlayAnimationForward"]),
                                  (True, ["IsAnimationPlayingForward", "StopAnimation", "SetAnimationCurrentTime", "PlayAnimationForward"])):
            widget = self.module.LyraWeaponReticlePythonProfile()
            widget.Elimination = object()
            calls = []
            widget.call_function = lambda name, *args: calls.append(name) or running
            widget.Eliminate()
            self.assertEqual(calls, expected)
            self.assertEqual(widget._uep_reticle_eliminations, 1)

    def test_ads_filters_foreign_controller(self):
        owner, other = object(), object()
        calls = []
        widget = types.SimpleNamespace(call_function=lambda name, *args: owner if name == "GetOwningPlayer" else calls.append((name, args)))
        payload = types.SimpleNamespace(**{self.module.CONTROLLER: other, self.module.ON: True})
        self.module.on_ads(widget, payload)
        self.assertEqual(calls, [])
        setattr(payload, self.module.CONTROLLER, owner)
        self.module.on_ads(widget, payload)
        self.assertEqual(calls, [("ADS", (True,))])

    def test_elimination_filters_cast_ownership_and_suicide(self):
        owner, other = object(), object()
        calls = []
        widget = types.SimpleNamespace(call_function=lambda name: owner if name == "GetOwningPlayer" else calls.append(name))
        actor = types.SimpleNamespace(is_a=lambda cls: cls == "LyraPlayerState", call_function=lambda name: owner)
        self.module.on_elimination(widget, types.SimpleNamespace(Instigator=actor, Target=other))
        self.assertEqual(calls, ["Eliminate"])
        self.module.on_elimination(widget, types.SimpleNamespace(Instigator=actor, Target=actor))
        self.module.on_elimination(widget, types.SimpleNamespace(Instigator=None, Target=other))
        actor.call_function = lambda name: other
        self.module.on_elimination(widget, types.SimpleNamespace(Instigator=actor, Target=other))
        self.assertEqual(calls, ["Eliminate"])


if __name__ == "__main__":
    unittest.main()
