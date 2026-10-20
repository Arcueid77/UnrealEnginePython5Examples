"""Tab ordering, opaque native registration and exact native async branch routing."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.load_class=lambda p:p
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._settings_screens_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/settings_screens_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class SettingsScreensPolicyTests(unittest.TestCase):
    def setUp(self):
        policy.ue=native;self.calls=[];self.has=True;self.collection=object();self.material=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('material',f,*a)));self.panel_valid=True;self.panel=types.SimpleNamespace(is_a=lambda c:self.panel_valid,call_function=lambda f,*a:self.calls.append(('panel',f,*a)));self.data=dict(OnActivated='screen-intro',OnParentScreenActivated='panel-intro',Settings_Panel=self.panel,MID_Checkerboard=self.material,Checkerboard=types.SimpleNamespace(call_function=lambda f:self.material));self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.data.__setitem__,call_function=self.call)
    def call(self,f,*a):
        if f=='GetSettingCollection':self.calls.append(('lookup',*a));return self.collection,self.has
        self.calls.append(('widget',f,*a))
    def test_gamma_const_focus_returns_self_without_side_effects(self):
        self.assertEqual(policy.invoke(self.w,'gamma','focus'),dict(UseOriginal=False,ReturnValue=self.w));self.assertFalse(self.calls)
    def test_hdr_construct_caches_exact_native_material(self):
        policy.invoke(self.w,'hdr','construct');self.assertIs(self.data['MID_Checkerboard'],self.material)
    def test_hdr_luminance_is_raw_including_outside_normalized_range(self):
        for value in (-.25,0.,.1,1.,2.):self.calls=[];policy.invoke(self.w,'hdr','luminance',value);self.assertEqual(self.calls,[('material','SetScalarParameterValue','MaxLuminance',value)])
    def test_invalid_hdr_material_has_no_native_write(self):
        self.data['MID_Checkerboard']=None;policy.invoke(self.w,'hdr','luminance',1.);self.assertFalse(self.calls)
    def test_tab_registration_passes_opaque_collection_to_native_writer(self):
        policy.register(self.w,'AudioCollection');self.assertEqual(self.calls,[('lookup','AudioCollection'),('widget',policy.REGISTER_NATIVE,'AudioCollection',self.collection,False)])
    def test_empty_collection_tab_is_hidden(self):
        self.has=False;policy.register(self.w,'GamepadCollection');self.assertEqual(self.calls[-1][-1],True)
    def test_construct_uses_original_five_tab_order(self):
        policy.construct(self.w);self.assertEqual(self.calls,[('widget','RegisterTopLevelTab',n) for n in ('GameplayCollection','VideoCollection','AudioCollection','MouseAndKeyboardCollection','GamepadCollection')])
    def test_screen_animation_precedes_panel_cast_and_animation(self):
        policy.activate(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationForward','screen-intro',1.,False),('panel','OnSettingScreenAnim')])
    def test_failed_panel_cast_keeps_screen_animation(self):
        self.panel_valid=False;policy.activate(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationForward','screen-intro',1.,False)])
    def test_missing_panel_does_not_stop_screen_animation(self):
        self.data['Settings_Panel']=None;policy.activate(self.w);self.assertEqual(len(self.calls),1)
    def test_navigation_forwards_exact_name(self):
        policy.invoke(self.w,'screen','navigate','AudioCollection');self.assertEqual(self.calls,[('widget','NavigateToSetting','AudioCollection')])
    def test_each_tag_starts_original_async_alias_without_new_payload(self):
        for name,route in policy.ACTIONS.items():
            self.calls=[];policy.action(self.w,object(),types.SimpleNamespace(TagName=name));self.assertEqual(self.calls,[('widget',route)])
    def test_tag_name_comparison_retains_native_fname_case_insensitivity(self):
        policy.action(self.w,None,types.SimpleNamespace(TagName='GAMESETTINGS.ACTION.EDITBRIGHTNESS'));self.assertEqual(self.calls,[('widget','UEPSettingsScreenPushGamma')])
    def test_parent_or_unrecognized_tag_does_not_match_child_case(self):
        for name in ('GameSettings.Action','GameSettings.Action.EditBrightness.Child','None'):policy.action(self.w,None,types.SimpleNamespace(TagName=name))
        self.assertFalse(self.calls)
    def test_panel_animation_preserves_native_arguments(self):
        policy.invoke(self.w,'panel','animate');self.assertEqual(self.calls,[('widget','PlayAnimationForward','panel-intro',1.,False)])
    def test_profiles_only_register_declared_presentation_and_routing_methods(self):
        for k,methods in policy.METHODS.items():
            for p in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraSettingsScreen'+k.title()+p+'Profile');self.assertEqual({v.override for v in vars(cls).values() if callable(v) and hasattr(v,'override')},set(policy.GATES[k].values()))
