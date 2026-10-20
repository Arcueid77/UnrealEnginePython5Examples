"""Touch/focus, scalar pitch, pip thresholds and native text-array boundaries."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.load_object=lambda c,p:p;native.find_struct=lambda n:lambda **kw:types.SimpleNamespace(**dict(dict(ImageType=0),**kw))
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._settings_editors_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/settings_editors_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class SettingsEditorsPolicyTests(unittest.TestCase):
    def setUp(self):
        policy.ue=native;self.calls=[];self.touch=False;self.input_type=0;self.count=3;self.indices=[1,1,1];self.data=dict(OnHover='row-hover',OnHovered='background-hover');self.brush=types.SimpleNamespace(**{n:object() for n in policy.BRUSH_FIELDS},ImageType=1);self.material=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('material',f,*a)))
        for n in ('ProgressBar','OptionsScalingSizeBox','OptionsPips','EntryText','Diamond','EntryBorder','EnumOptions',*policy.FOCUS.values()):self.data[n]=types.SimpleNamespace(call_function=lambda f,*a,n=n:self.obj(n,f,a),get_property=lambda p:self.brush)
        self.w=types.SimpleNamespace(get_property=self.data.get,call_function=self.call);self.sub=types.SimpleNamespace(call_function=lambda f:self.input_type);self.setting=types.SimpleNamespace(is_a=lambda c:True,call_function=lambda f:self.indices.pop(0));policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def obj(self,n,f,a):
        if f in ('GetDynamicMaterial','GetDynamicFontMaterial'):return self.material
        self.calls.append((n,f,*a))
    def call(self,f,*a):
        if f=='GetOwningPlayer':return 'player'
        if f==policy.OPTION_COUNT:return self.count
        self.calls.append(('widget',f,*a))
    def library(self,n,f,a):
        if f=='IsOwningPlayerUsingTouch':return self.touch
        if f=='GetLocalPlayerSubSystemFromPlayerController':return self.sub
        self.calls.append((n,f,*a))
    def test_touch_skips_all_hover_animation_delegate_and_sound(self):
        self.touch=True;self.input_type=2
        for k in ('background','action','discrete','keyboard','missing','scalar','collection'):policy.hover(self.w,k,True);policy.hover(self.w,k,False)
        self.assertFalse(self.calls)
    def test_background_animation_precedes_exact_native_delegate_alias(self):
        policy.hover(self.w,'background',True);self.assertEqual(self.calls,[('widget','PlayAnimationForward','background-hover',1.,False),('widget',policy.BROADCAST['enter'])])
    def test_background_leave_preserves_reverse_then_false_delegate_path(self):
        policy.hover(self.w,'background',False);self.assertEqual(self.calls,[('widget','PlayAnimationReverse','background-hover',1.,False),('widget',policy.BROADCAST['leave'])])
    def test_action_and_keyboard_use_actual_input_enum_query(self):
        self.touch=True;self.input_type=0;policy.hover(self.w,'action',True);self.assertEqual(self.calls,[('widget','PlayAnimationForward','row-hover',1.,False)])
    def test_other_rows_use_commonui_touch_query(self):
        self.touch=True;self.input_type=0;policy.hover(self.w,'missing',True);self.assertFalse(self.calls)
    def test_focus_returns_exact_child_in_typed_output(self):
        for k,n in policy.FOCUS.items():self.assertEqual(policy.focus(self.w,k),dict(UseOriginal=False,ReturnValue=self.data[n]))
    def test_scalar_progress_is_raw_while_only_pitch_is_clamped(self):
        for value,pitch in ((-.25,.9),(0.,.9),(.5,1.),(1.,1.1),(1.25,1.1)):
            self.calls=[];policy.scalar(self.w,'scalar',value,False);self.assertEqual(self.calls[0],('material','SetScalarParameterValue','Progress',value));self.assertAlmostEqual(self.calls[1][5],pitch)
    def test_default_value_has_no_sound(self):
        policy.scalar(self.w,'scalar',1.25,True);self.assertEqual(self.calls,[('material','SetScalarParameterValue','DefaultValue',1.25)])
    def test_scalar_hover_uses_submenu_sound_after_animation(self):
        policy.hover(self.w,'scalar',True);self.assertEqual(self.calls[0][1],'PlayAnimationForward');self.assertIn('SubMenu_Highlight',self.calls[1][3])
    def test_other_row_hover_does_not_add_sound(self):
        policy.hover(self.w,'discrete',True);self.assertEqual(len(self.calls),1)
    def test_rotator_thresholds_are_strict_and_count_stays_local(self):
        for count,index,width in ((-1,0,192.),(3,0,192.),(4,1,256.),(5,1,256.),(6,2,320.),(7,2,320.),(8,3,384.)):
            self.calls=[];policy.pips_style(self.w,'rotator',count);self.assertEqual(self.calls[0],('OptionsScalingSizeBox','SetWidthOverride',width));self.assertEqual(self.calls[1][2].ResourceObject,policy.PIP_MATERIALS[index]);self.assertEqual(self.calls[-1],('material','SetScalarParameterValue','Options',float(count)));self.assertNotIn('Count',self.data)
    def test_rotator_rebuild_copies_only_source_brush_pins(self):
        policy.pips_style(self.w,'rotator',4);new=self.calls[1][2]
        for n in policy.BRUSH_FIELDS:self.assertIs(getattr(new,n),getattr(self.brush,n))
        self.assertEqual(new.ImageType,0)
    def test_rotator_selection_and_default_are_not_clamped(self):
        policy.pips_index(self.w,'rotator',-1,False);policy.pips_index(self.w,'rotator',99,True);self.assertEqual(self.calls,[('material','SetScalarParameterValue','SelectedOption',-1.),('material','SetScalarParameterValue','DefaultOption',99.)])
    def test_details_updates_all_three_materials(self):
        policy.detail(self.w,'details',True);self.assertEqual(self.calls,[('material','SetScalarParameterValue','Hover_Animate',1.)]*3)
    def test_invalid_setting_resets_pool_without_deleting_widgets(self):
        policy.rebuild(self.w,'extension',None);self.assertEqual(self.calls,[('EnumOptions','Reset',False)])
    def test_wrong_setting_type_still_resets_pool(self):
        self.setting.is_a=lambda c:False;policy.rebuild(self.w,'extension',self.setting);self.assertEqual(self.calls,[('EnumOptions','Reset',False)])
    def test_rebuild_does_not_read_or_marshal_option_text_into_python(self):
        policy.rebuild(self.w,'extension',self.setting);self.assertEqual(self.calls,[('EnumOptions','Reset',False),('widget',policy.OPTION_CREATE,self.setting,0,False),('widget',policy.OPTION_CREATE,self.setting,1,True),('widget',policy.OPTION_CREATE,self.setting,2,False)])
    def test_selected_index_is_resampled_for_each_native_option(self):
        self.indices=[0,1,2];policy.rebuild(self.w,'extension',self.setting);self.assertTrue(all(c[-1] is True for c in self.calls[1:]))
    def test_profiles_keep_text_assignment_and_model_setters_out_of_python_routes(self):
        for k,methods in policy.METHODS.items():
            for p in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraSettingsEditor'+k.title()+p+'Profile');names={v.override for v in vars(cls).values() if callable(v) and hasattr(v,'override')};self.assertEqual(names,set(policy.GATES[k].values()));self.assertNotIn('OnSettingAssigned',names)
