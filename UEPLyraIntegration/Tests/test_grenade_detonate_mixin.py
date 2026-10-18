"""Explosion policy semantics; native RPC/trace/GAS proof is a separate lane."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native = types.ModuleType("unreal_engine")
structs, enums = types.ModuleType("unreal_engine.structs"), types.ModuleType("unreal_engine.enums")
for name in ("GameplayTag", "GameplayTagContainer", "GameplayEffectContextHandle"):
    setattr(structs, name, type(name, (), {}))
enums.EObjectTypeQuery = types.SimpleNamespace(ObjectTypeQuery3=2)
enums.ETraceTypeQuery = types.SimpleNamespace(TraceTypeQuery5=4)
enums.EDrawDebugTrace = types.SimpleNamespace(**{"None": 0})
helpers = types.ModuleType("uep_lyra_world.effect_pad_mixin")
helpers.valid = lambda value: value is not None
trace = types.ModuleType("uep_lyra_abilities.melee_trace_mixin")
trace.native_outputs = lambda cls, method, value: value
trace.break_hit = lambda value: value
base = types.ModuleType("uep_lyra_weapons.grenade_hit_mixin")
class Hit:
    def SetupVFX(self): pass
    def PostLaunchCleanup(self): pass
    def TeleportGrenade(self, a, b): pass
    def DestroyGrenade(self, component): pass
    def ReceiveBeginPlay(self): pass
    def ReceiveHit(self, *args): pass
base.LyraGrenadeHitPythonProfile = base.LyraGrenadeHitBlueprintFallbackProfile = Hit
spec = importlib.util.spec_from_file_location("uep_lyra_weapons._grenade_detonate_model",
    Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_detonate_mixin.py")
policy = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs,
    "unreal_engine.enums": enums, "uep_lyra_world.effect_pad_mixin": helpers,
    "uep_lyra_abilities.melee_trace_mixin": trace, "uep_lyra_weapons.grenade_hit_mixin": base}):
    spec.loader.exec_module(policy)


class TestGrenadeDetonateMixin(unittest.TestCase):
    def setUp(self):
        self.calls, self.authority, self.pawns, self.blocked, self.distance = [], True, [], True, 30.
        native.FVector = lambda: (0, 0, 0)
        native.FLinearColor = lambda *args: args
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda method, *args, **kw: self.call(name, method, args, kw)))
        native.load_class = lambda path: path
        self.mesh = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("mesh", args)))
        self.movement = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("movement", args)))
        self.source = types.SimpleNamespace(call_function=self.source_call)
        self.properties = {"Mesh": self.mesh, "ProjectileMovement": self.movement, "NS_Trail": object(),
                           "Radius": 100., "Gameplay Tag": "cue", "Instigator": "owner"}
        self.actor = types.SimpleNamespace(get_property=self.properties.get, set_property=self.properties.__setitem__,
            get_actor_location=lambda: (1, 2, 3), call_function=self.actor_call)

    def actor_call(self, method):
        self.calls.append(("actor", method))
        return self.authority if method == "HasAuthority" else None

    def source_call(self, method, *args):
        self.calls.append(("source", method, args))
        return "shared-context" if method == "MakeEffectContext" else None

    def call(self, cls, method, args, kw):
        self.calls.append((cls, method, args, kw))
        if method == "MakeGameplayCueParameters": return kw
        if method == "SphereOverlapActors": return {"ReturnValue": bool(self.pawns), "OutActors": self.pawns}
        if method == "GetAbilitySystemComponent": return self.source if args[0] == "owner" else ("asc", args[0])
        if method == "LineTraceSingle": return {"ReturnValue": self.blocked, "OutHit": {"Distance": self.distance, "HitActor": "wall"}}
        if method == "Divide_DoubleDouble": return args[0]/args[1]
        if method == "FClamp": return max(args[1], min(args[2], args[0]))

    def pawn(self, location):
        pawn = types.SimpleNamespace(get_actor_location=lambda: location)
        self.pawns.append(pawn)
        return pawn

    def test_remote_stops_after_visuals_without_overlap_or_cleanup(self):
        self.authority = False
        policy.detonate(self.actor)
        self.assertEqual([row[0] for row in self.calls], ["AbilitySystemBlueprintLibrary", "GameplayCueFunctionLibrary", "mesh", "movement", "actor"])

    def test_authority_empty_overlap_binds_native_finish(self):
        policy.detonate(self.actor)
        self.assertEqual(self.calls[-1], ("actor", policy.BIND))
        self.assertEqual(policy.evidence(self.actor)["effects"], 0)

    def test_invalid_trail_destroys_without_post_destroy_access(self):
        self.properties["NS_Trail"] = None
        original = self.actor.call_function
        def call(method):
            value = original(method)
            if method == "K2_DestroyActor": self.actor.get_property = lambda name: self.fail("access after Actor destruction")
            return value
        self.actor.call_function = call
        policy.detonate(self.actor)
        self.assertEqual(self.calls[-1], ("actor", "K2_DestroyActor"))

    def test_trace_target_is_overlap_pawn_even_when_hit_actor_is_wall(self):
        target = self.pawn((5, 6, 7))
        policy.detonate(self.actor)
        application, = [row for row in self.calls if row[:2] == ("source", "BP_ApplyGameplayEffectToTarget")]
        self.assertEqual(application[2], (policy.DAMAGE, ("asc", target), .3, "shared-context"))

    def test_each_trace_ignores_other_overlap_pawns_not_current(self):
        first, second = self.pawn((5, 6, 7)), self.pawn((8, 9, 10))
        policy.detonate(self.actor)
        traces = [row[3] for row in self.calls if row[1] == "LineTraceSingle"]
        self.assertEqual([row["ActorsToIgnore"] for row in traces], [[second], [first]])
        self.assertEqual(self.properties["IgnoreActors"], [first])
        self.assertTrue(all(row["TraceChannel"] == 4 and row["bTraceComplex"] for row in traces))

    def test_missed_trace_does_not_apply_effect(self):
        self.pawn((5, 6, 7)); self.blocked = False
        policy.detonate(self.actor)
        self.assertFalse(any(row[:2] == ("source", "BP_ApplyGameplayEffectToTarget") for row in self.calls))

    def test_original_increasing_level_and_clamp_preserved(self):
        self.pawn((5, 6, 7))
        for distance, expected in ((0., .1), (50., .5), (150., 1.)):
            self.calls.clear(); self.distance = distance
            policy.detonate(self.actor)
            application, = [row for row in self.calls if row[:2] == ("source", "BP_ApplyGameplayEffectToTarget")]
            self.assertEqual(application[2][2], expected)

    def test_context_created_once_hit_reset_before_each_application(self):
        self.pawn((1, 1, 1)); self.pawn((2, 2, 2))
        policy.detonate(self.actor)
        sequence = [row[1] for row in self.calls if row[0] in ("source", "AbilitySystemBlueprintLibrary")]
        self.assertEqual(sequence.count("MakeEffectContext"), 1)
        for index, name in enumerate(sequence):
            if name == "BP_ApplyGameplayEffectToTarget": self.assertEqual(sequence[index-3], "EffectContextAddHitResult")

    def test_profiles_never_override_reliable_rpc(self):
        self.assertNotIn("Detonate", vars(policy.LyraGrenadeDetonatePythonProfile))
        self.assertEqual(policy.LyraGrenadeDetonatePythonProfile.DetonateBody.override, policy.BODY)
        self.assertIs(policy.LyraGrenadeDetonatePythonProfile.ReceiveHit, Hit.ReceiveHit)

    def test_fallback_calls_only_retained_non_rpc_body(self):
        self.actor.call_mixin_original = lambda name: self.calls.append(("original", name))
        policy.LyraGrenadeDetonateBlueprintFallbackProfile.DetonateBody(self.actor)
        self.assertEqual(self.calls, [("original", policy.BODY)])
