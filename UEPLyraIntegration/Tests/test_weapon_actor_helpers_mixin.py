"""Weapon helper decisions; native engine checks are a separate requirement."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native = types.ModuleType("unreal_engine")
enums = types.ModuleType("unreal_engine.enums")
enums.ETraceTypeQuery = types.SimpleNamespace(TraceTypeQuery1=0)
enums.EDrawDebugTrace = types.SimpleNamespace(**{"None": 0})
enums.EAttachLocation = types.SimpleNamespace(KeepRelativeOffset=0)
enums.ERelativeTransformSpace = types.SimpleNamespace(RTS_World=0)
helpers = types.ModuleType("uep_lyra_world.effect_pad_mixin"); helpers.valid = lambda value: value is not None
trace = types.ModuleType("uep_lyra_abilities.melee_trace_mixin")
trace.trace_outputs = lambda method, value: value
trace.break_hit = lambda value: value
trace.native_outputs = lambda cls, method, value: value
spec = importlib.util.spec_from_file_location("_weapon_actor_helpers_model", Path(__file__).resolve().parents[1]/
    "Overlay/Content/Scripts/uep_lyra_weapons/weapon_actor_helpers_mixin.py")
policy = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.enums": enums,
    "uep_lyra_world.effect_pad_mixin": helpers, "uep_lyra_abilities.melee_trace_mixin": trace}): spec.loader.exec_module(policy)


class TestWeaponActorHelpersMixin(unittest.TestCase):
    def setUp(self):
        self.calls, self.writes, self.hit, self.local = [], [], True, False
        self.start, self.destination = (0., 0., 0.), (100., 0., 0.)
        self.mesh = types.SimpleNamespace(call_function=lambda *args: "transform")
        self.audio = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("trigger", args)))
        self.owner = types.SimpleNamespace(call_function=lambda *args: self.local)
        self.components = [types.SimpleNamespace(call_function=lambda *args: self.calls.append(("stencil", args))) for _ in range(2)]
        self.data = {"SkeletalMesh": self.mesh, "Impact Positions": [self.destination], "Impact Normals": [],
                     "ImpactSurfaceTypes": [], "AudioComponent": None, "OwnerAsPawn": self.owner, "ApplyTeamColorsToWeapon": True}
        self.actor = types.SimpleNamespace(get_property=self.data.get, set_property=self.write)
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=lambda method,*args,**kw:self.backend(name,method,args,kw)))
        native.FVector = lambda: (0., 0., 0.)
        native.FRotator = lambda: (0., 0., 0.)
        native.FTransform = lambda: "identity"
        native.FLinearColor = lambda *args: args
    def write(self, name, value): self.writes.append(name); self.data[name] = value
    def backend(self, cls, method, args, kw):
        self.calls.append((method, args, kw))
        if method == "BreakTransform": return dict(Location=self.start)
        if method == "Subtract_VectorVector": return tuple(a-b for a,b in zip(*args))
        if method == "Normal": return args[0]
        if method == "RandomUnitVectorInConeInDegrees": return (1., 0., 0.)
        if method == "Multiply_VectorFloat": return tuple(value*args[1] for value in args[0])
        if method == "Add_VectorVector": return tuple(a+b for a,b in zip(*args))
        if method == "LineTraceSingle": return self.hit, dict(Location=(50.,0.,0.), Normal=(-1.,0.,0.))
        if method == "GetSurfaceType": return 3
        if method == "FindComponentsByClass": return self.components
        if method == "SpawnSoundAttached": return self.spawned_audio
        self.fail(method)
    def test_zero_and_negative_counts_leave_arrays_and_mesh_unread(self):
        self.actor.get_property = lambda name: self.fail("zero-loop property read")
        policy.fake_projectiles(self.actor, 0, 5.)
        policy.fake_projectiles(self.actor, -8, 5.)
        self.assertEqual(self.writes, [])
    def test_native_hit_appends_three_independent_arrays_in_original_order(self):
        policy.fake_projectiles(self.actor, 2, 5.)
        self.assertEqual(self.writes, ["ImpactSurfaceTypes", "Impact Positions", "Impact Normals"]*2)
        self.assertEqual(self.data["Impact Positions"], [self.destination, (50.,0.,0.), (50.,0.,0.)])
        self.assertEqual(self.data["ImpactSurfaceTypes"], [3,3])
    def test_missed_trace_preserves_arrays(self):
        self.hit = False; policy.fake_projectiles(self.actor, 2, 5.)
        self.assertEqual(self.writes, []); self.assertEqual(policy.evidence(self.actor)["hits"], 0)
    def test_native_spread_and_original_million_unit_trace(self):
        policy.fake_projectiles(self.actor, 1, 7.)
        rng, = [row for row in self.calls if row[0] == "RandomUnitVectorInConeInDegrees"]
        ray, = [row for row in self.calls if row[0] == "LineTraceSingle"]
        self.assertEqual(rng[1][1], 7.)
        self.assertEqual((ray[2]["End"],ray[2]["TraceChannel"],ray[2]["bTraceComplex"],ray[2]["bIgnoreSelf"]),((1000000.,0.,0.),0,False,True))
    def test_empty_array_first_hit_changes_direction_for_next_iteration(self):
        self.data["Impact Positions"] = []; policy.fake_projectiles(self.actor, 2, 0.)
        subtracts = [row[1][0] for row in self.calls if row[0] == "Subtract_VectorVector"]
        self.assertEqual(subtracts, [(0.,0.,0.),(50.,0.,0.)])
    def test_local_bot_gets_zero_without_player_control_requirement(self):
        self.local = True; policy.stencil(self.actor, 42)
        self.assertEqual([row[1] for row in self.calls if row[0] == "stencil"], [("SetCustomDepthStencilValue",0)]*2)
    def test_remote_owner_preserves_input_for_native_clamping(self):
        policy.stencil(self.actor, -4)
        self.assertEqual([row[1][1] for row in self.calls if row[0] == "stencil"], [-4,-4])
        query, = [row for row in self.calls if row[0] == "FindComponentsByClass"]
        self.assertIs(query[1][0], self.actor); self.assertIs(query[1][2], True)
    def test_absent_owner_uses_remote_branch(self):
        self.data["OwnerAsPawn"] = None; policy.stencil(self.actor, 7)
        self.assertEqual([row[1][1] for row in self.calls if row[0] == "stencil"], [7,7])
    def test_existing_audio_reused_despite_new_sound_and_null_target(self):
        self.data["AudioComponent"] = self.audio; policy.trigger_audio(self.actor, "new-sound", None)
        self.assertEqual(self.calls, [("trigger",("SetTriggerParameter","Fire"))]); self.assertEqual(self.writes, [])
    def test_failed_native_spawn_stores_null_and_does_not_trigger(self):
        self.spawned_audio = None; policy.trigger_audio(self.actor, None, None)
        self.assertEqual(self.writes, ["AudioComponent"]); self.assertEqual(policy.evidence(self.actor)["audio_triggers"], 0)
    def test_native_audio_original_options(self):
        self.spawned_audio = self.audio; policy.trigger_audio(self.actor, "sound", None)
        row = self.calls[0][2]
        self.assertEqual((row["AttachPointName"],row["VolumeMultiplier"],row["PitchMultiplier"],row["StartTime"],row["bAutoDestroy"],row["bStopWhenAttachedToDestroyed"]),("hand_r",1.,1.,0.,True,False))
        self.assertEqual(self.calls[-1], ("trigger",("SetTriggerParameter","Fire")))
    def test_invalid_team_asset_short_circuits_actor_flag(self):
        self.actor.get_property = lambda name: self.fail("invalid asset read opt-in")
        policy.LyraWeaponActorHelpersPythonProfile.UpdateTeamColors(self.actor, None)
        self.assertEqual(policy.evidence(self.actor)["team_applications"], 0)
    def test_team_opt_out_and_native_recursive_application(self):
        asset = types.SimpleNamespace(call_function=lambda *args:self.calls.append(args))
        self.data["ApplyTeamColorsToWeapon"] = False
        policy.LyraWeaponActorHelpersPythonProfile.UpdateTeamColors(self.actor, asset); self.assertEqual(self.calls, [])
        self.data["ApplyTeamColorsToWeapon"] = True
        policy.LyraWeaponActorHelpersPythonProfile.UpdateTeamColors(self.actor, asset)
        self.assertEqual(self.calls, [("ApplyToActor",self.actor,True)])
    def test_fallback_retains_original_spelled_signature(self):
        self.actor.call_mixin_original = lambda *args:self.calls.append(args)
        policy.LyraWeaponActorHelpersBlueprintFallbackProfile.AddFakeProjectileData(self.actor, 4, 3.)
        self.assertEqual(self.calls, [(policy.FAKE,4,3.)])
