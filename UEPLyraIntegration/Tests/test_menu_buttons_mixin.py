"""Material, callback, text and native latent transport policy contracts."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.load_class=lambda p:p;native.load_object=lambda c,p:p;native.find_class=lambda n:n;native.find_struct=lambda n:lambda **kw:types.SimpleNamespace(**kw)
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._menu_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/menu_buttons_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class MenuPolicyTests(unittest.TestCase):
    def setUp(self):
        policy.ue=native;self.calls=[];self.tile=False;self.values=dict(IsDisabled=False,OnPressed='pressed',OnHovered='hover',PressProgress=.5,UseIconOverride=False,Font=object(),TextCase=2,KeyArtTexture=object());self.border=self.obj('border-material');self.font=self.obj('font-material');self.art=self.obj('art-material')
        for n in ('ButtonBorder','ButtonTextBlock','KeyArt'):self.values[n]=self.obj(n)
        self.w=types.SimpleNamespace(get_property=self.values.get,set_property=self.values.__setitem__,is_a=lambda c:self.tile,call_function=lambda f,*a:self.calls.append(('widget',f,*a)));policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.calls.append((n,f,*a)))
    def obj(self,n):return types.SimpleNamespace(call_function=lambda f,*a:self.object_call(n,f,a))
    def object_call(self,n,f,a):
        if f=='GetDynamicMaterial':return self.art if n=='KeyArt' else self.border
        if f=='GetDynamicFontMaterial':return self.font
        self.calls.append((n,f,*a))
    def test_registry_sees_all_shared_methods_in_each_own_class_dictionary(self):
        for c in (policy.LyraMenuMenuPythonProfile,policy.LyraMenuTilePythonProfile,policy.LyraMenuMenuBlueprintFallbackProfile,policy.LyraMenuTileBlueprintFallbackProfile):
            names=[v.override for v in vars(c).values() if callable(v) and hasattr(v,'override')];self.assertEqual(len(names),15);self.assertEqual(len(set(names)),15)
    def test_disabled_hover_and_selection_are_noops(self):
        self.values['IsDisabled']=True
        for fn in (policy.hover,policy.unhover,policy.select,policy.deselect,policy.click):fn(self.w)
        self.assertFalse(self.calls)
    def test_selected_animation_has_disabled_guard_not_selected_state_guard(self):
        policy.select(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationForward','pressed',1.,False)])
    def test_reset_stops_pressed_before_both_material_parameter_resets(self):
        policy.reset(self.w);self.assertEqual(self.calls,[('widget','StopAnimation','pressed'),('border-material','SetScalarParameterValue','Hover_Animate',0.),('font-material','SetScalarParameterValue','Hover_Animate',0.),('border-material','SetScalarParameterValue','Pressed_Animate',0.),('font-material','SetScalarParameterValue','Pressed_Animate',0.)])
    def test_disable_sets_flag_and_both_materials_then_reset(self):
        policy.disable(self.w);self.assertTrue(self.values['IsDisabled']);self.assertEqual(self.calls,[('border-material','SetScalarParameterValue','bIsDisabled',1.),('font-material','SetScalarParameterValue','bIsDisabled',1.),('widget','ResetMaterials')])
    def test_enable_keeps_existing_hover_and_press_values(self):
        self.values['IsDisabled']=True;policy.enable(self.w);self.assertFalse(self.values['IsDisabled']);self.assertEqual([c[2] for c in self.calls],['bIsDisabled','bIsDisabled'])
    def test_missing_native_material_is_a_noop_for_that_target(self):
        self.font=None;policy.reset(self.w);self.assertEqual(len(self.calls),3)
    def test_click_only_starts_original_native_latent_path(self):
        policy.click(self.w);self.assertEqual(self.calls,[('widget',policy.NATIVE_CLICK)])
    def test_click_sound_does_not_restart_animation(self):
        policy.clicksound(self.w);self.assertEqual(self.calls[0][1],'PlaySound2D');self.assertIn('MainMenu_Select',self.calls[0][3])
    def test_hover_icon_override_chooses_submenu_sound(self):
        self.values['UseIconOverride']=True;policy.hover(self.w);self.assertEqual(self.calls[0][1],'PlayAnimationForward');self.assertIn('SubMenu_Highlight',self.calls[1][3])
    def test_tile_uses_lobby_sound_independent_of_icon_property(self):
        self.tile=True;policy.clicksound(self.w);self.assertIn('Lobby_Select',self.calls[0][3])
    def test_native_finished_callback_reverses_only_when_enabled(self):
        policy.finished(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationReverse','pressed',1.,False)]);self.calls=[];self.values['IsDisabled']=True;policy.finished(self.w);self.assertFalse(self.calls)
    def test_menu_font_and_transform_use_original_opaque_font(self):
        policy.textstyle(self.w);self.assertEqual(self.calls,[('ButtonTextBlock','SetFont',self.values['Font']),('ButtonTextBlock','SetTextTransformPolicy',2)])
    def test_tile_labels_and_menu_text_never_cross_python_ftext(self):
        self.tile=True;self.assertIs(policy.textstyle(self.w),True);self.assertIs(policy.text(self.w),True);self.assertFalse(self.calls)
    def test_preconstruct_and_construct_order_is_text_art_reset(self):
        self.tile=True;policy.pre(self.w,False);self.assertEqual([c[1] for c in self.calls],['UpdateTextStyle','UpdateTileArt','ResetMaterials'])
    def test_raw_progress_is_not_clamped(self):
        for value in (-.25,0.,.5,1.,1.25):self.values['PressProgress']=value;self.assertEqual(policy.progress(self.w),dict(UseOriginal=False,Progress=value))
    def test_tile_texture_parameter_preserves_native_texture_identity(self):
        policy.art(self.w);self.assertEqual(self.calls,[('art-material','SetTextureParameterValue','TileArt',self.values['KeyArtTexture'])])
