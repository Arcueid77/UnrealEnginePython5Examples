"""Preserve source menu/property split, view guards and world-time Tick logic."""
import importlib.util
import math
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");world=types.ModuleType("uep_lyra_world.effect_pad_mixin");world.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location("_music_manager_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_audio/music_manager_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":world}):spec.loader.exec_module(policy)


class Object:
    def __init__(self,**fields):self.fields=fields;self.calls=[]
    def get_property(self,name):return self.fields.get(name)
    def set_property(self,name,value):self.fields[name]=value
    def is_a(self,cls):return self.fields.get("class")==cls
    def call_function(self,name,*args):self.calls.append((name,args));return self.fields.get(name)


class TestMusicManagerMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.sound=Object(IsPlaying=True);self.component=Object(**{"Music System":self.sound,"Alpha_Intensity":.8,"Alpha_Mvmt":.2,"bIsMenu":False})
        self.pawn=Object(**{"class":"Pawn","IsLocallyViewed":True,"GetActorForwardVector":(.25,.5,0.),"GetVelocity":(450.,0.,0.)})
        native.find_class=lambda name:name if name=="Pawn" else types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend));native.FLinearColor=lambda *args:args
    def backend(self,name,*args):
        self.calls.append((name,args))
        if name=="FClamp":return max(args[1],min(args[2],args[0]))
        if name=="GetPlayerPawn":return self.pawn
        if name=="GetWorldDeltaSeconds":return .02
        if name=="MakeVector":return args
        if name=="Dot_VectorVector":return sum(a*b for a,b in zip(*args))
        if name=="VSize":return math.sqrt(sum(v*v for v in args[0]))
        if name=="MapRangeClamped":return max(0.,min(1.,(args[0]-args[1])/(args[2]-args[1])))
        if name=="FInterpTo":return args[0]+(args[1]-args[0])*max(0.,min(1.,args[2]*args[3]))
    def test_menu_changes_audio_parameter_only_and_does_not_start_stopped_sound(self):
        policy.set_menu(self.component,True);self.assertFalse(self.component.fields["bIsMenu"]);self.assertEqual(self.sound.calls,[("IsPlaying",()),("SetBoolParameter",("bIsMenu",True))])
        self.sound.calls=[];self.sound.fields["IsPlaying"]=False;policy.set_menu(self.component,True);self.assertEqual(self.sound.calls,[("IsPlaying",())])
    def test_locally_viewed_guard_accepts_pawn_not_controller_or_locally_controlled_alias(self):
        policy.fire(self.component,self.pawn,.5);self.assertEqual(self.component.fields["Alpha_Intensity"],1.)
        for player in (None,Object(**{"class":"Controller","IsLocallyViewed":True}),Object(**{"class":"Pawn","IsLocallyViewed":False})):
            self.component.fields["Alpha_Intensity"]=.4;policy.death(self.component,player);self.assertEqual(self.component.fields["Alpha_Intensity"],.4)
    def test_fire_clamps_after_addition_including_negative_start_and_strength(self):
        self.component.fields["Alpha_Intensity"]=1.25;policy.fire(self.component,self.pawn,-.5);self.assertEqual(self.component.fields["Alpha_Intensity"],.75)
        policy.fire(self.component,self.pawn,-2.);self.assertEqual(self.component.fields["Alpha_Intensity"],0.)
    def test_stinger_resets_even_negative_and_positive_trigger_requires_playing_sound(self):
        policy.stinger(self.component,False);self.assertEqual(self.component.fields["Alpha_Intensity"],0.);self.assertEqual(self.sound.calls,[])
        policy.stinger(self.component,True);self.assertEqual(self.sound.calls[-1],("SetTriggerParameter",("OnStingerPositive",)))
    def test_invalid_positive_stinger_preserves_source_screen_only_message(self):
        self.component.fields["Music System"]=None;policy.stinger(self.component,True)
        self.assertEqual(self.calls[-1],("PrintString",(self.component,"mx system not valid",True,False,(0.,.66,1.,1.),10.,"None")))
    def test_tick_uses_world_delta_not_event_delta_and_movement_does_not_feed_intensity(self):
        policy.tick(self.component,9999.);self.assertEqual(self.component.fields["Alpha_Mvmt"],.5);self.assertEqual(self.component.fields["Alpha_Intensity"],.8*(1.-.02*.05))
        self.assertEqual([args for name,args in self.sound.calls if name=="SetFloatParameter"],[("LookDir",.25),("Intensity",.8*(1.-.02*.05))])
    def test_menu_tick_still_decays_intensity_and_starts_stopped_sound(self):
        self.component.fields["bIsMenu"]=True;self.sound.fields["IsPlaying"]=False;policy.tick(self.component,0.)
        self.assertIn(("Play",(0.,)),self.sound.calls);self.assertEqual(self.component.fields["Alpha_Mvmt"],.2);self.assertNotIn("GetPlayerPawn",[name for name,_ in self.calls])
    def test_five_methods_exclude_native_begin_play_listener_lifecycle(self):
        self.assertEqual(len(policy.METHODS),5);self.assertNotIn("ReceiveBeginPlay",policy.METHODS)
        self.assertFalse(hasattr(policy.LyraMusicManagerPythonProfile,"ReceiveBeginPlay"))
