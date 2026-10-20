"""Original brush reconstruction, guards and native animation dispatch contracts."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.load_object=lambda c,p:p
native.find_struct=lambda n:lambda **kw:types.SimpleNamespace(**dict(dict(ImageType=0,ResourceName='None',bIsDynamicallyLoaded=False),**kw))
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._bound_action_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/bound_action_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class BoundActionPolicyTests(unittest.TestCase):
    def setUp(self):
        policy.ue=native;self.calls=[];self.old=types.SimpleNamespace(**{n:object() for n in policy.BRUSH_FIELDS},ImageType=1,ResourceName='old',bIsDynamicallyLoaded=True);self.materials={n:types.SimpleNamespace(call_function=lambda f,*a,n=n:self.calls.append((n+'-material',f,*a))) for n in ('ButtonBorder','Text_ActionName')};self.data=dict(IsDisabled=False,OnPressed='pressed',OnHovered='hover')
        for n in self.materials:self.data[n]=types.SimpleNamespace(get_property=lambda p:self.old,call_function=lambda f,*a,n=n:self.object_call(n,f,a))
        self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.data.__setitem__,call_function=lambda f,*a:self.calls.append(('widget',f,*a)));policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.calls.append((n,f,*a)))
    def object_call(self,n,f,a):
        if f in ('GetDynamicMaterial','GetDynamicFontMaterial'):return self.materials[n]
        self.calls.append((n,f,*a))
    def test_only_gamepad_uses_no_draw_type(self):
        for value in (0,1,2,3):policy.style(self.w,value);self.assertEqual(self.calls[-1][2].DrawAs,0 if value==1 else 1)
    def test_brush_copies_only_original_pins_and_resets_omitted_fields(self):
        policy.style(self.w,0);new=self.calls[-1][2]
        for n in policy.BRUSH_FIELDS:self.assertIs(getattr(new,n),getattr(self.old,n))
        self.assertEqual(new.ImageType,0);self.assertEqual(new.ResourceName,'None');self.assertFalse(new.bIsDynamicallyLoaded)
    def test_reset_stops_press_before_resetting_both_materials(self):
        policy.reset(self.w);self.assertEqual(self.calls,[('widget','StopAnimation','pressed'),('ButtonBorder-material','SetScalarParameterValue','Hover_Animate',0.),('Text_ActionName-material','SetScalarParameterValue','Hover_Animate',0.),('ButtonBorder-material','SetScalarParameterValue','Pressed_Animate',0.),('Text_ActionName-material','SetScalarParameterValue','Pressed_Animate',0.)])
    def test_disable_sets_both_disabled_parameters_then_reset(self):
        policy.disable(self.w);self.assertTrue(self.data['IsDisabled']);self.assertEqual(self.calls[-1],('widget','ResetMaterials'));self.assertEqual([c[2] for c in self.calls[:-1]],['bIsDisabled','bIsDisabled'])
    def test_enable_keeps_press_and_hover_state(self):
        self.data['IsDisabled']=True;policy.enable(self.w);self.assertFalse(self.data['IsDisabled']);self.assertEqual([c[2] for c in self.calls],['bIsDisabled','bIsDisabled'])
    def test_disabled_animation_and_click_callbacks_are_noops(self):
        self.data['IsDisabled']=True
        for f in (policy.hover,policy.unhover,policy.select,policy.deselect,policy.click):f(self.w)
        self.assertFalse(self.calls)
    def test_hover_plays_forward_before_submenu_sound(self):
        policy.hover(self.w);self.assertEqual(self.calls[0],('widget','PlayAnimationForward','hover',1.,False));self.assertEqual(self.calls[1][1],'PlaySound2D');self.assertIn('SubMenu_Highlight',self.calls[1][3])
    def test_selection_and_deselection_do_not_play_click_sound(self):
        policy.select(self.w);policy.deselect(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationForward','pressed',1.,False),('widget','PlayAnimationReverse','pressed',1.,False)])
    def test_click_starts_only_existing_native_latent_node(self):
        policy.click(self.w);self.assertEqual(self.calls,[('widget',policy.NATIVE_CLICK)])
    def test_immediate_click_sound_uses_submenu_select(self):
        policy.clicksound(self.w);self.assertEqual(self.calls[0][1],'PlaySound2D');self.assertIn('SubMenu_Select',self.calls[0][3])
    def test_finished_resamples_current_disabled_flag(self):
        self.data['IsDisabled']=True;policy.finished(self.w);self.assertFalse(self.calls);self.data['IsDisabled']=False;policy.finished(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationReverse','pressed',1.,False)])
    def test_missing_font_material_does_not_block_border_reset(self):
        self.materials['Text_ActionName']=None;policy.reset(self.w);self.assertEqual(len(self.calls),3)
    def test_profiles_do_not_replace_native_construct_destruct_or_input_delegate(self):
        for cls in (policy.LyraBoundActionPythonProfile,policy.LyraBoundActionBlueprintFallbackProfile):
            names={v.override for v in vars(cls).values() if callable(v) and hasattr(v,'override')};self.assertEqual(names,set(policy.GATES.values()));self.assertFalse({'Construct','Destruct','Event Input Method Changed'}&names)
