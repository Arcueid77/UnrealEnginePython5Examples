"""Shared firing order, authority, exact task/timer identities and failure policy."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");enums=types.ModuleType("unreal_engine.enums");structs=types.ModuleType("unreal_engine.structs")
enums.ESpawnActorCollisionHandlingMethod=types.SimpleNamespace(Undefined=0);enums.ESpawnActorScaleMethod=types.SimpleNamespace(SelectDefaultAtRuntime=2)
structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw)
validity=types.ModuleType("uep_lyra_world.effect_pad_mixin");validity.valid=lambda value:value is not None
trace=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");trace.native_outputs=lambda cls,name,value:{"ReturnValue":value};trace.break_hit=lambda hit:hit
spec=importlib.util.spec_from_file_location("_weapon_ability_fire_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_ability_fire_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.enums":enums,"unreal_engine.structs":structs,"uep_lyra_world.effect_pad_mixin":validity,"uep_lyra_abilities.melee_trace_mixin":trace}):spec.loader.exec_module(policy)


class NativeObject:
    def __init__(self,owner,kind):self.owner,self.kind=owner,kind
    def call_function(self,name,*args,**kw):
        self.owner.calls.append((self.kind,name,args,kw))
        if name=="IsDeadOrDying":return self.owner.dead


class TestWeaponAbilityFireMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.authority=True;self.local=True;self.dead=False;self.blocked=False;self.random=0;self.random_values=[]
        self.task=NativeObject(self,"task");self.health=NativeObject(self,"health");self.field=object()
        self.data={"CharacterFireMontage":"fire-montage","AutoRate":2.2,"FireDelayTimeSecs":.5,"Failure Montage Delay Time":1.,
            "Can Trigger Failure Montage":True,"Gameplay Cue TagFiring":"fire-cue","GameplayCue_Impact":"impact-cue","GE_Damage":"damage-class","FieldActorToSpawnOnImpact":None}
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.ability)
        native.find_class=lambda cls:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda name,*args,**kw:self.backend(cls,name,args,kw)))
        native.load_object=lambda cls,path:path;native.FVector=lambda *args:args or (0.,0.,0.);native.FRotator=lambda:(0.,0.,0.);native.FTransform=lambda *args:args
        self.hit_actor=types.SimpleNamespace(call_function=lambda name:(1.,0.,0.) if name=="GetActorForwardVector" else (0.,1.,0.))
    def write(self,name,value):self.calls.append(("write",name,value));self.data[name]=value
    def ability(self,name,*args,**kw):
        self.calls.append(("ability",name,args,kw))
        if name=="IsLocallyControlled":return self.local
        if name=="K2_HasAuthority":return self.authority
        if name=="GetAvatarActorFromActorInfo":return "pawn"
        if name=="GetAbilitySystemComponentFromActorInfo":return "asc"
    def backend(self,cls,name,args,kw):
        self.calls.append((cls,name,args,kw))
        if name=="CreatePlayMontageAndWaitProxy":return self.task
        if name=="GetHitResultFromTargetData":return args[0][args[1]] if args[1]<len(args[0]) else self.hit(False)
        if name=="GetDataCountFromTargetData":return len(args[0])
        if name=="MakeGameplayCueParametersFromHitResult":return {"hit":args[0]}
        if name=="IsValidClass":return args[0] is not None
        if name=="BeginDeferredActorSpawnFromClass":return self.field
        if name=="FindHealthComponent":return self.health
        if name=="DoesTagAssetInterfaceHaveTag":return self.blocked
        if name=="Dot_VectorVector":return sum(a*b for a,b in zip(*args))
        if name=="InRange_FloatFloat":return args[1]<=args[0]<=args[2]
        if name=="RandomIntegerInRange":
            value=self.random_values.pop(0) if self.random_values else self.random
            self.assertGreaterEqual(value,args[0]);self.assertLessEqual(value,args[1]);return value
    @staticmethod
    def hit(blocking,point=(10.,20.,30.)):return dict(bBlockingHit=blocking,ImpactPoint=point)
    def names(self,kind):return [row[1] for row in self.calls if row[0]==kind]
    def test_local_targeting_precedes_montage_and_timer(self):
        policy.activate(self.actor);names=[row[1] for row in self.calls if row[0] in ("ability","AbilityTask_PlayMontageAndWait","task","KismetSystemLibrary")]
        self.assertLess(names.index("StartRangedWeaponTargeting"),names.index("CreatePlayMontageAndWaitProxy"));self.assertLess(names.index("ReadyForActivation"),names.index("K2_SetTimer"))
    def test_remote_context_still_starts_native_task_and_timer(self):
        self.local=False;policy.activate(self.actor);self.assertNotIn("StartRangedWeaponTargeting",self.names("ability"));self.assertIn("ReadyForActivation",self.names("task"));self.assertIn("K2_SetTimer",self.names("KismetSystemLibrary"))
    def test_fire_montage_original_options_and_exact_binding_before_activation(self):
        policy.activate(self.actor);kw=next(row[3] for row in self.calls if row[1]=="CreatePlayMontageAndWaitProxy")
        self.assertEqual((kw["MontageToPlay"],kw["Rate"],kw["bStopWhenAbilityEnds"],kw["AnimRootMotionTranslationScale"],kw["StartTimeSeconds"],kw["bAllowInterruptAfterBlendOut"]),("fire-montage",2.2,False,1.,0.,False))
        self.assertLess(next(i for i,r in enumerate(self.calls) if r[1]==policy.BIND),next(i for i,r in enumerate(self.calls) if r[1]=="ReadyForActivation"))
    def test_invalid_task_still_requests_original_timer(self):
        self.task=None;policy.activate(self.actor);self.assertNotIn(policy.BIND,self.names("ability"));self.assertIn("K2_SetTimer",self.names("KismetSystemLibrary"))
    def test_native_named_timer_owner_and_original_zero_jitter_options(self):
        policy.activate(self.actor);kw=next(row[3] for row in self.calls if row[1]=="K2_SetTimer")
        self.assertIs(kw["Object"],self.actor);self.assertEqual((kw["FunctionName"],kw["Time"],kw["bLooping"],kw["bMaxOncePerFrame"],kw["InitialStartDelay"],kw["InitialStartDelayVariance"]),(policy.COMPLETE,.5,False,False,0.,0.))
    def test_zero_duration_is_forwarded_to_native_timer_semantics(self):
        self.data["FireDelayTimeSecs"]=0.;policy.activate(self.actor);self.assertEqual(next(row[3]["Time"] for row in self.calls if row[1]=="K2_SetTimer"),0.)
    def test_original_montage_callback_function_identities_retained(self):
        cls=policy.LyraWeaponAbilityFirePythonProfile
        self.assertEqual([cls.MontageCompleted.override,cls.MontageInterrupted.override,cls.MontageCancelled.override],list(policy.FIRE_CALLBACKS.values()))
    def test_native_completions_only_end_ability_without_timer_cancellation(self):
        cls=policy.LyraWeaponAbilityFirePythonProfile
        for fn in (cls.FireComplete,cls.MontageCompleted,cls.MontageInterrupted,cls.MontageCancelled):fn(self.actor)
        self.assertEqual(self.names("ability"),["K2_EndAbility"]*4);self.assertEqual(self.names("KismetSystemLibrary"),[])
    def test_firing_cue_occurs_once_before_blocking_impact_cues(self):
        policy.target_data(self.actor,[self.hit(False),self.hit(True),self.hit(True)])
        tags=[row[2][0] for row in self.calls if row[1]=="K2_ExecuteGameplayCueWithParams"]
        self.assertEqual(tags,["fire-cue","impact-cue","impact-cue"])
    def test_nonblocking_hit_never_spawns_field_actor(self):
        self.data["FieldActorToSpawnOnImpact"]="field-class";policy.target_data(self.actor,[self.hit(False)])
        self.assertNotIn("BeginDeferredActorSpawnFromClass",self.names("GameplayStatics"))
    def test_damage_once_for_whole_target_handle_after_all_hits(self):
        data=[self.hit(True),self.hit(True)];policy.target_data(self.actor,data)
        rows=[row for row in self.calls if row[1]=="BP_ApplyGameplayEffectToTarget"]
        self.assertEqual(len(rows),1);self.assertIs(rows[0][3]["TargetData"],data);self.assertEqual((rows[0][3]["GameplayEffectLevel"],rows[0][3]["Stacks"]),(1,1))
        self.assertGreater(self.calls.index(rows[0]),max(i for i,row in enumerate(self.calls) if row[1]=="K2_ExecuteGameplayCueWithParams"))
    def test_predicting_client_cues_but_never_damage_or_field_spawns(self):
        self.authority=False;self.data["FieldActorToSpawnOnImpact"]="field-class";policy.target_data(self.actor,[self.hit(True)])
        self.assertEqual(self.names("ability").count("K2_ExecuteGameplayCueWithParams"),2);self.assertNotIn("BP_ApplyGameplayEffectToTarget",self.names("ability"));self.assertNotIn("BeginDeferredActorSpawnFromClass",self.names("GameplayStatics"))
    def test_empty_target_data_still_firing_cue_and_authority_apply_request(self):
        policy.target_data(self.actor,[]);self.assertEqual(self.names("ability").count("K2_ExecuteGameplayCueWithParams"),1);self.assertIn("BP_ApplyGameplayEffectToTarget",self.names("ability"))
    def test_gcn_parameter_uses_first_hit_including_nonblocking(self):
        data=[self.hit(False),self.hit(True,(99.,0.,0.))];policy.target_data(self.actor,data);self.assertIs(self.data["GCNParameter"]["hit"],data[0])
    def test_field_actor_uses_impact_point_original_spawn_defaults(self):
        self.data["FieldActorToSpawnOnImpact"]="field-class";policy.target_data(self.actor,[self.hit(True)])
        kw=next(row[3] for row in self.calls if row[1]=="BeginDeferredActorSpawnFromClass")
        self.assertEqual(kw["SpawnTransform"],((10.,20.,30.),(0.,0.,0.),(1.,1.,1.)));self.assertEqual((kw["Owner"],kw["CollisionHandlingOverride"],kw["TransformScaleMethod"]),(None,0,2))
    def test_invalid_field_class_skips_only_optional_spawn(self):
        policy.target_data(self.actor,[self.hit(True)]);self.assertNotIn("BeginDeferredActorSpawnFromClass",self.names("GameplayStatics"));self.assertIn("BP_ApplyGameplayEffectToTarget",self.names("ability"))
    def test_other_avatar_failure_is_noop(self):
        policy.failure(self.actor,"other","failure-montage");self.assertNotIn("FindHealthComponent",self.names("LyraHealthComponent"));self.assertNotIn("K2_SetTimer",self.names("KismetSystemLibrary"))
    def test_dead_avatar_failure_is_noop(self):
        self.dead=True;policy.failure(self.actor,"pawn","failure-montage");self.assertNotIn("CreatePlayMontageAndWaitProxy",self.names("AbilityTask_PlayMontageAndWait"))
    def test_missing_health_component_still_allows_original_failure_branch(self):
        self.health=None;policy.failure(self.actor,"pawn","failure-montage");self.assertIn("CreatePlayMontageAndWaitProxy",self.names("AbilityTask_PlayMontageAndWait"))
    def test_no_firing_tag_suppresses_failure_montage(self):
        self.blocked=True;policy.failure(self.actor,"pawn","failure-montage");self.assertNotIn("CreatePlayMontageAndWaitProxy",self.names("AbilityTask_PlayMontageAndWait"));self.assertIs(self.data["Can Trigger Failure Montage"],True)
    def test_throttled_failure_suppressed(self):
        self.data["Can Trigger Failure Montage"]=False;policy.failure(self.actor,"pawn","failure-montage");self.assertNotIn("K2_SetTimer",self.names("KismetSystemLibrary"))
    def test_failure_task_options_and_flag_then_timer_order(self):
        policy.failure(self.actor,"pawn","failure-montage");kw=next(row[3] for row in self.calls if row[1]=="CreatePlayMontageAndWaitProxy")
        self.assertEqual((kw["MontageToPlay"],kw["Rate"],kw["bStopWhenAbilityEnds"]),("failure-montage",1.,True));self.assertNotIn(policy.BIND,self.names("ability"))
        self.assertLess(next(i for i,row in enumerate(self.calls) if row[:2]==("write","Can Trigger Failure Montage")),next(i for i,row in enumerate(self.calls) if row[1]=="K2_SetTimer"))
    def test_failure_native_timer_uses_original_spaced_callback(self):
        policy.failure(self.actor,"pawn","failure-montage");kw=next(row[3] for row in self.calls if row[1]=="K2_SetTimer");self.assertEqual((kw["FunctionName"],kw["Time"]),(policy.FAILURE_COMPLETE,1.))
    def test_failure_timer_callback_reenables_original_flag(self):
        self.data["Can Trigger Failure Montage"]=False;policy.LyraWeaponAbilityFirePythonProfile.FailureComplete(self.actor);self.assertIs(self.data["Can Trigger Failure Montage"],True)
    def test_added_delegates_native_listener_start_without_python_scope(self):
        policy.LyraWeaponAbilityFirePythonProfile.Added(self.actor);self.assertEqual(self.names("ability"),[policy.LISTEN]);self.assertFalse(any("scope" in key for key in vars(self.actor)))
    def test_front_choice_preserves_all_four_random_asset_options(self):
        for index,expected in enumerate(policy.MONTAGES["front"]):self.random_values=[index,0];self.assertEqual(policy.select(self.actor,(1.,0.,0.),self.hit_actor)["Hit Montage"],expected)
    def test_side_sign_maps_to_original_right_and_left_options(self):
        self.assertEqual(policy.select(self.actor,(0.,1.,0.),self.hit_actor)["Hit Montage"],policy.MONTAGES["right"][0]);self.assertEqual(policy.select(self.actor,(0.,-1.,0.),self.hit_actor)["Hit Montage"],policy.MONTAGES["left"][0])
    def test_half_boundaries_are_inclusive_straight_branch(self):
        for right in (-.5,.5):self.assertEqual(policy.select(self.actor,(1.,right,0.),self.hit_actor)["Hit Montage"],policy.MONTAGES["front"][0])
    def test_zero_forward_dot_is_back(self):self.assertEqual(policy.select(self.actor,(0.,0.,0.),self.hit_actor)["Hit Montage"],policy.MONTAGES["back"][0])
    def test_straight_select_evaluates_both_front_then_back_native_draws(self):
        policy.select(self.actor,(1.,0.,0.),self.hit_actor);calls=[row for row in self.calls if row[1]=="RandomIntegerInRange"];self.assertEqual([row[2] for row in calls],[(0,3),(0,1)])
    def test_unusual_authored_second_back_asset_is_retained(self):
        self.random=1;self.assertIn("Front_Med_02",policy.select(self.actor,(-1.,0.,0.),self.hit_actor)["Hit Montage"])
    def test_fallback_preserves_native_target_handle_and_generated_callback(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args);data=[self.hit(True)]
        policy.LyraWeaponAbilityFireBlueprintFallbackProfile.TargetData(self.actor,data);policy.LyraWeaponAbilityFireBlueprintFallbackProfile.MontageCompleted(self.actor)
        self.assertEqual(self.calls,[("OnRangedWeaponTargetDataReady",data),(policy.FIRE_CALLBACKS["OnCompleted"],)])
