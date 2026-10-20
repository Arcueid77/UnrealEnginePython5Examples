"""Polling/string boundary, content replacement, brush identity and sizing rules."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.load_class=lambda p:p
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._foundation_widgets_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/foundation_widgets_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class FoundationWidgetsPolicyTests(unittest.TestCase):
    def setUp(self):
        policy.ue=native;self.calls=[];self.created=[];self.value='加载{Reason}...';self.brush=object();self.size=object();self.data=dict(OnActivated='intro',DisplayBrush=self.brush,Size=self.size);self.manager=types.SimpleNamespace(call_function=lambda f:self.value)
        for n in ('Background','BlurredBackground','Spinner','ExperienceSpecificWidgetSlot'):self.data[n]=types.SimpleNamespace(call_function=lambda f,*a,n=n:self.calls.append((n,f,*a)))
        self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.set_property,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def set_property(self,n,v):self.calls.append(('set',n,v));self.data[n]=v
    def call(self,f,*a):
        if f=='GetOwningPlayer':return 'player'
        self.calls.append(('widget',f,*a))
    def library(self,n,f,a):
        if f=='GetGameInstanceSubsystem':self.calls.append(('subsystem',a[1]));return self.manager
        if f=='Create':
            value=object();self.created.append(value);self.calls.append(('create',*a));return value
        raise AssertionError((n,f,a))
    def test_dialog_activation_preserves_native_forward_animation_arguments(self):
        policy.dialog(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationForward','intro',1.,False)])
    def test_reason_polls_native_subsystem_and_forwards_string_without_formatting(self):
        policy.reason(self.w);self.assertEqual(self.calls,[('subsystem','LoadingScreenManager'),('widget',policy.NATIVE_REASON,self.value)])
    def test_reason_repolls_each_callback_instead_of_caching(self):
        policy.reason(self.w);self.value='changed';policy.reason(self.w);self.assertEqual(self.calls[-1],('widget',policy.NATIVE_REASON,'changed'))
    def test_loading_stores_requested_class_before_default_fallback(self):
        policy.loading(self.w,None);self.assertEqual(self.calls[:2],[('set','ContentWidgetClass',None),('set','ContentWidgetClass',policy.DEFAULT_CONTENT)]);self.assertEqual(self.calls[2],('create',self.w,policy.DEFAULT_CONTENT,'player'))
    def test_valid_loading_class_does_not_load_fallback(self):
        cls=object();policy.loading(self.w,cls);self.assertIs(self.data['ContentWidgetClass'],cls);self.assertEqual(len([c for c in self.calls if c[0]=='set']),1)
    def test_same_class_callback_always_creates_new_content(self):
        policy.loading(self.w,'class');policy.loading(self.w,'class');self.assertEqual(len(self.created),2);self.assertIsNot(self.created[0],self.created[1]);self.assertEqual(self.calls[-1],('ExperienceSpecificWidgetSlot','SetContent',self.created[-1]))
    def test_loading_does_not_add_new_delegate_lifetime_policy(self):
        policy.loading(self.w,'class');self.assertFalse(any('Delegate' in str(c) or 'Destruct' in str(c) for c in self.calls))
    def test_aspect_copies_entire_opaque_brush_to_both_images(self):
        policy.aspect(self.w);self.assertEqual(self.calls,[('Background','SetBrush',self.brush),('BlurredBackground','SetBrush',self.brush)])
    def test_spinner_preserves_opaque_size_without_clamp_or_conversion(self):
        policy.spinner(self.w);self.assertEqual(self.calls,[('Spinner','SetDesiredSizeOverride',self.size)])
    def test_spinner_uses_same_policy_in_design_and_runtime(self):
        fn=policy.ignore_design(policy.spinner);fn(self.w,True);fn(self.w,False);self.assertEqual(self.calls,[('Spinner','SetDesiredSizeOverride',self.size)]*2)
    def test_each_profile_exposes_one_typed_policy_only(self):
        for label in policy.CLASSES:
            for name in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraFoundationWidget'+label.title()+name+'Profile');values=[v.override for v in vars(cls).values() if callable(v) and hasattr(v,'override')];self.assertEqual(values,[policy.GATES[label]])
