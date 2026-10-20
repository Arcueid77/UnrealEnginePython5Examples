"""Original CommonUI state guards, opaque FText and layout/action ordering."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.load_object=lambda c,p:p
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._foundation_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/foundation_buttons_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)


class FoundationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.selected=False;self.playing=False;self.gamepad=False;self.count=0;self.slot_valid=True;self.empty=object();self.data=dict(DefaultStyle='mouse',ControllerInputStyle='pad',ContentAlignment=3,PressProgress=.5,TextTransformPolicy=2,TextJustification=1,Hovered='hover-animation',Selected='select-animation',TabButtonPadding='padding',MinTabWidth=137,UseButtonStyle=True,ButtonStyle='tab-style',DebugTabCount=3,DebugButtonTypeDisplay='tab-class',PreviousTabInputActionData=object(),NextTabInputActionData=object());self.slot=types.SimpleNamespace(is_a=lambda c:self.slot_valid,call_function=lambda f,*a:self.calls.append(('slot',f,*a)))
        for n in ('Text','ButtonTextBlock','TabButtonBox','PreviousTabAction','NextTabAction','PreviousTabActionWrapper','NextTabActionWrapper','ContentBorder'):self.data[n]=self.obj(n)
        self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.data.__setitem__,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def obj(self,name):return types.SimpleNamespace(call_function=lambda f,*a:self.object_call(name,f,a))
    def object_call(self,name,f,a):
        self.calls.append((name,f,*a))
        if f in ('GetContentSlot','AddChildToHorizontalBox'):return self.slot
    def call(self,f,*a):
        if f=='GetSelected':return self.selected
        if f=='IsAnimationPlaying':return self.playing
        if f=='GetCurrentTextStyleClass':return 'native-text-style'
        if f=='GetTabCount':return self.count
        if f=='GetOwningPlayer':return 'player'
        self.calls.append(('widget',f,*a))
    def library(self,n,f,a):
        if f=='IsOwningPlayerUsingGamepad':return self.gamepad
        if f=='GetEmptyText':return self.empty
        if f=='Create':return types.SimpleNamespace(set_property=lambda *a:self.calls.append(('created',*a)))
        self.calls.append((n,f,*a))
    def test_input_combination_refreshes_style_before_text_style(self):
        policy.combined(self.w,1);self.assertEqual(self.calls,[('widget','UpdateStyle',True),('widget','UpdateTextStyle')])
    def test_touch_uses_mouse_branch_as_source_does(self):
        policy.combined(self.w,2);self.assertEqual(self.calls[0],('widget','UpdateStyle',False))
    def test_mouse_setter_uses_its_oddly_named_controller_parameter_for_default(self):
        policy.mouse(self.w,'new-mouse');self.assertEqual(self.data['DefaultStyle'],'new-mouse');self.assertEqual(self.data['ControllerInputStyle'],'pad')
    def test_missing_controller_style_falls_back_to_default(self):
        self.data['ControllerInputStyle']=None;policy.style(self.w,True);self.assertEqual(self.calls,[('widget','SetStyle','mouse')])
    def test_gamepad_uses_explicit_controller_style(self):
        policy.style(self.w,True);self.assertEqual(self.calls,[('widget','SetStyle','pad')])
    def test_alignment_setter_updates_property_then_slot(self):
        policy.align(self.w,1);self.assertEqual(self.data['ContentAlignment'],1);self.assertEqual(self.calls,[('widget','UpdateContentAlignment')]);self.calls=[];policy.alignupdate(self.w);self.assertEqual(self.calls[-1],('slot','SetHorizontalAlignment',1))
    def test_wrong_slot_type_has_no_alignment_write(self):
        self.slot_valid=False;policy.alignupdate(self.w);self.assertFalse(any(c[1]=='SetHorizontalAlignment' for c in self.calls))
    def test_progress_is_raw_and_not_clamped(self):
        policy.held(self.w,1.25);self.assertEqual(policy.progress(self.w),dict(UseOriginal=False,Progress=1.25))
    def test_text_forwarder_does_not_marshal_ftext_through_python(self):
        self.assertIs(policy.text(self.w),True);self.assertIs(policy.tabtext(self.w),True);self.assertFalse(self.calls)
    def test_preconstruct_empty_native_text_precedes_style_transform_and_justification(self):
        policy.pre(self.w);self.assertEqual(self.calls,[('widget','UpdateContentAlignment'),('Text','SetText',self.empty),('widget','UpdateTextStyle'),('Text','SetTextTransformPolicy',2),('Text','SetJustification',1)])
    def test_selected_hover_and_unhover_do_not_modify_animations_or_sound(self):
        self.selected=True;policy.hover(self.w);policy.unhover(self.w);self.assertFalse(self.calls)
    def test_hover_plays_forward_then_sound(self):
        policy.hover(self.w);self.assertEqual(self.calls[0],('widget','PlayAnimationForward','hover-animation',1.,False));self.assertEqual(self.calls[1][1],'PlaySound2D')
    def test_deselection_reverses_hover_stops_playing_selected_then_reverses(self):
        self.playing=True;policy.deselect(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationReverse','hover-animation',1.,False),('widget','StopAnimation','select-animation'),('widget','PlayAnimationReverse','select-animation',1.,False)])
    def test_nonplaying_selected_animation_is_not_artificially_stopped(self):
        policy.deselect(self.w);self.assertFalse(any(c[1]=='StopAnimation' for c in self.calls))
    def test_tab_layout_add_padding_dimensions_style_then_navigation_refresh(self):
        button=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('button',f,*a)));policy.tabstyle(self.w,button);self.assertEqual([c[1] for c in self.calls],['AddChildToHorizontalBox','SetPadding','SetMinDimensions','SetStyle','Refresh Next/Previous Visibility'])
    def test_navigation_hidden_preserves_layout_space(self):
        self.count=1;policy.refresh(self.w);self.assertEqual([c[-1] for c in self.calls],[2,2]);self.calls=[];self.count=2;policy.refresh(self.w);self.assertEqual([c[-1] for c in self.calls],[0,0])
    def test_preconstruct_binds_native_delegates_after_both_input_actions(self):
        policy.tabpre(self.w,False);self.assertEqual([c[1] for c in self.calls],['SetInputAction','SetInputAction',policy.BIND])
    def test_only_design_time_and_valid_class_enable_preview(self):
        policy.tabpre(self.w,True);self.assertEqual(self.calls[-1],('widget','DebugCreateTabsForDesigner'));self.calls=[];self.data['DebugButtonTypeDisplay']=None;policy.tabpre(self.w,True);self.assertFalse(any(c[1]=='DebugCreateTabsForDesigner' for c in self.calls))
    def test_designer_loop_is_one_through_count_and_does_not_register_tabs(self):
        policy.debug(self.w);self.assertEqual(sum(c[1]=='UpdateTabStyles' for c in self.calls),3);self.assertFalse(any(c[1]=='RegisterDynamicTab' for c in self.calls))
