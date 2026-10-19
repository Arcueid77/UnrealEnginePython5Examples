"""Original inclusive ray fan, native template geometry and overlap API policy."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");enums=types.ModuleType("unreal_engine.enums");structs=types.ModuleType("unreal_engine.structs")
enums.ETraceTypeQuery=types.SimpleNamespace(TraceTypeQuery2=2);enums.EDrawDebugTrace=types.SimpleNamespace(**{"None":0});structs.GameplayEffectContextHandle=lambda:"empty-native-context"
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
trace=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");trace.native_outputs=lambda cls,name,value:value;trace.break_hit=lambda hit:hit
spec=importlib.util.spec_from_file_location("_netshooter_actor_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/netshooter_actor_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.enums":enums,"unreal_engine.structs":structs,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_abilities.melee_trace_mixin":trace}):spec.loader.exec_module(policy)


class Component:
    def __init__(self,owner,label):self.owner,self.label=owner,label
    def call_function(self,name,*args,**kw):self.owner.calls.append((self.label,name,args,kw))


class TestNetShooterActorMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.random_values=[];self.trace_hit=True
        self.sphere=Component(self,"sphere");self.component=Component(self,"ray");self.source=Component(self,"source-asc");self.target=Component(self,"target-asc")
        self.data={"NumberOfWeb":12,"OffsetImpact":25.,"DistanceTrace":2500.,"Sphere":self.sphere}
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=lambda name,value:self.data.__setitem__(name,value),get_actor_location=lambda:(-1.,0.,0.),call_function=self.actor_call)
        native.find_class=lambda cls:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda name,*args,**kw:self.backend(name,args,kw)))
        native.load_class=lambda path:path;native.FVector=lambda *args:args or (0.,0.,0.);native.FTransform=lambda *args:args;native.FLinearColor=lambda *args:args
    def actor_call(self,name,*args,**kw):
        self.calls.append(("actor",name,args,kw))
        if name=="GetInstigator":return "instigator"
        if name=="AddComponent":return self.component
    def backend(self,name,args,kw):
        self.calls.append(("native",name,args,kw))
        if name=="Add_VectorVector":return tuple(a+b for a,b in zip(*args))
        if name=="Multiply_VectorFloat":return tuple(a*args[1] for a in args[0])
        if name=="RandomFloatInRange":return self.random_values.pop(0) if self.random_values else 0.
        if name=="MakeVector":return args
        if name=="LineTraceSingle":return dict(ReturnValue=self.trace_hit,OutHit=self.hit_result())
        if name=="Vector_Distance":return sum((a-b)**2 for a,b in zip(*args))**.5
        if name=="FindLookAtRotation":return (0.,0.,0.)
        if name=="GetAbilitySystemComponent":return self.source if args[0]=="instigator" else self.target
    @staticmethod
    def hit_result():return dict(TraceStart=(0.,0.,0.),TraceEnd=(100.,0.,0.),ImpactPoint=(10.,0.,0.))
    def records(self,name):return [row for row in self.calls if row[1]==name]
    def test_default_number_twelve_emits_thirteen_rays(self):policy.hit(self.actor,(0.,0.,0.),(1.,0.,0.));self.assertEqual(len(self.records("LineTraceSingle")),13)
    def test_zero_number_still_one_ray(self):self.data["NumberOfWeb"]=0;policy.hit(self.actor,(0.,0.,0.),(1.,0.,0.));self.assertEqual(len(self.records("LineTraceSingle")),1)
    def test_negative_number_skips_rays_but_keeps_original_delay(self):
        self.data["NumberOfWeb"]=-1;policy.hit(self.actor,(0.,0.,0.),(1.,0.,0.));self.assertEqual(self.records("LineTraceSingle"),[]);self.assertEqual(self.calls[-1][1],policy.DELAY)
    def test_start_is_hit_location_plus_normal_offset(self):
        self.data["NumberOfWeb"]=-1;policy.hit(self.actor,(10.,20.,30.),(0.,1.,0.));self.assertEqual(self.data["Start"],(10.,45.,30.))
    def test_random_xyz_draw_order_and_end_are_unnormalized(self):
        self.data["NumberOfWeb"]=0;self.random_values=[1.,2.,3.];policy.hit(self.actor,(10.,20.,30.),(1.,0.,0.))
        self.assertEqual(self.records("LineTraceSingle")[0][3]["End"],(5010.,5020.,7530.));self.assertEqual([row[2] for row in self.records("RandomFloatInRange")],[(-10.,10.)]*3)
    def test_camera_trace_channel_complex_self_ignore_and_original_draw_options(self):
        self.data["NumberOfWeb"]=0;policy.hit(self.actor,(0.,0.,0.),(1.,0.,0.));kw=self.records("LineTraceSingle")[0][3]
        self.assertEqual((kw["TraceChannel"],kw["bTraceComplex"],kw["bIgnoreSelf"],kw["ActorsToIgnore"],kw["DrawDebugType"],kw["DrawTime"]),(2,True,True,[],0,5.))
    def test_each_blocking_trace_calls_original_rpc_entry(self):
        self.data["NumberOfWeb"]=1;policy.hit(self.actor,(0.,0.,0.),(1.,0.,0.));self.assertEqual(len(self.records("SpawnComponents")),2)
    def test_trace_miss_never_requests_rpc(self):
        self.trace_hit=False;self.data["NumberOfWeb"]=0;policy.hit(self.actor,(0.,0.,0.),(1.,0.,0.));self.assertEqual(self.records("SpawnComponents"),[])
    def test_policy_does_not_override_native_hit_or_multicast(self):
        self.assertFalse(hasattr(policy.LyraNetShooterActorPythonProfile,"ReceiveHit"));self.assertFalse(hasattr(policy.LyraNetShooterActorPythonProfile,"SpawnComponents"))
    def test_component_template_manual_attachment_transform_and_context(self):
        policy.spawn(self.actor,self.hit_result());kw=self.records("AddComponent")[0][3]
        self.assertEqual(kw,dict(TemplateName="NODE_AddStaticMeshComponent-0",bManualAttachment=True,RelativeTransform=((-1.,0.,0.),(0.,0.,0.),(10.,3.,3.)),ComponentTemplateContext=None,bDeferredFinish=False))
    def test_hidden_sphere_and_native_weak_overlap_bind_follow_creation(self):
        policy.spawn(self.actor,self.hit_result());self.assertEqual([row[1] for row in self.calls if row[0] in ("actor","sphere")],["AddComponent","SetHiddenInGame",policy.BIND])
    def test_failed_component_creation_still_hides_original_sphere(self):
        self.component=None;policy.spawn(self.actor,self.hit_result());self.assertEqual(len(self.records("SetHiddenInGame")),1);self.assertEqual(self.records(policy.BIND),[])
    def test_overlap_uses_native_instigator_source_target_and_original_level_zero(self):
        policy.overlap(self.actor,"victim");kw=self.records("BP_ApplyGameplayEffectToTarget")[0][3]
        self.assertEqual((kw["GameplayEffectClass"],kw["Target"],kw["Level"],kw["Context"]),(policy.DAMAGE,self.target,0.,"empty-native-context"))
    def test_overlap_does_not_add_an_authority_gate(self):policy.overlap(self.actor,"victim");self.assertEqual(self.records("HasAuthority"),[])
    def test_invalid_source_preserves_native_vm_noop(self):self.source=None;policy.overlap(self.actor,"victim");self.assertEqual(self.records("BP_ApplyGameplayEffectToTarget"),[])
    def test_invalid_target_is_forwarded_to_original_native_api(self):
        self.target=None;policy.overlap(self.actor,"victim");self.assertIsNone(self.records("BP_ApplyGameplayEffectToTarget")[0][3]["Target"])
    def test_life_continuation_only_destroys_actor(self):
        policy.LyraNetShooterActorPythonProfile.LifeEnded(self.actor);self.assertEqual([row[1] for row in self.calls],["K2_DestroyActor"])
    def test_fallback_preserves_original_body_and_life_entries(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args)
        policy.LyraNetShooterActorBlueprintFallbackProfile.HitBody(self.actor,"point","normal");policy.LyraNetShooterActorBlueprintFallbackProfile.SpawnBody(self.actor,"hit")
        policy.LyraNetShooterActorBlueprintFallbackProfile.LifeEnded(self.actor);self.assertEqual(self.calls,[(policy.HIT,"point","normal"),(policy.BODY,"hit"),(policy.AFTER,)])
