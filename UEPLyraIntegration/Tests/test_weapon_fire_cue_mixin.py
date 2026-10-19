"""Original Cue call order, exact contexts, first-item macro and Rifle defaults."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");structs=types.ModuleType("unreal_engine.structs");structs.GameplayCueParameters=lambda:"empty-native-cue-params"
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
trace=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");trace.native_outputs=lambda cls,name,result:result
spec=importlib.util.spec_from_file_location("_weapon_fire_cue_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_fire_cue_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.structs":structs,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_abilities.melee_trace_mixin":trace}):spec.loader.exec_module(policy)


class Object:
    def __init__(self,owner,label):self.owner,self.label=owner,label
    def call_function(self,name,*args):return self.owner.call(self.label,name,args)
    def is_a(self,cls):return self.owner.actor_type_ok


class TestWeaponFireCueMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.weapon=Object(self,"weapon");self.instance=Object(self,"instance");self.equipment=Object(self,"equipment");self.audio=Object(self,"audio")
        self.target=Object(self,"target");self.instances=[self.instance];self.actors=[self.weapon];self.actor_type_ok=True;self.name="Pistol"
        self.cue=types.SimpleNamespace(get_class=lambda:types.SimpleNamespace(get_path_name=lambda:policy.CLASSES[self.name]),call_mixin_original=self.original)
        self.params=types.SimpleNamespace(PhysicalMaterial=None,Location=object(),Normal=object());self.spawns=object()
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:Object(self,"gas")) if name=="AbilitySystemBlueprintLibrary" else name;native.load_object=lambda cls,path:path
        native.load_class=lambda name:types.SimpleNamespace(get_cdo=lambda:self.audio) if name==policy.AUDIO else name
    def original(self,name,*args):self.calls.append(("original",name,args));return "original"
    def call(self,label,name,args):
        self.calls.append((label,name,args))
        if name=="GetComponentByClass":return self.equipment
        if name=="GetEquipmentInstancesOfType":return self.instances
        if name=="GetSpawnedActors":return self.actors
        if name=="BreakGameplayCueParameters":return dict(Location=args[0].Location,Normal=args[0].Normal,PhysicalMaterial=args[0].PhysicalMaterial)
    def run_burst(self):return policy.burst(self.cue,self.target,self.params,self.spawns)
    def audio_names(self):return [row[1] for row in self.calls if row[0]=="audio"]
    def test_exact_per_weapon_strengths_and_world_context_are_retained(self):
        for name,strength in (("Pistol",.1),("Rifle",.15),("Shotgun",.2)):
            self.calls=[];self.name=name;self.run_burst();row=next(row for row in self.calls if row[1]=="SendWeaponFire");self.assertEqual(row[2],(self.target,strength,self.cue))
    def test_send_weapon_fire_precedes_the_native_equipment_lookup(self):
        self.run_burst();self.assertEqual(self.calls[0][1],"SendWeaponFire");self.assertEqual(self.calls[1],("target","GetComponentByClass",("LyraEquipmentManagerComponent",)))
    def test_native_macro_uses_first_instance_and_first_actor(self):
        later=Object(self,"later");self.instances=[None,later];self.run_burst();self.assertNotIn("GetSpawnedActors",[row[1] for row in self.calls]);self.assertEqual(self.audio_names(),["SendWeaponFire"])
    def test_invalid_first_spawned_actor_does_not_scan_later_actors(self):
        self.actors=[None,self.weapon];self.run_burst();self.assertEqual(self.audio_names(),["SendWeaponFire"])
    def test_empty_or_wrong_class_weapon_short_circuits_remaining_audio(self):
        for actors,valid in (([],True),([self.weapon],False)):
            self.calls=[];self.actors=actors;self.actor_type_ok=valid;self.run_burst();self.assertEqual(self.audio_names(),["SendWeaponFire"])
    def test_cue_location_normal_and_default_surface_are_singleton_arrays(self):
        self.run_burst();row=next(row for row in self.calls if row[1]=="Fire");self.assertEqual(row[2],([self.params.Location],[self.params.Normal],[0]))
    def test_physical_material_surface_is_forwarded_without_recomputation(self):
        self.params.PhysicalMaterial=types.SimpleNamespace(get_property=lambda name:4);self.run_burst();self.assertEqual(next(row for row in self.calls if row[1]=="Fire")[2][2],[4])
    def test_audio_order_and_spawn_results_identity(self):
        self.run_burst();self.assertEqual(self.audio_names(),["SendWeaponFire","SetWeaponSoundParams","EarlyReflections","WhizBy"])
        row=next(row for row in self.calls if row[1]=="SetWeaponSoundParams");self.assertEqual(row[2],(self.target,self.spawns,self.cue))
    def test_rifle_only_audio_occurs_between_fire_and_sound_parameters(self):
        self.name="Rifle";self.run_burst();names=[row[1] for row in self.calls];self.assertLess(names.index("Fire"),names.index("TriggerFireAudio"));self.assertLess(names.index("TriggerFireAudio"),names.index("SetWeaponSoundParams"))
        self.assertEqual(next(row for row in self.calls if row[1]=="TriggerFireAudio")[2],(policy.RIFLE_SOUND,self.target))
    def test_rifle_early_reflections_uses_empty_params_but_whizby_uses_input(self):
        self.name="Rifle";self.run_burst();self.assertEqual(next(row for row in self.calls if row[1]=="EarlyReflections")[2][1],"empty-native-cue-params");self.assertIs(next(row for row in self.calls if row[1]=="WhizBy")[2][1],self.params)
    def test_other_weapons_retain_input_early_reflections_parameters(self):
        for name in ("Pistol","Shotgun"):
            self.calls=[];self.name=name;self.run_burst();self.assertIs(next(row for row in self.calls if row[1]=="EarlyReflections")[2][1],self.params)
    def test_invalid_target_retains_original_diagnostic_path(self):
        self.assertEqual(policy.burst(self.cue,None,self.params,self.spawns),"original");self.assertEqual(self.calls,[("original","OnBurst",(None,self.params,self.spawns))])
    def test_fallback_preserves_original_typed_parameter_objects(self):
        result=policy.LyraWeaponFireCueBlueprintFallbackProfile.OnBurst(self.cue,self.target,self.params,self.spawns);self.assertEqual(result,"original");self.assertEqual(self.calls,[("original","OnBurst",(self.target,self.params,self.spawns))])
