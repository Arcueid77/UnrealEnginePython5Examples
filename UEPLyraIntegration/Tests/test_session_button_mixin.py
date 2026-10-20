"""Session material target/order, disabled rules, native sounds and latent click."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');native.find_class=lambda name:name;native.load_object=lambda cls,name:name
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location('_session_button_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/session_button_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class SessionButtonPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.props=dict(IsDisabled=False,OnPressed='press',OnHovered='hover');self.materials={}
        for name in ('ButtonBorder','GameModeText','PingText','PingLabel','MapLabel','PlayersText','MapNameText','MaxPlayersText'):
            material=types.SimpleNamespace(call_function=lambda fn,*args,n=name:self.calls.append((n,fn,*args)));self.materials[name]=material;self.props[name]=types.SimpleNamespace(call_function=lambda fn,*args,n=name:self.get(n,fn,args))
        self.w=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=lambda fn,*args:self.calls.append(('widget',fn,*args)));policy.ue=native;policy.lib=lambda name:types.SimpleNamespace(call_function=lambda fn,*args:self.calls.append((name,fn,*args)))
    def get(self,name,fn,args):self.calls.append(('get',name,fn));return self.materials[name]
    def set(self,name,value):self.props[name]=value;self.calls.append(('set',name,value))
    def test_reset_preserves_native_getter_order_including_two_unused_labels(self):
        policy.invoke(self.w,'reset');self.assertEqual([v[1] for v in self.calls if v[0]=='get'],['ButtonBorder','GameModeText','PingText','PingLabel','MapLabel','PlayersText','MapNameText','MaxPlayersText'])
    def test_reset_writes_all_hover_targets_then_all_pressed_targets(self):
        policy.invoke(self.w,'reset');writes=[v for v in self.calls if len(v)>1 and v[1]=='SetScalarParameterValue'];targets=['ButtonBorder','GameModeText','PingText','PlayersText','MapNameText','MaxPlayersText'];self.assertEqual(writes,[(n,'SetScalarParameterValue',p,0.) for p in ('Hover_Animate','Pressed_Animate') for n in targets])
    def test_reset_stops_only_pressed_animation_first(self):policy.invoke(self.w,'reset');self.assertEqual(self.calls[0],('widget','StopAnimation','press'))
    def test_font_reset_uses_exact_native_font_material_and_two_parameters(self):
        policy.invoke(self.w,'font_reset',self.props['MapLabel']);self.assertEqual(self.calls,[('get','MapLabel','GetDynamicFontMaterial'),('MapLabel','SetScalarParameterValue','Hover_Animate',0.),('MapLabel','SetScalarParameterValue','Pressed_Animate',0.)])
    def test_image_uses_original_map_tile_art_parameter_and_forwards_null(self):
        policy.invoke(self.w,'image',None);self.assertEqual(self.calls[-1],('ButtonBorder','SetTextureParameterValue','MapTileArt',None))
    def test_construct_and_preconstruct_call_original_reset_function(self):
        for method in ('construct','pre'):
            self.calls=[];policy.invoke(self.w,method,False);self.assertEqual(self.calls,[('widget','ResetMaterials')])
    def test_disabled_pointer_and_selection_handlers_do_nothing(self):
        self.props['IsDisabled']=True
        for method in ('hover','unhover','select','deselect','click','finished'):policy.invoke(self.w,method)
        self.assertFalse(self.calls)
    def test_hover_animates_then_plays_original_native_sound(self):
        policy.invoke(self.w,'hover');self.assertEqual(self.calls[0],('widget','PlayAnimationForward','hover',1.,False));self.assertEqual(self.calls[1][0:2],('GameplayStatics','PlaySound2D'));self.assertEqual(self.calls[1][3],policy.SOUNDS['hover'])
    def test_selection_and_finished_keep_forward_reverse_arguments(self):
        policy.invoke(self.w,'select');policy.invoke(self.w,'finished');self.assertEqual(self.calls,[('widget','PlayAnimationForward','press',1.,False),('widget','PlayAnimationReverse','press',1.,False)])
    def test_click_only_starts_original_latent_adapter(self):policy.invoke(self.w,'click');self.assertEqual(self.calls,[('widget',policy.NATIVE_CLICK)])
    def test_disable_only_sets_border_disabled_then_resets(self):
        policy.invoke(self.w,'disable');self.assertEqual(self.calls,[('set','IsDisabled',True),('get','ButtonBorder','GetDynamicMaterial'),('ButtonBorder','SetScalarParameterValue','bIsDisabled',1.),('widget','ResetMaterials')])
    def test_enable_does_not_reset_fonts_or_animations(self):
        policy.invoke(self.w,'enable');self.assertEqual(self.calls,[('set','IsDisabled',False),('get','ButtonBorder','GetDynamicMaterial'),('ButtonBorder','SetScalarParameterValue','bIsDisabled',0.)])
    def test_profiles_define_all_routed_methods_but_not_five_text_setter(self):
        for profile in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraSessionButton'+profile+'Profile');self.assertEqual({fn.override for fn in vars(cls).values() if callable(fn)},set(policy.GATES.values()));self.assertNotIn('Set Texts',vars(cls))
