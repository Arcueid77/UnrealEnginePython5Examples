"""GI music decisions, typed message transforms and local inherited method family."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");world=types.ModuleType("uep_lyra_world.effect_pad_mixin");world.valid=lambda obj:obj is not None
controls=types.ModuleType("uep_lyra_audio.music_manager_mixin");controls.METHODS=("SetIsMenu","Receive Player Death","Receive Weapon Fire","Fire Stinger","ReceiveTick")
def noop(*args):pass
controls.LyraMusicManagerPythonProfile=type("ControlsPython",(),{name:noop for name in ("SetIsMenu","Death","Fire","Stinger","ReceiveTick")})
controls.LyraMusicManagerBlueprintFallbackProfile=type("ControlsFallback",(),{name:noop for name in ("SetIsMenu","Death","Fire","Stinger","ReceiveTick")})
spec=importlib.util.spec_from_file_location("uep_lyra_audio._music_lifecycle_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_audio/music_manager_lifecycle_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":world,"uep_lyra_audio.music_manager_mixin":controls}):spec.loader.exec_module(policy)


class Object:
    def __init__(self,cls="Actor",**values):self.cls=cls;self.values=values;self.calls=[]
    def is_a(self,cls):return self.cls==cls
    def get_property(self,name):return self.values.get(name)
    def set_property(self,name,value):self.values[name]=value
    def call_function(self,name,*args):self.calls.append((name,args));return self.values.get(name)


class TestMusicLifecycleMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.component=Object();self.sound=Object();self.game=Object("LyraGI",MusicSystem=self.sound)
        controls.lib=lambda name:types.SimpleNamespace(call_function=self.backend);controls.locally_viewed=lambda player:player is not None and player.cls=="Pawn" and player.values.get("local",False)
        native.load_class=lambda path:"LyraGI";native.find_class=lambda name:name;native.load_object=lambda cls,path:path
    def backend(self,name,*args,**kwargs):
        self.calls.append((name,args,kwargs))
        if name=="GetGameInstance":return self.game
        if name=="CreateSound2D":return self.sound
    def test_existing_gi_audio_reused_without_play_or_duplicate_creation(self):
        policy.begin(self.component);self.assertIs(self.component.values["Music System"],self.sound);self.assertEqual([name for name,_,_ in self.calls],["GetGameInstance"])
        self.assertEqual(self.component.calls,[(policy.START,())]);self.assertEqual(policy.evidence(self.component)["reused"],1)
    def test_create_uses_original_persistent_non_autodestroy_defaults_and_does_not_play(self):
        self.game.values["MusicSystem"]=None;policy.begin(self.component);name,args,kwargs=self.calls[-1]
        self.assertEqual(name,"CreateSound2D");self.assertEqual(kwargs,dict(WorldContextObject=self.component,Sound=policy.SOUND,VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,ConcurrencySettings=None,bPersistAcrossLevelTransition=True,bAutoDestroy=False))
        self.assertIs(self.game.values["MusicSystem"],self.sound);self.assertEqual(self.sound.calls,[])
    def test_wrong_game_instance_exits_before_music_or_subscriptions(self):
        self.game=Object("OtherGI");policy.begin(self.component);self.assertEqual(self.component.calls,[])
    def test_elimination_casts_player_state_then_passes_native_pawn_including_none(self):
        pawn=Object("Pawn");state=Object("PlayerState",GetPawn=pawn);self.assertFalse(policy.elimination(self.component,types.SimpleNamespace(Target=state)))
        self.assertEqual(self.component.calls,[("Receive Player Death",(pawn,))]);self.component.calls=[]
        policy.elimination(self.component,types.SimpleNamespace(Target=pawn));self.assertEqual(self.component.calls,[])
    def test_damage_filters_locally_viewed_pawn_and_uses_unconditional_strength_one(self):
        local=Object("Pawn",local=True);policy.damage(self.component,types.SimpleNamespace(Target=local));self.assertEqual(self.component.calls,[("Receive Weapon Fire",(local,1.))])
        self.component.calls=[];policy.damage(self.component,types.SimpleNamespace(Target=Object("Pawn",local=False)));self.assertEqual(self.component.calls,[])
    def test_complete_eight_method_profile_family_keeps_all_previous_controls(self):
        self.assertEqual(len(policy.METHODS),8)
        for cls in (policy.LyraMusicLifecyclePythonProfile,policy.LyraMusicLifecycleBlueprintFallbackProfile):
            self.assertTrue(all(name in vars(cls) for name in ("SetIsMenu","Death","Fire","Stinger","ReceiveTick","ReceiveBeginPlay","EliminationMessage","DamageMessage")))
    def test_fallback_gates_only_choose_retained_native_business(self):
        self.assertTrue(policy.LyraMusicLifecycleBlueprintFallbackProfile.EliminationMessage(self.component,None));self.assertTrue(policy.LyraMusicLifecycleBlueprintFallbackProfile.DamageMessage(self.component,None))
        self.assertEqual(self.component.calls,[])
