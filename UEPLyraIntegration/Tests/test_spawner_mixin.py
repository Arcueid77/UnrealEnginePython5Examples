"""Spawner policy models; native collision/timers/replication are separate."""
import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object

class SpawnerPolicy(unittest.TestCase):
    def setUp(self):
        self.phase, self.slot, self.spare, self.reload = False, 1, 12, False
        self.existing = None
        self.calls = []
        native = types.ModuleType("unreal_engine");native.find_class = lambda name: name
        native.load_object = lambda *args: "material"
        native.FLinearColor = lambda *values:values
        native.call_function_by_class = lambda *args: {"ReturnValue": self.reload}
        structs = types.ModuleType("unreal_engine.structs");structs.GameplayTag = lambda **kwargs: kwargs["TagName"]
        dependency = types.ModuleType("uep_lyra_world.effect_pad_mixin")
        dependency.valid = lambda value: value is not None and value.is_valid()
        dependency.ability_system = lambda pawn: getattr(pawn, "asc", None)
        self.root = Path(__file__).resolve().parents[1]
        file = self.root/"Overlay/Content/Scripts/uep_lyra_world/spawner_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_world._spawner_policy", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native,"unreal_engine.structs":structs,"uep_lyra_world.effect_pad_mixin":dependency}):
            spec.loader.exec_module(self.module)
        self.module.library = lambda cls: Object(cls, lambda name,*args,**kwargs:self.library(cls,name,*args,**kwargs))
        self.item = Object("item", lambda name,*args:self.spare if name == "GetStatTagStackCount" else None)
        self.inventory = Object("inventory", lambda name,*args:self.existing if name == "FindFirstItemStackByDefinition" else self.item)
        self.bar = Object("bar", lambda name,*args:self.slot if name == "GetNextFreeItemSlot" else None)
        self.controller = Object("controller")
        self.controller.get_component_by_type = lambda cls:self.bar if cls == "LyraQuickBarComponent" else self.inventory
        self.pawn = Object("pawn", lambda name,*args:self.controller)
        self.health, self.max_health = 75.0, 100.0
        self.pawn.asc = Object("asc")
        self.pawn.get_component_by_type = lambda cls:Object("health", lambda name,*args:self.health if name == "GetHealth" else self.max_health)
        self.actor = Object("spawner")
        self.actor.get_class = lambda:"spawner-class"
        self.actor.GiveAmmoForDuplicatedWeapons = self.actor.IgnorePickUpWhenReload = True
        self.actor.GameplayEffectToApply = "heal-effect"
        self.actor.get_property = lambda name:50.0

    def library(self, cls, name, *args, **kwargs):
        self.calls.append((cls,name,*args,kwargs))
        if name == "GetWorldSubsystem":
            return Object("phase",lambda *args:self.phase)
        if name == "GetDefaultStatFromItemDef":
            return 50
        if name == "MakeGameplayCueParameters":
            return kwargs
        if name == "Multiply_LinearColorFloat":
            return "native-scaled-color"
        if name == "Multiply_LinearColorLinearColor":
            return tuple(a*b for a,b in zip(args[0],args[1]))

    def test_fresh_grant_uses_cue_inventory_slot_then_native_select(self):
        self.assertTrue(self.module.weapon(self.actor,"rifle",self.pawn))
        self.assertEqual(self.inventory.calls,[("FindFirstItemStackByDefinition","rifle"),("AddItemDefinition","rifle",1)])
        self.assertEqual(self.bar.calls,[("GetNextFreeItemSlot",),("AddItemToSlot",1,self.item),("SetActiveSlotIndex",1)])
        self.assertEqual(self.module.snapshot()["cues"],1)

    def test_full_bar_rejects_without_item_or_cue(self):
        self.slot = -1
        self.assertFalse(self.module.weapon(self.actor,"rifle",self.pawn))
        self.assertNotIn(("AddItemDefinition","rifle",1),self.inventory.calls)
        self.assertEqual(self.module.snapshot()["cues"],0)

    def test_duplicate_refills_existing_native_stat_not_new_item(self):
        self.existing = self.item
        self.assertTrue(self.module.weapon(self.actor,"rifle",self.pawn))
        self.assertIn(("AddStatTagStack",self.module.SPARE,38),self.item.calls)
        self.assertEqual(self.bar.calls,[])
        self.assertEqual(self.module.snapshot()["refills"],1)

    def test_duplicate_full_uses_retained_failure_rpc_no_cue(self):
        self.existing,self.spare = self.item,50
        self.assertFalse(self.module.weapon(self.actor,"rifle",self.pawn))
        self.assertEqual(self.actor.calls,[("Broadcast Failure Message",self.pawn)])
        self.assertEqual(self.module.snapshot()["cues"],0)

    def test_duplicate_ammo_disabled_can_grant_another_instance(self):
        self.existing,self.actor.GiveAmmoForDuplicatedWeapons = self.item,False
        self.assertTrue(self.module.weapon(self.actor,"rifle",self.pawn))
        self.assertIn(("AddItemDefinition","rifle",1),self.inventory.calls)

    def test_reload_guard_preserves_new_item_without_selection(self):
        self.reload = True
        self.assertTrue(self.module.weapon(self.actor,"rifle",self.pawn))
        self.assertNotIn(("SetActiveSlotIndex",1),self.bar.calls)
        self.actor.IgnorePickUpWhenReload = False
        self.assertTrue(self.module.weapon(self.actor,"rifle",self.pawn))
        self.assertIn(("SetActiveSlotIndex",1),self.bar.calls)

    def test_post_game_rejects_before_inventory(self):
        self.phase = True
        self.assertFalse(self.module.weapon(self.actor,"rifle",self.pawn))
        self.assertEqual(self.inventory.calls,[])

    def test_missing_controller_or_asc_rejects(self):
        self.pawn.callback = lambda *args:None
        self.assertFalse(self.module.weapon(self.actor,"rifle",self.pawn))
        self.pawn.asc = None
        self.assertFalse(self.module.ability(self.actor,"ignored",self.pawn))

    def test_ability_applies_original_zero_level_only_when_below_max(self):
        self.assertTrue(self.module.ability(self.actor,"ignored",self.pawn))
        self.assertEqual(self.pawn.asc.calls,[("BP_ApplyGameplayEffectToSelf","heal-effect",0.0)])
        self.health = 100.0
        self.assertFalse(self.module.ability(self.actor,"ignored",self.pawn))
        self.assertEqual(len(self.pawn.asc.calls),1)

    def test_begin_skips_native_out_hit_result_by_keyword(self):
        self.actor.WeaponMesh = Object("mesh")
        self.assertFalse(self.module.LyraSpawnerPythonProfile.Begin(self.actor))
        self.assertEqual(self.actor.WeaponMesh.calls,[("K2_AddWorldOffset",50.0,False,{"bTeleport":False})])

    def test_construction_scales_rgb_but_retains_original_alpha(self):
        mid=Object("mid")
        self.actor.PadMesh=Object("pad",lambda *args:mid)
        self.actor.set_property=lambda name,value:setattr(self.actor,name,value)
        self.actor.LightColor=(1.0,.5,.25,.7)
        self.actor.LightIntensity,self.actor.LightRadius,self.actor.LifeTimeReload=500.0,300.0,10.0
        for name in ("PointLight","NS_GunPad","NS_GunPad_Loading","WeaponMesh"):
            setattr(self.actor,name,Object(name))
        self.module.construct(self.actor)
        self.assertIn(("SetVectorParameterValue","Color",(.02,.01,.005,.7)),mid.calls)

    def test_generator_and_policy_parse(self):
        ast.parse((self.root/"Tools/generate_spawner_mixin_assets.py").read_text(encoding="utf-8"))
