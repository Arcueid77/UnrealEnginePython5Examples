"""Policy isolation only; native physics/collision/RPC need separate proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object

def vector(*xyz):
    return types.SimpleNamespace(**dict(zip(("x", "y", "z"), xyz)))

class LauncherPolicy(unittest.TestCase):
    def setUp(self):
        native = types.ModuleType("unreal_engine")
        native.FVector = vector
        native.find_class = lambda name: name
        native.call_function_by_class = lambda actor, cls, name, args: {"Return": actor.call_function(name)}
        structs = types.ModuleType("unreal_engine.structs")
        structs.GameplayCueParameters = lambda **values: values
        dependency = types.ModuleType("uep_lyra_world.effect_pad_mixin")
        dependency.valid = lambda value: value is not None and value.is_valid()
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world/launcher_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_world._launcher_policy", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs,
                                     "uep_lyra_world.effect_pad_mixin": dependency}):
            spec.loader.exec_module(self.module)
        self.authority, self.ai = True, None
        self.libraries = []
        self.module.library = lambda cls: Object(cls, lambda name, *args, **kwargs: self.library(cls, name, *args, **kwargs))
        self.actor = Object("launcher", lambda name, *args: self.authority if name == "HasAuthority" else True)
        self.props = {"Light Color": "color", "Glow Intensity": 15.0, "Light Intensity": 60.0,
            "Light Attenuation": 250.0, "Do Not Activate on Fall Entry": False, "Use Target": False, "Gameplay Tag": "tag"}
        self.actor.get_property = self.props.get
        self.actor.get_class = lambda: "launcher-class"
        self.actor.set_property = lambda name, value: setattr(self.actor, name, value)
        self.actor.get_actor_location = lambda: "location"
        self.actor.SphereRadius, self.actor.UpOverride, self.actor.Multiplier = 100.0, .75, 750.0
        self.actor.Target, self.actor.XYBounds, self.actor.ZBounds = vector(150.0, 0.0, 0.0), 5500.0, 500.0
        self.actor.MinimumVerticalVelocityAllowed = -1200.0
        self.velocity = vector(0.0, 0.0, 0.0)
        self.pawn = Object("pawn", lambda name, *args: vector(.6, .8, 0.0) if name == "GetActorForwardVector" else None)
        self.pawn.is_a = lambda cls: cls == "Character"
        self.pawn.CharacterMovement = Object("movement", lambda *args: self.velocity)
        self.actor.OverlappingPawn = self.pawn
        self.mid = Object("mid")
        self.actor.LauncherMesh = Object("mesh", lambda name, *args: self.mid if name == "CreateDynamicMaterialInstance" else "material")
        self.actor.PointLight, self.actor.Sphere = Object("light"), Object("sphere")

    def library(self, cls, name, *args, **kwargs):
        self.libraries.append((cls, name, *args, kwargs) if kwargs else (cls, name, *args))
        if name == "MakeGameplayCueParameters":
            return kwargs
        return self.ai if name == "GetAIController" else None

    def launch(self, kind):
        self.assertTrue(self.module.overlap(self.actor, kind))
        call = self.pawn.calls[-1]
        self.assertEqual(call[0], "LaunchCharacter")
        return [getattr(call[1], key) for key in ("x", "y", "z")], call[2:]

    def test_construction_native_light_material_and_sphere(self):
        self.assertFalse(self.module.LyraLauncherPythonProfile.Construction(self.actor))
        self.assertEqual(self.mid.calls, [("SetScalarParameterValue", "Intensity", 15.0), ("SetVectorParameterValue", "Color", "color")])
        self.assertEqual(self.actor.Sphere.calls, [("SetSphereRadius", 100.0, True)])
        self.assertEqual(self.actor.PointLight.calls, [("SetLightColor", "color", True), ("SetIntensity", 60.0), ("SetAttenuationRadius", 250.0)])

    def test_push_construction_clamps_three_axes_without_parent_replay(self):
        self.actor.Target = vector(6000.0, -6000.0, -700.0)
        self.module.construct_push(self.actor)
        self.assertEqual([getattr(self.actor.Target, k) for k in ("x", "y", "z")], [5500.0, 0.0, -500.0])
        self.assertEqual(self.actor.calls, [])

    def test_push_forward_preserves_additive_native_flags(self):
        values, flags = self.launch("push")
        self.assertEqual(values, [450.0, 600.0, 562.5])
        self.assertEqual(flags, (False, False))

    def test_up_preserves_xy_additive_z_override(self):
        self.actor.UpOverride = 250.0
        values, flags = self.launch("up")
        self.assertEqual(values, [.6, .8, 250.0])
        self.assertEqual(flags, (False, True))

    def test_target_uses_xy_length_vertical_clamp_and_native_flags(self):
        self.props["Use Target"] = True
        self.actor.Target = vector(150.0, 200.0, 1000.0)
        values, flags = self.launch("push")
        self.assertEqual(values, [315.0, 420.0, 850.0])
        self.assertEqual(flags, (False, False))
        self.actor.Target = vector(20000.0, 0.0, -500.0)
        values, _ = self.launch("push")
        self.assertAlmostEqual(sum(v*v for v in values)**.5, 12000.0)

    def test_falling_filter_is_strict_and_missing_pawn_is_false(self):
        self.props["Do Not Activate on Fall Entry"] = True
        self.velocity = vector(0.0, 0.0, -1200.01)
        self.assertFalse(self.module.overlap(self.actor, "push"))
        self.velocity = vector(0.0, 0.0, -1200.0)
        self.assertTrue(self.module.overlap(self.actor, "push"))
        self.actor.OverlappingPawn = None
        self.assertFalse(self.module.overlap(self.actor, "up"))
        self.assertTrue(self.module.overlap(self.actor, "parent"))

    def test_client_assigns_pawn_but_does_not_launch_or_rpc(self):
        self.authority = False
        self.module.begin(self.actor, self.pawn)
        self.assertIs(self.actor.OverlappingPawn, self.pawn)
        self.assertEqual(self.actor.calls, [("HasAuthority",)])

    def test_authority_excludes_ai_and_calls_retained_rpc_after_overlap(self):
        self.ai = Object("ai")
        self.module.begin(self.actor, self.pawn)
        self.assertNotIn(("Overlap",), self.actor.calls)
        self.ai = None
        self.module.begin(self.actor, self.pawn)
        self.assertEqual(self.actor.calls[-2:], [("Overlap",), ("Activate VFX",)])

    def test_cue_keeps_native_default_levels_and_causer(self):
        self.module.cue(self.actor)
        parameters = self.libraries[-1][-1]
        self.assertEqual(parameters, {"Location": "location", "EffectCauser": self.actor, "GameplayEffectLevel": 1, "AbilityLevel": 1})

    def test_typed_out_parameter_false_does_not_emit_rpc(self):
        self.actor.callback = lambda name, *args: name == "HasAuthority"
        self.module.begin(self.actor, self.pawn)
        self.assertNotIn(("Activate VFX",), self.actor.calls)
        self.actor.callback = lambda name, *args: True
        self.module.begin(self.actor, self.pawn)
        self.assertEqual(self.actor.calls[-1], ("Activate VFX",))

    def test_exception_never_returns_fallback_minus_one(self):
        self.actor.OverlappingPawn = self.pawn
        self.pawn.call_function = lambda *args: (_ for _ in ()).throw(RuntimeError("native failure"))
        with self.assertRaisesRegex(RuntimeError, "native failure"):
            self.module.LyraLauncherPythonProfile.PushOverlap(self.actor)
        self.assertEqual(self.module.snapshot()["errors"], ["native failure"])
