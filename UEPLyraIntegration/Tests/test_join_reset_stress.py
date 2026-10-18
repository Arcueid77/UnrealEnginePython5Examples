"""Bounded native-input scheduler models, not real GAS or replication."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

policy=types.ModuleType("uep_lyra_abilities.auto_respawn_helpers_mixin");policy.CLASS="auto"
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
native=types.ModuleType("unreal_engine");structs=types.ModuleType("unreal_engine.structs")
structs.GameplayTag=lambda **values:types.SimpleNamespace(**values);structs.GameplayEventData=lambda **values:types.SimpleNamespace(**values)
spec=importlib.util.spec_from_file_location("uep_lyra_abilities._join_reset_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/join_reset_stress.py")
stress=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.structs":structs,"uep_lyra_abilities.auto_respawn_helpers_mixin":policy,"uep_lyra_world.effect_pad_mixin":helpers}): spec.loader.exec_module(stress)


class Obj:
    def __init__(self,name,fields=None): self.name,self.fields=name,fields or {};self.PlayerId=256
    def get_path_name(self): return self.name
    def get_property(self,name): return self.fields[name]
    def get_class(self): return self
    def call_function(self,name):
        if name!="IsActorBeingDestroyed": raise AssertionError(name)
        return False
    def get_controlled_pawn(self): return self.pawn


class TestJoinResetStress(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.mapped=True;self.role=3
        self.specification=types.SimpleNamespace(Ability=Obj(stress.RESET_CLASS))
        self.asc=Obj("asc",dict(ActivatableAbilities=types.SimpleNamespace(Items=[self.specification])))
        self.state=Obj("state",dict(AbilitySystemComponent=self.asc));self.controller=Obj("controller",dict(PlayerState=self.state));self.controller.pawn=Obj("2")
        def native_send(*args):
            self.calls.append(args);pawn=self.controller.pawn
            counts=getattr(pawn,"_uep_character_lifecycle",dict(reset_python=0));counts["reset_python"]+=1;pawn._uep_character_lifecycle=counts
        api=types.SimpleNamespace(find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=native_send)))
        for item in (patch.object(stress,"ue",api),patch.object(stress.wire,"read",lambda pawn:dict(valid=self.mapped,transport="Legacy",wire_id=pawn.name,local_role=self.role))):
            item.start();self.addCleanup(item.stop)
        self.value=stress.JoinResetStress(Path("unused"),"model")
    def test_native_input_not_a_callback(self):
        self.value.consider(self.controller,1.)
        self.assertEqual(self.calls[0][0],"SendGameplayEventToActor");self.assertEqual(self.calls[0][2].TagName,"GameplayEvent.RequestReset")
        self.assertEqual(len(self.value.report["requests"]),1)
    def test_does_not_allocate_a_missing_wire_id(self):
        self.mapped=False;self.value.consider(self.controller,1.);self.assertEqual(self.calls,[])
    def test_requires_existing_native_reset_spec(self):
        self.asc.fields["ActivatableAbilities"].Items=[];self.value.consider(self.controller,1.);self.assertEqual(self.calls,[])
    def test_same_native_actor_not_reset_twice(self):
        self.value.consider(self.controller,1.);self.value.consider(self.controller,2.);self.assertEqual(len(self.calls),1)
    def test_interval_does_not_overlap_pending_restart(self):
        self.value.consider(self.controller,1.);self.controller.pawn=Obj("4");self.value.consider(self.controller,1.1);self.assertEqual(len(self.calls),1)
    def test_two_distinct_actual_pawns_then_stop(self):
        self.value.consider(self.controller,1.);self.controller.pawn=Obj("4");self.value.consider(self.controller,1.2)
        self.controller.pawn=Obj("6");self.value.consider(self.controller,2.);self.assertEqual(len(self.calls),2)
    def test_client_authority_write_not_allowed(self):
        self.role=2
        with self.assertRaisesRegex(RuntimeError,"authority"): self.value.consider(self.controller,1.)
    def test_native_callback_must_really_execute(self):
        with patch.object(stress,"ue",types.SimpleNamespace(find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda *args:None)))):
            with self.assertRaisesRegex(RuntimeError,"exactly one"): self.value.consider(self.controller,1.)
    def test_no_health_or_asc_repair_api(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/join_reset_stress.py").read_text(encoding="utf-8")
        for value in ('set_property(', 'InitializeAbilitySystem', 'SetNumericAttribute', 'TryActivateAbilityByClass'): self.assertNotIn(value,text)
