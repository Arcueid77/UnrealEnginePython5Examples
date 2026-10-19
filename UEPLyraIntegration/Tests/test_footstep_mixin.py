"""Guard source quirks and failure branches independently of the native renderer."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native = types.ModuleType("unreal_engine"); enums = types.ModuleType("unreal_engine.enums")
enums.EAttachLocation = types.SimpleNamespace(KeepRelativeOffset=0)
enums.ENCPoolMethod = types.SimpleNamespace(**{"None":0})
enums.ERelativeTransformSpace = types.SimpleNamespace(RTS_World=0)
helpers = types.ModuleType("uep_lyra_world.effect_pad_mixin"); helpers.valid = lambda obj:obj is not None
trace = types.ModuleType("uep_lyra_abilities.melee_trace_mixin"); trace.break_hit = lambda value:value
spec = importlib.util.spec_from_file_location("_footstep_model", Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/footstep_mixin.py")
policy = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"unreal_engine":native, "unreal_engine.enums":enums, "uep_lyra_world.effect_pad_mixin":helpers, "uep_lyra_abilities.melee_trace_mixin":trace}): spec.loader.exec_module(policy)


class Component:
    def __init__(self, active=True): self.active = active; self.calls = []
    def call_function(self, method, *args):
        self.calls.append((method, args))
        if method == "IsActive": return self.active
        if method == "GetSocketTransform": return "stored-mesh-transform"


class TestFootstepMixin(unittest.TestCase):
    def setUp(self):
        self.calls = []; self.mesh = Component(); self.component = Component(); self.spawned = Component()
        self.data = {"Enable FootPlantEffect":True, "Skeletal Mesh Component":self.mesh, "NS_FootPrint":self.component,
            "Foot Print System":"system", "DefaultSceneRoot":"root", "FootStepRightFootBone":"foot_r", "FootPrintTrigger":False}
        self.actor = types.SimpleNamespace(get_property=self.data.get, set_property=self.write,
            call_function=lambda *args:self.calls.append(("actor", args)), call_mixin_original=lambda *args:self.calls.append(("original", args)))
        native.FVector = lambda *args:args or (0., 0., 0.); native.FRotator = lambda: (0., 0., 0.)
        native.find_class = lambda cls:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda method,*a,**kw:self.backend(cls,method,a,kw)))
        self.hit = dict(Location=(1.,2.,3.), ImpactPoint=(101.,102.,103.), Normal=(0.,0.,7.), ImpactNormal=(0.,-1.,0.))
        self.surface = 0; self.args = ("FOOT_R", "tag", "ignored-component", "offset", "rotation", "animation", True, self.hit, "contexts", "scale", .5, 2.)
    def write(self, key, value): self.data[key] = value; self.calls.append(("write", key, value))
    def backend(self, cls, method, args, kwargs):
        self.calls.append((method, args, kwargs))
        if method == "GetSurfaceType": return self.surface
        if method == "Conv_ByteToInt": return int(args[0])
        if method == "EqualEqual_NameName": return args[0].lower() == args[1].lower()
        if method in ("Conv_NameToString", "Conv_StringToName"): return args[0]
        if method == "Concat_StrStr": return "".join(args)
        if method == "SpawnSystemAttached": return self.spawned
        if method == "Conv_RotatorToQuaternion": return (0.,0.,0.,1.)
        return (method, args)
    def run_motion(self): policy.motion(self.actor, *self.args)
    def test_disabled_event_still_retriggers_without_state_write(self):
        self.data["Enable FootPlantEffect"] = False; self.run_motion(); self.assertEqual(self.calls, [("actor", (policy.DELAY,))])
    def test_miss_preserves_state_and_requests_delay(self):
        args = list(self.args); args[6] = False; policy.motion(self.actor, *args); self.assertEqual(self.calls, [("actor", (policy.DELAY,))])
    def test_unsupported_surface_only_stores_hit_and_surface(self):
        self.surface = 4; self.run_motion(); self.assertEqual([v[1] for v in self.calls if v[0] == "write"], ["Hit Result", "FootStepSurfaceType"])
        self.assertEqual(self.calls[-1], ("actor", (policy.DELAY,)))
    def test_all_four_original_surface_branches_continue(self):
        for surface in range(4):
            with self.subTest(surface=surface): self.surface = surface; self.run_motion(); self.assertEqual(self.data["FootStepSurfaceTypeNiagara"], surface)
    def test_location_and_normal_do_not_use_impact_fields(self):
        self.run_motion(); self.assertEqual(self.data["FootStepHitLocation"], self.hit["Location"]); self.assertEqual(self.data["FootStepHitNormal"], self.hit["Normal"])
    def test_socket_uses_stored_mesh_and_bone_suffix(self):
        self.run_motion(); self.assertIn(("GetSocketTransform", ("FOOT_R_Socket", 0)), self.mesh.calls)
    def test_native_name_comparison_preserves_case_insensitivity(self): self.run_motion(); self.assertIs(self.data["FootStepSide"], True)
    def test_normalization_uses_native_tolerance_and_math(self):
        self.run_motion(); calls = [v for v in self.calls if v[0] == "Normal"]; self.assertEqual(calls[0][1][1], .0001)
        self.assertTrue(any(v[0] == "MakeRotationFromAxes" for v in self.calls))
    def test_active_cache_toggles_without_spawn(self):
        self.run_motion(); self.run_motion(); self.assertIs(self.data["FootPrintTrigger"], False); self.assertIs(self.data["NS_FootPrint"], self.component)
        self.assertFalse(any(v[0] == "SpawnSystemAttached" for v in self.calls))
    def test_inactive_cache_replaced_and_trigger_reset(self):
        self.component.active = False; self.data["FootPrintTrigger"] = True; self.run_motion()
        self.assertIs(self.data["NS_FootPrint"], self.spawned); self.assertEqual([v[2] for v in self.calls if v[:2] == ("write", "FootPrintTrigger")], [False, True])
    def test_spawn_keeps_native_zero_transform_and_options(self):
        self.data["NS_FootPrint"] = None; self.run_motion(); kw = next(v[2] for v in self.calls if v[0] == "SpawnSystemAttached")
        self.assertEqual((kw["Location"], kw["Rotation"], kw["AttachToComponent"], kw["bAutoDestroy"], kw["bAutoActivate"], kw["bPreCullCheck"]), ((0.,0.,0.), (0.,0.,0.), "root", True, True, True))
    def test_niagara_writes_use_original_order(self):
        self.run_motion(); self.assertEqual([v[1][0] for v in self.component.calls if v[0].startswith("SetVariable")], ["User.Trigger", "User.StepLocation", "User.Orientation", "User.SurfaceType", "User.StepSide"])
    def test_absent_stored_mesh_preserves_original_diagnostics(self):
        self.data["Skeletal Mesh Component"] = None; self.run_motion(); self.assertEqual(self.calls, [("original", ("AnimMotionEffect", *self.args))])
    def test_absent_system_preserves_original_diagnostics(self):
        self.data["Foot Print System"] = None; self.run_motion(); self.assertEqual(self.calls, [("original", ("AnimMotionEffect", *self.args))])
    def test_cleanup_retains_valid_inactive_cache(self):
        self.component.active = False; policy.cleanup(self.actor); self.assertEqual(self.calls, [("actor", (policy.DELAY,))]); self.assertEqual(self.component.calls, [])
    def test_cleanup_without_cache_destroys(self):
        self.data["NS_FootPrint"] = None; policy.cleanup(self.actor); self.assertEqual(self.calls, [("actor", ("K2_DestroyActor",))])
    def test_fallback_forwards_exact_interface_arguments(self):
        policy.LyraFootstepBlueprintFallbackProfile.AnimMotionEffect(self.actor, *self.args); self.assertEqual(self.calls, [("original", ("AnimMotionEffect", *self.args))])
    def test_fallback_cleanup_returns_original_continuation(self):
        policy.LyraFootstepBlueprintFallbackProfile.AfterDelay(self.actor); self.assertEqual(self.calls, [("original", (policy.AFTER,))])
