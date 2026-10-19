"""Prototype-specific empty callback, spawn basis, Cue fields and native order."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");enums=types.ModuleType("unreal_engine.enums");structs=types.ModuleType("unreal_engine.structs")
enums.ESpawnActorCollisionHandlingMethod=types.SimpleNamespace(Undefined=0);enums.ESpawnActorScaleMethod=types.SimpleNamespace(OverrideRootScale=0)
for name in ("GameplayEffectContextHandle","GameplayTag","GameplayTagContainer","HitResult"):setattr(structs,name,lambda n=name:("empty-native-"+n))
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location("_netshooter_ability_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/netshooter_ability_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.enums":enums,"unreal_engine.structs":structs,"uep_lyra_world.effect_pad_mixin":helpers}):spec.loader.exec_module(policy)


def vector(*args):return types.SimpleNamespace(**dict(zip(("x","y","z"),args)))
def xyz(value):return [value.x,value.y,value.z]


class Object:
    def __init__(self,owner,label,data=None):self.owner,self.label,self.data=owner,label,data or {}
    def get_property(self,name):return self.data.get(name)
    def set_property(self,name,value):self.owner.calls.append((self.label,"write",(name,value),{}));self.data[name]=value
    def call_function(self,name,*args,**kw):return self.owner.call(self.label,name,args,kw)
    def call_mixin_original(self,name,*args):self.owner.calls.append(("original",name,args,{}));return "original-result"


class TestNetShooterAbilityMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.local=True;self.authority=True;self.task=Object(self,"task");self.projectile=Object(self,"projectile")
        self.camera=Object(self,"camera");self.controller=Object(self,"controller",{"PlayerCameraManager":self.camera});self.mesh=Object(self,"mesh");self.pawn=Object(self,"pawn",{"Mesh":self.mesh})
        self.actor=Object(self,"ability",{"CharacterFireMontage":"montage","AutoRate":2.8,"OffsetGCN":vector(2.,3.,5.),"Gameplay Cue TagFiring":"shotgun-fire"})
        native.find_class=lambda cls:types.SimpleNamespace(get_cdo=lambda:Object(self,cls));native.load_class=lambda path:path;native.FTransform=lambda *args:args;native.FLinearColor=lambda *args:args
    def call(self,label,name,args,kw):
        self.calls.append((label,name,args,kw))
        if name=="IsLocallyControlled":return self.local
        if name=="K2_HasAuthority":return self.authority
        if name=="GetLyraPlayerControllerFromActorInfo":return self.controller
        if name=="GetLyraCharacterFromActorInfo":return self.pawn
        if name=="GetCameraLocation":return vector(10.125,20.5,30.25)
        if name=="GetCameraRotation":return "actual-camera-rotation"
        if name=="GetActorForwardVector":return vector(0.,1.,0.) if label=="controller" else vector(1.,0.,0.)
        if name=="GetActorUpVector":return vector(0.,0.,1.)
        if name=="GetActorRightVector":return vector(0.,1.,0.)
        if name=="GetSocketLocation":return vector(100.,200.,300.)
        if name=="GetSocketRotation":return "socket-rotation"
        if name=="Conv_RotatorToVector":return vector(.2,.3,.4)
        if name=="Add_VectorVector":return vector(*(a+b for a,b in zip(xyz(args[0]),xyz(args[1]))))
        if name=="Multiply_VectorFloat":return vector(*(a*args[1] for a in xyz(args[0])))
        if name=="MakeVector":return vector(*args)
        if name=="MakeGameplayCueParameters":return kw
        if name=="CreatePlayMontageAndWaitProxy":return self.task
        if name=="BeginDeferredActorSpawnFromClass":return self.projectile
    def first(self,name):return next(row for row in self.calls if row[1]==name)
    def names(self):return [row[1] for row in self.calls]
    def test_spawn_location_uses_controller_actor_forward_and_actual_camera_rotation(self):
        policy.pose(self.actor);self.assertEqual(xyz(self.actor.data["Location"]),[10.125,370.5,30.25]);self.assertEqual(self.actor.data["Direction"],"actual-camera-rotation");self.assertNotIn("GetControlRotation",self.names())
    def test_nonzero_cue_offsets_use_forward_x_then_up_z_then_right_y(self):
        policy.cue(self.actor,self.pawn);params=self.first("K2_ExecuteGameplayCueWithParams")[2][1];self.assertEqual(xyz(params["Location"]),[102.,203.,305.])
    def test_cue_normal_comes_from_named_character_mesh_socket_rotation(self):
        policy.cue(self.actor,self.pawn);self.assertEqual(self.first("GetSocketRotation")[2],("weapon_r_muzzle",));self.assertEqual(self.first("Conv_RotatorToVector")[2],("socket-rotation",))
    def test_cue_uses_empty_original_context_tags_and_source_fields(self):
        policy.cue(self.actor,self.pawn);p=self.first("MakeGameplayCueParameters")[3]
        self.assertEqual([p[key] for key in ("NormalizedMagnitude","RawMagnitude","GameplayEffectLevel","AbilityLevel","bReplicateLocationWhenUsingMinimalRepProxy")],[0.,0.,1,1,False])
        self.assertTrue(all(p[key] is None for key in ("Instigator","EffectCauser","SourceObject","PhysicalMaterial","TargetAttachComponent")));self.assertEqual(p["EffectContext"],"empty-native-GameplayEffectContextHandle")
    def test_native_targeting_precedes_task_and_cue_precedes_authority_spawn(self):
        policy.activate(self.actor);names=self.names();self.assertLess(names.index("StartRangedWeaponTargeting"),names.index("CreatePlayMontageAndWaitProxy"));self.assertLess(names.index("ReadyForActivation"),names.index("K2_ExecuteGameplayCueWithParams"));self.assertLess(names.index("K2_ExecuteGameplayCueWithParams"),names.index("K2_HasAuthority"))
    def test_native_task_original_defaults_and_bind_before_ready(self):
        policy.activate(self.actor);p=self.first("CreatePlayMontageAndWaitProxy")[3]
        self.assertEqual((p["Rate"],p["bStopWhenAbilityEnds"],p["AnimRootMotionTranslationScale"],p["StartTimeSeconds"],p["bAllowInterruptAfterBlendOut"]),(2.8,False,1.,0.,False));self.assertLess(self.names().index(policy.BIND),self.names().index("ReadyForActivation"))
    def test_spawn_uses_native_default_collision_no_owner_override_root_scale(self):
        policy.activate(self.actor);p=self.first("BeginDeferredActorSpawnFromClass")[3]
        self.assertEqual((p["ActorClass"],p["CollisionHandlingOverride"],p["Owner"],p["TransformScaleMethod"]),(policy.PROJECTILE,0,None,0));self.assertEqual(xyz(p["SpawnTransform"][2]),[.1,.1,.1])
    def test_exposed_empty_hit_and_instigator_are_written_before_finish_spawning(self):
        policy.activate(self.actor);self.assertEqual(self.projectile.data["HitBreakResult"],"empty-native-HitResult");self.assertIs(self.projectile.data["Instigator"],self.pawn)
        writes=[i for i,row in enumerate(self.calls) if row[0]=="projectile" and row[1]=="write"];self.assertTrue(all(i<self.names().index("FinishSpawningActor") for i in writes))
    def test_remote_authority_does_not_locally_target_but_still_montages_cues_spawns(self):
        self.local=False;policy.activate(self.actor);self.assertNotIn("StartRangedWeaponTargeting",self.names());self.assertIn("ReadyForActivation",self.names());self.assertIn("FinishSpawningActor",self.names())
    def test_predicting_client_still_cues_without_spawning_projectile(self):
        self.authority=False;policy.activate(self.actor);self.assertIn("K2_ExecuteGameplayCueWithParams",self.names());self.assertNotIn("BeginDeferredActorSpawnFromClass",self.names());self.assertIn("PrintString",self.names())
    def test_no_shared_fire_timer_is_registered(self):
        policy.activate(self.actor);self.assertNotIn("K2_SetTimer",self.names());self.assertNotIn("FireComplete",self.names())
    def test_child_target_data_is_an_explicit_empty_override(self):
        policy.LyraNetShooterAbilityPythonProfile.TargetData(self.actor,object());self.assertEqual(self.calls,[]);self.assertEqual(policy.evidence(self.actor)["target_data_noops"],1)
    def test_invalid_native_task_does_not_abort_original_post_task_sequence(self):
        self.task=None;policy.activate(self.actor);self.assertNotIn(policy.BIND,self.names());self.assertIn("FinishSpawningActor",self.names())
    def test_failed_native_spawn_keeps_original_print_continuation(self):
        self.projectile=None;policy.activate(self.actor);self.assertNotIn("FinishSpawningActor",self.names());self.assertIn("PrintString",self.names())
    def test_print_retains_original_text_screen_log_color_duration(self):
        policy.activate(self.actor);p=self.first("PrintString")[3];self.assertEqual((p["InString"],p["bPrintToScreen"],p["bPrintToLog"],p["TextColor"],p["Duration"]),("NETSHOOTER",True,True,(0.,.66,1.,1.),2.))
    def test_original_compiler_callbacks_only_end_the_native_ability(self):
        cls=policy.LyraNetShooterAbilityPythonProfile
        for name,event in (("Completed","OnCompleted"),("Interrupted","OnInterrupted"),("Cancelled","OnCancelled")):
            fn=getattr(cls,name);self.assertEqual(fn.override,policy.CALLBACKS[event]);fn(self.actor)
        self.assertEqual(self.names(),["K2_EndAbility"]*3)
    def test_fallback_keeps_child_empty_callback_and_compiler_identities(self):
        cls=policy.LyraNetShooterAbilityBlueprintFallbackProfile;handle=object();self.assertEqual(cls.TargetData(self.actor,handle),"original-result");self.assertIs(self.calls[0][2][0],handle)
        cls.Activate(self.actor);cls.Completed(self.actor);cls.Interrupted(self.actor);cls.Cancelled(self.actor)
        self.assertEqual(self.names(),["OnRangedWeaponTargetDataReady","K2_ActivateAbility",*policy.CALLBACKS.values()])
    def test_child_profiles_do_not_copy_shared_parent_business_methods(self):
        for cls in (policy.LyraNetShooterAbilityPythonProfile,policy.LyraNetShooterAbilityBlueprintFallbackProfile):
            self.assertEqual({name for name,fn in vars(cls).items() if callable(fn)},{"Activate","TargetData","Completed","Interrupted","Cancelled"})
