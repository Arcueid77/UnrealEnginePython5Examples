"""Native localized name bridge, exact alpha/style fields and activation branch."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.FLinearColor=lambda *v:v;native.find_class=lambda n:n;native.load_class=lambda n:n;native.load_object=lambda c,p:p
structs=types.ModuleType('unreal_engine.structs');structs.SlateBrush=lambda:types.SimpleNamespace()
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
rows=types.ModuleType('uep_lyra_hud.scoreboard_rows_mixin');rows.color=lambda t,a:(t,a);rows.slate=lambda c:c;rows.text=lambda n:('native-text',n);rows.one=lambda v:v[0] if isinstance(v,tuple) and len(v)==1 else v
import uep_lyra_hud
spec=importlib.util.spec_from_file_location('uep_lyra_hud._scoreboard_style_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/scoreboard_style_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_hud.scoreboard_rows_mixin':rows}),patch.object(uep_lyra_hud,'scoreboard_rows_mixin',rows,create=True):spec.loader.exec_module(policy)


class ScoreboardStyleTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.playing=False;self.localized=object();self.data={'TeamId':1,'IsTDMScoring':True,'OnActivated':object(),'StatId':object()};self.brush=types.SimpleNamespace(**{n:object() for n in policy.BRUSH_FIELDS});self.scoring=types.SimpleNamespace(call_function=lambda f,*a:(8,125,False));self.state=types.SimpleNamespace(get_component_by_type=lambda c:self.scoring)
        for n in ('TeamName','StatGoalText','TeamText','StatTextWidget','TeamIcon','BodyBorder','HeaderBorder','StatGlow','PlayerNameWidget','ElimCount','BeenEliminatedCount','AssistCount','ConnectionStatus'):self.data[n]=self.obj(n)
        self.w=types.SimpleNamespace(get_property=self.data.get,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=self.library)
    def obj(self,n):return types.SimpleNamespace(get_property=lambda f:self.brush,call_function=lambda f,*a:self.object_call(n,f,a))
    def object_call(self,n,f,a):
        self.calls.append((n,f,*a))
        if f=='GetDynamicMaterial':return self.obj(n+'-MID')
    def call(self,f,*a):
        if f==policy.NAME:return self.localized
        if f=='IsAnimationPlayingForward':return self.playing
        self.calls.append(('widget',f,*a))
    def library(self,f,*a):
        if f=='GetGameState':return self.state
        if f=='GetWorldSubsystem':return types.SimpleNamespace(call_function=lambda f,*a:77)
    def test_team_name_uses_opaque_native_literal_adapter(self):
        policy.style(self.w);self.assertIs(self.calls[0][-1],self.localized);self.assertEqual(self.calls[1:5],[('TeamName','SetColorAndOpacity',(1,.1)),('StatGoalText','SetColorAndOpacity',(1,.6)),('TeamText','SetColorAndOpacity',(1,.4)),('StatTextWidget','SetColorAndOpacity',(1,1.))])
    def test_brush_reconstruction_keeps_exact_authored_fields(self):
        target=self.obj('target');policy.brush(target,self.brush,'new-material');value=self.calls[-1][-1]
        for n in policy.BRUSH_FIELDS:self.assertIs(getattr(value,n),getattr(self.brush,n))
        self.assertEqual(value.ResourceObject,'new-material')
    def test_team_glow_uses_original_negative_rotation(self):
        policy.style(self.w);self.assertEqual(self.calls[-1],('TeamIcon-MID','SetScalarParameterValue','RotationSpeed',-2.))
    def test_header_applies_five_text_colors_then_border_resource(self):
        policy.header(self.w);self.assertEqual(len([c for c in self.calls if c[1]=='SetColorAndOpacity']),5);self.assertEqual(self.calls[-1][0:2],('HeaderBorder','SetBrush'))
    def test_periodic_update_does_not_refresh_target_or_style(self):
        policy.update(self.w);self.assertEqual(self.calls,[('StatTextWidget','SetText',('native-text',77))])
    def test_construct_target_uses_second_native_query_output(self):
        policy.goal(self.w);self.assertEqual(self.calls,[('StatGoalText','SetText',('native-text',125))])
    def test_forward_reactivation_stops_then_plays(self):
        self.playing=True;policy.activate(self.w);self.assertEqual(self.calls,[('widget','StopAnimation',self.data['OnActivated']),('widget','PlayAnimationForward',self.data['OnActivated'],1.,False)])
    def test_inactive_animation_does_not_invent_stop(self):
        policy.activate(self.w);self.assertEqual(self.calls,[('widget','PlayAnimationForward',self.data['OnActivated'],1.,False)])
    def test_invalid_team_preserves_original_diagnostics_before_side_effects(self):
        self.data['TeamId']=-1;self.assertIs(policy.style(self.w),True);self.assertFalse(self.calls)
