"""Authored audio branch distinctions and native API argument semantics."""
import importlib.util
import math
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");structs=types.ModuleType("unreal_engine.structs")
structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw);structs.TapDelayInfo=lambda **kw:types.SimpleNamespace(**kw)
world_policy=types.ModuleType("uep_lyra_world.effect_pad_mixin");world_policy.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location("_weapon_audio_dispatch_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_audio_dispatch_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.structs":structs,"uep_lyra_world.effect_pad_mixin":world_policy}):spec.loader.exec_module(policy)


class Object:
    def __init__(self,cls="Actor",**fields):self.cls=cls;self.fields=fields;self.calls=[];self.values={}
    def is_a(self,cls):return self.cls==cls
    def get_property(self,name):return self.fields.get(name)
    def get_component_by_type(self,cls):return self.fields.get(cls)
    def call_function(self,name,*args):
        self.calls.append((name,args))
        if name=="SetIntParameter":self.values[args[0]]=args[1];return
        value=self.fields.get(name)
        return value(*args) if callable(value) else value


class TestWeaponAudioDispatchMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.pawn=Object("Pawn");self.manager=Object();self.state=Object("LyraGameState",**{"music":self.manager});self.preset=Object()
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend)) if name.endswith("Library") or name=="GameplayStatics" else name
        native.load_class=lambda path:"music";native.FLinearColor=lambda *args:args;native.load_object=lambda *args:self.preset
    def backend(self,name,*args):
        self.calls.append((name,args))
        if name=="GetPlayerPawn":return self.pawn
        if name=="GetGameState":return self.state
        if name=="GetDisplayName":return "Pawn_9"
        if name=="Len":return len(args[0])
        if name=="GetCharacterAsNumber":return ord(args[0][args[1]])
        if name=="Conv_DoubleToString":return format(args[0],".4f")
        if name=="Conv_StringToName":return ("native-name",args[0])
        if name=="Subtract_VectorVector":return tuple(a-b for a,b in zip(*args))
        if name=="VSize":return math.sqrt(sum(v*v for v in args[0]))
        if name=="Conv_DoubleToFloat":return struct.unpack("<f",struct.pack("<f",args[0]))[0]
        if name in ("MapRangeClamped","MapRangeUnclamped"):
            value,a,b,c,d=args;t=(value-a)/(b-a)
            if name=="MapRangeClamped":t=max(0.,min(1.,t))
            return c+t*(d-c)
        if name=="Normal":
            size=math.sqrt(sum(v*v for v in args[0]));return tuple(v/size for v in args[0]) if size*size>args[1] else (0.,0.,0.)
        if name=="GetRightVector":return (0.,1.,0.)
        if name=="Dot_VectorVector":return sum(a*b for a,b in zip(*args))
    def pawn_chain(self,local):
        item=Object(HasStatTag=True,GetStatTagStackCount=17);bar=Object(GetActiveSlotItem=item);controller=Object(LyraQuickBarComponent=bar)
        instigator=Object("Pawn",GetController=controller);return Object("Pawn",Instigator=instigator,IsLocallyViewed=local)
    def test_nonlocal_preserves_existing_ammo_but_local_sets_both_in_order(self):
        for local in (False,True):
            audio=Object();audio.values={"MagazineAmmo":777,"Other":3};policy.sound_params(self.pawn_chain(local),types.SimpleNamespace(AudioComponents=[None,audio]))
            self.assertEqual(audio.values,{"MagazineAmmo":17 if local else 777,"PawnSeed":-1 if local else ord("9"),"Other":3})
            self.assertEqual([args[0] for _,args in audio.calls],["PawnSeed","MagazineAmmo"] if local else ["PawnSeed"])
    def test_macro_uses_instigator_controller_and_aborts_on_missing_quickbar(self):
        pawn=Object("Pawn",Instigator=Object("Pawn",GetController=Object()),IsLocallyViewed=True);audio=Object()
        policy.sound_params(pawn,types.SimpleNamespace(AudioComponents=[audio]));self.assertEqual(audio.calls,[])
    def test_invalid_pawn_and_instigator_exit_without_parameter_writes(self):
        for actor in (None,Object(),Object("Pawn",IsLocallyViewed=False)):
            audio=Object();policy.sound_params(actor,types.SimpleNamespace(AudioComponents=[audio]));self.assertEqual(audio.calls,[])
    def test_absent_ammo_tag_selects_zero(self):
        pawn=self.pawn_chain(True);item=pawn.fields["Instigator"].fields["GetController"].fields["LyraQuickBarComponent"].fields["GetActiveSlotItem"];item.fields["HasStatTag"]=False
        audio=Object();policy.sound_params(pawn,types.SimpleNamespace(AudioComponents=[audio]));self.assertEqual(audio.values["MagazineAmmo"],0)
    def test_empty_active_slot_selects_original_vm_to_preserve_null_target_diagnostics(self):
        pawn=self.pawn_chain(True);pawn.fields["Instigator"].fields["GetController"].fields["LyraQuickBarComponent"].fields["GetActiveSlotItem"]=None
        audio=Object();self.assertTrue(policy.sound_params(pawn,types.SimpleNamespace(AudioComponents=[audio])));self.assertEqual(audio.calls,[])
    def test_send_only_first_local_pawn_and_does_not_clamp_strength(self):
        for player in (None,Object("Pawn"),self.pawn):policy.send_fire(player,-2.5,"world")
        self.assertEqual(self.manager.calls,[("Receive Weapon Fire",(self.pawn,-2.5))])
    def test_missing_manager_uses_authored_screen_only_warning(self):
        self.state.fields.clear();policy.send_fire(self.pawn,3.,"world");name,args=self.calls[-1]
        self.assertEqual(name,"PrintString");self.assertEqual(args,("world","Pawn_9 does not have a MusicManager.",True,False,(1.,.376326,0.,1.),10.,"None"))
    def test_debug_keeps_native_float_strings_crlf_color_duration_and_suffix_name(self):
        policy.debug_tap("tap",.125,-9.5,180.,"world");name,args=self.calls[-1]
        self.assertEqual(name,"PrintString");self.assertEqual(args,("world","EarlyReflection.tap\r\nDelay : 0.1250\r\nGain : -9.5000\r\nPan : 180.0000",True,False,(0.,.526042,.159781,1.),5.,("native-name","tap")))
    def test_miss_preserves_delay_and_pan_and_resets_mode_channel_without_camera_access(self):
        self.preset.fields["GetTap"]=(types.SimpleNamespace(DelayLength=123.25,PanInDegrees=-67.125),)
        policy.tap_properties("unused",None,None,4,1e12,999.,False,None)
        name,args=self.preset.calls[-1];self.assertEqual(name,"SetTap");self.assertEqual(args[0],4)
        self.assertEqual(vars(args[1]),dict(TapLineMode=1,DelayLength=123.25,Gain=-60.,PanInDegrees=-67.125));self.assertEqual(self.calls,[])
    def test_hit_delay_unclamped_gain_clamped_camera_position_not_listener_and_no_debug(self):
        cam=Object(GetCameraLocation=(0.,1.,0.),GetCameraRotation=(0.,0.,0.))
        policy.tap_properties("unused",cam,(0.,0.,0.),4,-9876.,20000.,True,(1000.,0.,0.))
        value=self.preset.calls[-1][1][1];self.assertGreater(value.DelayLength,600.);self.assertEqual(value.Gain,-60.);self.assertEqual(value.PanInDegrees,180.)
        self.assertNotIn("PrintString",[name for name,_ in self.calls])
    def test_four_named_void_fallbacks_only_request_original(self):
        router=types.SimpleNamespace()
        for name in ("Send","Params","Debug","Tap"):
            handler=getattr(policy.LyraWeaponAudioDispatchBlueprintFallbackProfile,name);self.assertTrue(handler.uep_named_outputs)
            self.assertEqual(handler(router,None,None),dict(UseOriginal=True))
        self.assertEqual(self.calls,[])
