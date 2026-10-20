"""Root layer order, focus, native async selection and terminal argument fidelity."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.find_struct=lambda n:lambda **kw:types.SimpleNamespace(**kw)
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._menu_layers_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/menu_layers_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class MenuLayersPolicyTests(unittest.TestCase):
    def setUp(self):
        policy.ue=native;self.calls=[];self.parent_valid=True;self.parent=types.SimpleNamespace(is_a=lambda c:self.parent_valid,call_function=lambda f,*a:self.calls.append(('parent',f,*a)));self.sub=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('input',f,*a)));self.data=dict(OnActivated='intro',OptionsButtons=object(),**{n:object() for _,n in policy.LAYERS});self.w=types.SimpleNamespace(get_property=self.data.get,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def call(self,f,*a):
        if f=='GetOwningPlayer':return 'controller'
        self.calls.append(('widget',f,*a))
    def library(self,n,f,a):
        if f=='FindParentWidgetOfType':return self.parent
        if f=='GetLocalPlayerSubSystemFromPlayerController':return self.sub
        self.calls.append((n,f,*a))
    def test_layer_initialization_uses_original_four_tag_stack_pairs_in_order(self):
        policy.invoke(self.w,'layout','initialize');self.assertEqual([c[2].TagName for c in self.calls],['UI.Layer.Game','UI.Layer.GameMenu','UI.Layer.Menu','UI.Layer.Modal']);self.assertEqual([c[3] for c in self.calls],[self.data[n] for _,n in policy.LAYERS])
    def test_menu_focus_returns_exact_options_button(self):self.assertEqual(policy.invoke(self.w,'menu','focus'),dict(UseOriginal=False,ReturnValue=self.data['OptionsButtons']))
    def test_spinner_focus_returns_self_with_no_extra_action(self):self.assertEqual(policy.invoke(self.w,'spinner','focus'),dict(UseOriginal=False,ReturnValue=self.w));self.assertFalse(self.calls)
    def test_activation_retains_native_animation_arguments(self):
        policy.invoke(self.w,'menu','activate');self.assertEqual(self.calls,[('widget','PlayAnimationForward','intro',1.,False)])
    def test_settings_action_starts_only_native_push_alias(self):
        policy.invoke(self.w,'menu','settings');self.assertEqual(self.calls,[('widget',policy.PUSH)])
    def test_return_action_starts_native_localized_confirmation(self):
        policy.invoke(self.w,'menu','exit');self.assertEqual(self.calls,[('widget',policy.CONFIRM)])
    def test_only_confirmed_result_invokes_original_frontend_travel_alias(self):
        for value in (0,1,2,3,4):self.calls=[];policy.invoke(self.w,'menu','result',value);self.assertEqual(self.calls,[('widget',policy.TRAVEL)] if value==0 else [])
    def test_quit_resets_native_input_before_exact_quit_call(self):
        policy.invoke(self.w,'menu','quit');self.assertEqual(self.calls,[('input','SetCurrentInputType',0),('KismetSystemLibrary','QuitGame',self.w,None,0,False)])
    def test_touch_close_deactivates_actual_matching_parent(self):
        policy.invoke(self.w,'close','click');self.assertEqual(self.calls,[('parent','DeactivateWidget')])
    def test_unparented_touch_close_is_noop(self):
        self.parent=None;policy.invoke(self.w,'close','click');self.assertFalse(self.calls)
    def test_failed_parent_type_cast_is_noop(self):
        self.parent_valid=False;policy.invoke(self.w,'close','click');self.assertFalse(self.calls)
    def test_profiles_keep_exact_declared_routing_methods(self):
        for k,methods in policy.METHODS.items():
            for p in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraMenuLayer'+k.title()+p+'Profile');self.assertEqual({v.override for v in vars(cls).values() if callable(v) and hasattr(v,'override')},set(policy.GATES[k].values()))
