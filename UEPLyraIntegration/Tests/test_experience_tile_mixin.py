"""Retain original material asymmetry, unwired sound output and latent guards."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.load_class=lambda p:p;native.load_object=lambda c,p:p;native.find_class=lambda n:n
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._experience_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/experience_tile_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class ExperiencePolicyTests(unittest.TestCase):
    def setUp(self):
        policy.ue=native;self.calls=[];self.cast=True;self.spawned=object();self.data=dict(IsDisabled=False,OnPressed='pressed',OnHovered='hover',PressProgress=.5);self.gi=types.SimpleNamespace(is_a=lambda c:self.cast,set_property=lambda n,v:self.calls.append(('instance',n,v)))
        for n in ('ButtonBorder','ExperienceTitle','MapTitle','ExperienceDescription','KeyArt'):self.data[n]=types.SimpleNamespace(call_function=lambda f,*a,n=n:self.object_call(n,f,a))
        self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.data.__setitem__,call_function=lambda f,*a:self.calls.append(('widget',f,*a)));policy.lib=lambda n:types.SimpleNamespace(call_function=self.library)
    def object_call(self,n,f,a):
        self.calls.append((n,f,*a))
        if f in ('GetDynamicMaterial','GetDynamicFontMaterial'):return types.SimpleNamespace(call_function=lambda method,*args:self.calls.append((n+'-material',method,*args)))
    def library(self,f,*a):
        self.calls.append(('library',f,*a))
        if f=='GetGameInstance':return self.gi
        if f=='SpawnSound2D':return self.spawned
    def test_reset_stops_animation_then_resets_four_materials(self):
        policy.reset(self.w);writes=[c for c in self.calls if c[1]=='SetScalarParameterValue'];self.assertEqual(self.calls[0],('widget','StopAnimation','pressed'));self.assertEqual(len(writes),8);self.assertEqual({c[0] for c in writes},{n+'-material' for n in ('ButtonBorder','ExperienceTitle','MapTitle','ExperienceDescription')});self.assertEqual({c[2] for c in writes},{'Hover_Animate','Pressed_Animate'})
    def test_disable_changes_only_border_disabled_value_before_reset(self):
        policy.disable(self.w);self.assertTrue(self.data['IsDisabled']);self.assertEqual(self.calls,[('ButtonBorder','GetDynamicMaterial'),('ButtonBorder-material','SetScalarParameterValue','bIsDisabled',1.),('widget','ResetMaterials')])
    def test_enable_does_not_create_font_materials_or_reset_animations(self):
        self.data['IsDisabled']=True;policy.enable(self.w);self.assertFalse(self.data['IsDisabled']);self.assertEqual(self.calls,[('ButtonBorder','GetDynamicMaterial'),('ButtonBorder-material','SetScalarParameterValue','bIsDisabled',0.)])
    def test_unwired_spawned_sound_result_clears_game_instance_field(self):
        policy.clicksound(self.w);self.assertEqual(self.calls[-1],('instance','Audio_LobbySelect',None));self.assertNotIn(('instance','Audio_LobbySelect',self.spawned),self.calls);self.assertEqual(self.calls[0][-2:],(True,True))
    def test_failed_game_instance_cast_keeps_spawn_but_skips_clear(self):
        self.cast=False;policy.clicksound(self.w);self.assertEqual(self.calls[0][1],'SpawnSound2D');self.assertFalse(any(c[0]=='instance' for c in self.calls))
    def test_missing_game_instance_keeps_spawn(self):
        self.gi=None;policy.clicksound(self.w);self.assertEqual(self.calls[0][1],'SpawnSound2D')
    def test_selected_plays_press_then_lobby_select_sound(self):
        policy.select(self.w);self.assertEqual(self.calls[0],('widget','PlayAnimationForward','pressed',1.,False));self.assertEqual(self.calls[1][1],'PlaySound2D');self.assertIn('Lobby_Select',self.calls[1][3])
    def test_disabled_animation_and_click_entries_are_noops(self):
        self.data['IsDisabled']=True
        for f in (policy.hover,policy.unhover,policy.select,policy.deselect,policy.click):f(self.w)
        self.assertFalse(self.calls)
    def test_click_starts_only_original_native_latent_adapter(self):
        policy.click(self.w);self.assertEqual(self.calls,[('widget',policy.NATIVE_CLICK)])
    def test_finished_resamples_disabled_flag(self):
        self.data['IsDisabled']=True;policy.finished(self.w);self.assertFalse(self.calls);self.data['IsDisabled']=False;policy.finished(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationReverse','pressed',1.,False)])
    def test_art_uses_parameter_without_storing_new_widget_property(self):
        texture=object();policy.art(self.w,texture);self.assertEqual(self.calls[-1],('KeyArt-material','SetTextureParameterValue','TileArt',texture));self.assertNotIn('TileArt',self.data)
    def test_construct_and_preconstruct_only_reset(self):
        policy.pre(self.w,True);policy.construct(self.w);self.assertEqual(self.calls,[('widget','ResetMaterials'),('widget','ResetMaterials')])
    def test_progress_is_unclamped(self):
        for v in (-.25,0.,.5,1.,1.25):self.data['PressProgress']=v;self.assertEqual(policy.progress(self.w),dict(UseOriginal=False,Progress=v))
