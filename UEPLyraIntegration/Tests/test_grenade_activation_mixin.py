"""Activation/aim ordering models,not native grenade or damage acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

class Vec:
    def __init__(self,x=0.,y=0.,z=0.): self.x,self.y,self.z=x,y,z
class Rot:
    def __init__(self,roll=0.,pitch=0.,yaw=0.): self.roll,self.pitch,self.yaw=roll,pitch,yaw
native=types.ModuleType("unreal_engine");structs=types.ModuleType("unreal_engine.structs");enums=types.ModuleType("unreal_engine.enums")
structs.LyraInteractionDurationMessage=lambda **values:types.SimpleNamespace(**values)
enums.ESpawnActorCollisionHandlingMethod=types.SimpleNamespace(AlwaysSpawn=1);enums.ESpawnActorScaleMethod=types.SimpleNamespace(OverrideRootScale=2)
enums.ETraceTypeQuery=types.SimpleNamespace(TraceTypeQuery4=3);enums.EDrawDebugTrace=types.SimpleNamespace(**{"None":0})
ui=types.ModuleType("uep_lyra_abilities.grenade_widget_mixin")
class Ui:
    def K2_OnPawnAvatarSet(self): pass
    def K2_OnAbilityRemoved(self): pass
ui.LyraGrenadeWidgetPythonProfile=Ui;ui.LyraGrenadeWidgetBlueprintFallbackProfile=Ui
traces=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");traces.trace_outputs=lambda method,result:result;traces.break_hit=lambda value:value
events=types.ModuleType("uep_lyra_abilities.auto_respawn_events_mixin");events.broadcast=lambda *args:None
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location("uep_lyra_abilities._grenade_activation_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_activation_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.structs":structs,"unreal_engine.enums":enums,"uep_lyra_abilities.grenade_widget_mixin":ui,
    "uep_lyra_abilities.melee_trace_mixin":traces,"uep_lyra_abilities.auto_respawn_events_mixin":events,"uep_lyra_world.effect_pad_mixin":helpers}): spec.loader.exec_module(policy)

class Object:
    def __init__(self,fields=None,calls=None): self.fields,self.calls=fields or {},calls or {}
    def get_property(self,name): return self.fields[name]
    def set_property(self,name,value): self.fields[name]=value
    def call_function(self,name,*args,**kwargs):
        value=self.calls[name]
        return value(*args,**kwargs) if callable(value) else value


class TestGrenadeActivationMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.hit=True;self.distance=100.;self.task_valid=True;self.spawn_valid=True
        self.camera=Object(calls=dict(GetCameraLocation=Vec(0.,0.,50.),GetCameraRotation=Rot()))
        self.control=Rot(1.,2.,3.);self.controller=Object(dict(PlayerCameraManager=self.camera),dict(GetControlRotation=self.control))
        self.character=Object(calls=dict(K2_GetActorLocation=Vec(100.,200.,300.),GetActorForwardVector=Vec(0.,1.,0.),GetActorUpVector=Vec(0.,0.,1.)))
        self.ability=Object(dict(**{"Default Targeting Range":1000.,"Start Trace Offset":10.,"Cooldown Time":7.,"GrenadeThrowMontage":"montage"}),
            dict(K2_CheckAbilityCost=True,K2_CheckAbilityCooldown=True,K2_CommitAbility=False,K2_HasAuthority=True,
                GetLyraCharacterFromActorInfo=self.character,GetLyraPlayerControllerFromActorInfo=self.controller,GetCooldownTimeRemaining=5.,K2_EndAbility=lambda:self.calls.append("end")))
        self.original_call=self.ability.call_function
        def observed(name,*args,**kwargs): self.calls.append(name);return self.original_call(name,*args,**kwargs)
        self.ability.call_function=observed
        self.projectile=Object();self.projectile.set_property=lambda name,value:self.calls.append(("instigator",name,value))
        self.task=Object(calls=dict(ReadyForActivation=lambda:self.calls.append("ready")))
        native=types.SimpleNamespace(FVector=Vec,FRotator=Rot,FTransform=lambda *args:args,FLinearColor=lambda *args:args,load_class=lambda name:name)
        for item in (patch.object(policy,"ue",native),patch.object(policy,"lib",self.library),
            patch.object(policy,"broadcast",lambda ability,suffix,channel,payload:self.calls.append(("message",channel,payload.Duration,payload.Instigator)))):
            item.start();self.addCleanup(item.stop)
    def library(self,name): return types.SimpleNamespace(call_function=lambda method,*args,**kwargs:self.native_call(name,method,*args,**kwargs))
    def native_call(self,library,method,*args,**kwargs):
        if method=="Add_VectorVector": return Vec(*(getattr(args[0],key)+getattr(args[1],key) for key in ("x","y","z")))
        if method=="Multiply_VectorFloat": return Vec(*(getattr(args[0],key)*args[1] for key in ("x","y","z")))
        if method=="Conv_RotatorToVector": return Vec(1.,0.,0.)
        if method=="Less_DoubleDouble": return args[0]<args[1]
        if method=="FindLookAtRotation": self.calls.append(("look",args[0],args[1]));return Rot(4.,5.,6.)
        if method=="LineTraceSingle": self.calls.append(("trace",kwargs));return self.hit,dict(Distance=self.distance,Location=Vec(500.,20.,30.),ImpactPoint=Vec(999.,999.,999.))
        if method=="MakeTransform": return args
        if method=="BeginDeferredActorSpawnFromClass": self.calls.append(("begin-spawn",args));return self.projectile if self.spawn_valid else None
        if method=="FinishSpawningActor": self.calls.append(("finish-spawn",args));return args[0]
        if method=="CreatePlayMontageAndWaitProxy": self.calls.append(("montage",kwargs));return self.task if self.task_valid else None
        raise AssertionError(method)
    def activate(self): policy.LyraGrenadeActivationPythonProfile.K2_ActivateAbility(self.ability)
    def test_checks_both_even_when_cost_denied(self):
        self.ability.calls["K2_CheckAbilityCost"]=False;self.activate()
        self.assertEqual(self.calls[:3],["K2_CheckAbilityCost","K2_CheckAbilityCooldown","K2_EndAbility"])
        self.assertEqual(policy.evidence(self.ability)["commits"],0)
    def test_cooldown_denied_ends_without_commit_or_trace(self):
        self.ability.calls["K2_CheckAbilityCooldown"]=False;self.activate();self.assertEqual(policy.evidence(self.ability)["aim_queries"],0)
    def test_commit_false_return_is_original_ignored_value(self): self.activate();self.assertEqual(policy.evidence(self.ability)["projectiles"],1)
    def test_location_uses_actor_basis_offset_not_socket_or_camera(self):
        self.activate();self.assertEqual(policy.vector(self.ability.fields["Location"]),[100.,205.,325.])
    def test_hit_direction_uses_hit_location_not_impact(self):
        self.activate();look=next(call for call in self.calls if isinstance(call,tuple) and call[0]=="look")
        self.assertEqual(policy.vector(look[2]),[500.,20.,30.])
    def test_near_predicate_precedes_miss_boolean(self):
        self.hit=False;self.distance=0.;self.activate();self.assertIs(self.ability.fields["Direction"],self.control)
    def test_strict_45_boundary_not_near(self):
        self.distance=45.;self.activate();self.assertEqual(policy.evidence(self.ability)["near_control_rotation"],0)
    def test_miss_far_uses_default_target_endpoint(self):
        self.hit=False;self.activate();look=next(call for call in self.calls if isinstance(call,tuple) and call[0]=="look")
        self.assertEqual(policy.vector(look[2]),[1000.,0.,50.])
    def test_instigator_assigned_before_finish_spawn(self):
        self.activate();labels=[call[0] if isinstance(call,tuple) else call for call in self.calls]
        self.assertLess(labels.index("begin-spawn"),labels.index("instigator"));self.assertLess(labels.index("instigator"),labels.index("finish-spawn"))
    def test_native_spawn_failure_still_continues_original_cooldown_montage_message_end(self):
        self.spawn_valid=False;self.activate();self.assertEqual(policy.evidence(self.ability)["cooldown_writes"],1);self.assertEqual(policy.evidence(self.ability)["native_ends"],1)
    def test_non_authority_does_not_write_cooldown_or_spawn(self):
        self.ability.calls["K2_HasAuthority"]=False;self.activate()
        counts=policy.evidence(self.ability);self.assertEqual((counts["projectiles"],counts["cooldown_writes"]),(0,0))
        message=next(call for call in self.calls if isinstance(call,tuple) and call[0]=="message");self.assertEqual(message[2],7.)
    def test_native_montage_not_stopped_and_no_wait_for_completion(self):
        self.activate();task=next(call for call in self.calls if isinstance(call,tuple) and call[0]=="montage")
        self.assertFalse(task[1]["bStopWhenAbilityEnds"]);self.assertLess(self.calls.index("ready"),self.calls.index("K2_EndAbility"))
        self.assertEqual(policy.evidence(self.ability)["duration_messages"],1)
    def test_invalid_task_does_not_create_synthetic_completion(self):
        self.task_valid=False;self.activate();self.assertNotIn("ready",self.calls);self.assertEqual(policy.evidence(self.ability)["native_ends"],1)
    def test_original_profile_calls_original_native_event_once(self):
        calls=[];ability=Object();ability.call_mixin_original=lambda name:calls.append(name)
        policy.LyraGrenadeActivationBlueprintFallbackProfile.K2_ActivateAbility(ability);self.assertEqual(calls,["K2_ActivateAbility"])
    def test_no_new_ticker_subscription_or_montage_callback_business(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_activation_mixin.py").read_text(encoding="utf-8")
        for value in ('add_ticker','bind_event','SubscriptionScope','call_mixin_original("K2_ActivateAbility")'):
            if value.startswith('call_mixin'): continue
            self.assertNotIn(value,text)
