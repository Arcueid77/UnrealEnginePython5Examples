"""Native primitive stand-ins; hostile/friendly/occlusion/damage await real UE."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch

structs = types.ModuleType("unreal_engine.structs")
for name in ("GameplayTag", "GameplayTagContainer", "GameplayEffectContextHandle", "HitResult"):
    setattr(structs, name, lambda **values: types.SimpleNamespace(**values))
enums = types.ModuleType("unreal_engine.enums")
for name, values in {"EObjectTypeQuery": dict(ObjectTypeQuery3=2), "ETraceTypeQuery": dict(TraceTypeQuery4=3),
        "EDrawDebugTrace": {"None": 0}, "ERootMotionFinishVelocityMode": dict(MaintainLastRootMotionVelocity=0),
        "ELyraTeamComparison": dict(DifferentTeams=1)}.items(): setattr(enums, name, types.SimpleNamespace(**values))
effects = types.ModuleType("uep_lyra_world.effect_pad_mixin"); effects.valid = lambda value: value is not None
with patch.dict(sys.modules, {"unreal_engine": types.ModuleType("unreal_engine"), "unreal_engine.structs": structs,
        "unreal_engine.enums": enums, "uep_lyra_world.effect_pad_mixin": effects}):
    policy = importlib.import_module("uep_lyra_abilities.melee_trace_mixin")


class V:
    def __init__(self, x=0., y=0., z=0.): self.x, self.y, self.z = x, y, z
    def data(self): return [self.x, self.y, self.z]


class Ability:
    def __init__(self, owner): self.owner, self.fields = owner, dict(Distance=350., Radius=96., **{"Half Height":48.}, Strength=2200., Duration=.05)
    def get_property(self, name): return self.fields[name]
    def set_property(self, name, value): self.owner.order.append(("store-"+name, value)); self.fields[name] = value
    def call_function(self, name, *args):
        self.owner.order.append((name, args))
        if name == "GetLyraCharacterFromActorInfo": return self.owner.actor
        if name == "GetLyraAbilitySystemComponentFromActorInfo": return self.owner.source


class MeleeTracePolicyModels(unittest.TestCase):
    @staticmethod
    def description(cls, name):
        arrays = ["ObjectTypes", "ActorsToIgnore"] if name == "CapsuleTraceSingleForObjects" else ["ActorsToIgnore"]
        return dict(parameters=[dict(name=value, flags=4503599761589122, type="TArray") for value in arrays]+
            [dict(name="OutHit", flags=0x100, type="FHitResult"), dict(name="ReturnValue", flags=0x400, type="bool")])
    def setUp(self):
        self.order = []; self.calls = {}; self.hit = True; self.asc_valid = True; self.team = 1; self.blocked = False; self.hit_distance = 175.
        self.target = types.SimpleNamespace(get_path_name=lambda: "native-target")
        self.actor = types.SimpleNamespace(get_property=lambda name: types.SimpleNamespace(call_function=lambda method, socket: V(1., 2., 3.)), call_function=lambda name: V(1., 0., 0.))
        self.source = types.SimpleNamespace(call_function=lambda name, *args: self.native("SourceASC", name, args, {}))
        self.ability = Ability(self); self.hit_struct = object()
        self.patches = [patch.object(policy, "ue", types.SimpleNamespace(FLinearColor=lambda *args: args, find_class=lambda name: name, load_class=lambda name: name, describe_function=self.description)),
            patch.object(policy, "library", lambda cls: types.SimpleNamespace(call_function=lambda name, *args, **kwargs: self.native(cls, name, args, kwargs))),
            patch.object(policy, "break_hit", lambda hit: dict(HitActor=self.target, ImpactPoint=V(20., 2., 3.), Distance=self.hit_distance))]
        for item in self.patches: item.start(); self.addCleanup(item.stop)
        for key in policy._stats: policy._stats[key] = 0
    def native(self, cls, name, args, kwargs):
        self.order.append((name, args or kwargs)); self.calls[name] = (args, kwargs)
        if name == "MakeVector": return V(*args)
        if name in ("Multiply_VectorVector", "Add_VectorVector"):
            return V(*(a*b if name.startswith("Multiply") else a+b for a,b in zip(args[0].data(), args[1].data())))
        if name == "CapsuleTraceSingleForObjects": return self.hit, kwargs["ObjectTypes"], kwargs["ActorsToIgnore"], self.hit_struct
        if name == "LineTraceSingle": return self.blocked, kwargs["ActorsToIgnore"], object()
        if name == "GetAbilitySystemComponent": return "target-asc" if self.asc_valid else None
        if name == "IsValid": return args[0] is not None
        if name == "GetWorldSubsystem": return types.SimpleNamespace(call_function=lambda method, *args: self.native("teams", method, args, {}))
        if name == "CompareTeams": return self.team, 1, 2
        if name == "NormalizeToRange": return args[0]/args[2]
        if name == "Multiply_DoubleDouble": return args[0]*args[1]
        if name == "ApplyRootMotionConstantForce": return types.SimpleNamespace(call_function=lambda method: self.order.append(("root-"+method, ())))
        if name == "MakeEffectContext": return "native-effect-context"
        if name == "MakeGameplayCueParameters": return "native-cue-parameters"
        if name in ("EffectContextAddHitResult", "BP_ApplyGameplayEffectToTarget"): return None
        raise AssertionError((cls,name,args,kwargs))
    def trace(self): policy.trace(self.ability)
    def names(self): return [name for name, _ in self.order]
    def test_original_hand_socket_basis_distance_end(self):
        self.trace(); data = self.calls["CapsuleTraceSingleForObjects"][1]
        self.assertEqual(data["Start"].data(), [1.,2.,3.]); self.assertEqual(data["End"].data(), [351.,2.,3.])
    def test_native_capsule_configuration_and_pawn_query(self):
        self.trace(); data = self.calls["CapsuleTraceSingleForObjects"][1]
        self.assertEqual((data["Radius"],data["HalfHeight"],data["ObjectTypes"],data["bTraceComplex"],data["bIgnoreSelf"]),(96.,48.,[2],False,True))
        self.assertEqual(data["ActorsToIgnore"],[self.actor])
    def test_no_hit_does_not_apply_effect_or_cue(self): self.hit=False;self.trace();self.assertNotIn("GetAbilitySystemComponent",self.calls);self.assertNotIn("K2_ExecuteGameplayCueWithParams",self.names())
    def test_invalid_target_asc_stops_before_team(self): self.asc_valid=False;self.trace();self.assertNotIn("CompareTeams",self.calls)
    def test_same_team_stops_before_occlusion(self): self.team=0;self.trace();self.assertNotIn("LineTraceSingle",self.calls)
    def test_invalid_team_stops_before_occlusion(self): self.team=2;self.trace();self.assertNotIn("LineTraceSingle",self.calls)
    def test_native_team_comparison_argument_order(self): self.trace();self.assertEqual(self.calls["CompareTeams"][0],(self.target,self.actor))
    def test_occlusion_query_start_impact_and_ignore_both(self):
        self.trace();data=self.calls["LineTraceSingle"][1];self.assertEqual(data["TraceChannel"],3);self.assertEqual(data["ActorsToIgnore"],[self.target,self.actor]);self.assertEqual(data["End"].data(),[20.,2.,3.])
    def test_occluded_target_gets_no_root_or_damage(self): self.blocked=True;self.trace();self.assertNotIn("ApplyRootMotionConstantForce",self.calls)
    def test_root_uses_unclamped_native_normalize_ratio(self):
        self.hit_distance=700.;self.trace();data=self.calls["ApplyRootMotionConstantForce"][1];self.assertEqual(data["Strength"],4400.)
    def test_original_root_additive_gravity_and_finish_mode(self):
        self.trace();data=self.calls["ApplyRootMotionConstantForce"][1];self.assertEqual((data["bIsAdditive"],data["bEnableGravity"],data["VelocityOnFinishMode"],data["Duration"]),(True,True,0,.05))
    def test_root_ready_precedes_damage_sequence(self): self.trace();self.assertLess(self.names().index("root-ReadyForActivation"),self.names().index("MakeEffectContext"))
    def test_empty_original_hitresult_not_actual_capsule_result(self):
        self.trace();args=self.calls["EffectContextAddHitResult"][0];self.assertIsNot(args[1],self.hit_struct);self.assertEqual(vars(args[1]),{});self.assertIs(args[2],True)
    def test_original_effect_class_target_level_context(self):
        self.trace();args=self.calls["BP_ApplyGameplayEffectToTarget"][0]
        self.assertEqual(args,("/ShooterCore/Weapons/GE_Damage_Melee.GE_Damage_Melee_C","target-asc",1.,"native-effect-context"))
    def test_cue_default_fields_not_invented_hit_metadata(self):
        self.trace();data=self.calls["MakeGameplayCueParameters"][1];self.assertEqual((data["NormalizedMagnitude"],data["RawMagnitude"]),(0.,0.));self.assertIsNone(data["SourceObject"]);self.assertIsNone(data["Instigator"]);self.assertEqual(data["Normal"].data(),[0.,0.,0.])
    def test_cue_stays_on_owner_after_damage(self): self.trace();self.assertLess(self.names().index("BP_ApplyGameplayEffectToTarget"),self.names().index("K2_ExecuteGameplayCueWithParams"))
    def test_four_explicit_local_profile_methods(self):
        for cls in (policy.LyraMeleeTracePythonProfile,policy.LyraMeleeTraceBlueprintFallbackProfile):
            names=[name for name,value in cls.__dict__.items() if not name.startswith("__") and callable(value)]
            self.assertEqual(len(names),4);self.assertEqual(cls.AuthorityTrace.override,policy.TRACE)
    def test_const_arrays_are_native_outputs_with_return_first(self):
        fields = policy.native_outputs("KismetSystemLibrary", "CapsuleTraceSingleForObjects", (True, [2], [self.actor], self.hit_struct))
        self.assertEqual(fields["ObjectTypes"], [2]); self.assertIs(fields["OutHit"], self.hit_struct); self.assertIs(fields["ReturnValue"], True)
    def test_missing_const_arrays_rejects_short_shape(self):
        with self.assertRaises(RuntimeError): policy.trace_outputs("CapsuleTraceSingleForObjects", (True, self.hit_struct))
    def test_trace_return_must_be_actual_bool(self):
        with self.assertRaises(RuntimeError): policy.trace_outputs("CapsuleTraceSingleForObjects", (1, [2], [], self.hit_struct))
    def test_template_spelling_also_retains_const_array_outputs(self):
        desc = self.description("KismetSystemLibrary", "LineTraceSingle")
        desc["parameters"][0]["type"] = "TArray<AActor*>"
        with patch.object(policy.ue, "describe_function", lambda cls, name: desc):
            self.assertIs(policy.trace_outputs("LineTraceSingle", (False, [], self.hit_struct))[1], self.hit_struct)
