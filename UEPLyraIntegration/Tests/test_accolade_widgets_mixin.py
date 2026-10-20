"""Typed existing-widget return, opaque text, source sequence and native play."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
enums=types.ModuleType('unreal_engine.enums');enums.ESlateVisibility=types.SimpleNamespace(Collapsed=1,HitTestInvisible=3)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
spec=importlib.util.spec_from_file_location('_accolade_widgets_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/accolade_widgets_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine.enums':enums,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)


class OpaqueText:
    def __str__(self):raise AssertionError('localized text must not be stringified')


class AccoladePresentationTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.text=OpaqueText();self.sound=object();self.icon=object();self.animation=object();self.children={n:self.obj(n) for n in ('TextWidget','IconWidget')};self.children['IntroOutro']=self.animation;self.toast=self.obj('toast',self.children);self.host=self.obj('host',{'MyToast':self.toast});self.entry=types.SimpleNamespace(Row=types.SimpleNamespace(DisplayName=self.text),Sound=self.sound,Icon=self.icon);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda fn,**kw:self.calls.append(('sound',fn,kw)))
    def obj(self,name,props=None):return types.SimpleNamespace(get_property=lambda key:(props or {}).get(key),call_function=lambda fn,*args:self.calls.append((name,fn,*args)))
    def test_create_returns_existing_toast_and_preserves_localized_text_object(self):
        r=policy.create(self.host,self.entry);self.assertEqual(r,dict(UseOriginal=False,Widget=self.toast));self.assertIs(self.calls[2][-1],self.text)
    def test_sequence_is_show_sound_text_icon_native_play(self):
        policy.create(self.host,self.entry);self.assertEqual([x[:2] for x in self.calls],[('toast','SetVisibility'),('sound','PlaySound2D'),('TextWidget','SetText'),('IconWidget','SetBrushResourceObject'),('toast','PlayIntroOutro')]);self.assertEqual(self.calls[0][-1],3)
    def test_valid_sound_uses_original_ui_parameters(self):
        policy.create(self.host,self.entry);self.assertEqual(self.calls[1][2],dict(WorldContextObject=self.host,Sound=self.sound,VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,ConcurrencySettings=None,OwningActor=None,bIsUISound=True))
    def test_null_sound_skips_audio_and_null_icon_still_clears_brush(self):
        self.entry.Sound=self.entry.Icon=None;policy.create(self.host,self.entry);self.assertFalse(any(x[0]=='sound' for x in self.calls));self.assertEqual(self.calls[-2],('IconWidget','SetBrushResourceObject',None))
    def test_missing_toast_falls_back_before_partial_side_effects(self):
        host=self.obj('bad-host',{'MyToast':None});self.assertEqual(policy.create(host,self.entry),dict(UseOriginal=True,Widget=None));self.assertFalse(self.calls)
    def test_missing_control_falls_back_before_visibility_or_sound(self):
        self.children['TextWidget']=None;self.assertEqual(policy.create(self.host,self.entry)['UseOriginal'],True);self.assertFalse(self.calls)
    def test_construct_and_destroy_only_collapse_owned_toast(self):
        self.assertIs(policy.hide(self.host,'construct'),False);self.assertEqual(self.calls,[('toast','SetVisibility',1)]);self.calls=[];policy.LyraAccoladeHostPythonProfile.Destroy(self.host,object());self.assertEqual(self.calls,[('toast','SetVisibility',1)])
    def test_toast_play_does_not_connect_dead_stop_or_rewind_business(self):
        self.assertIs(policy.play(self.toast),False);self.assertEqual(self.calls,[('toast','PlayAnimationForward',self.animation,1.,False)])
    def test_missing_animation_returns_to_original_diagnostics(self):
        self.children['IntroOutro']=None;self.assertIs(policy.play(self.toast),True);self.assertFalse(self.calls)
    def test_fallback_typed_gate_keeps_original_function_return_path(self):
        self.assertEqual(policy.LyraAccoladeHostBlueprintFallbackProfile.Create(self.host,self.entry),dict(UseOriginal=True,Widget=None));self.assertFalse(self.calls)
