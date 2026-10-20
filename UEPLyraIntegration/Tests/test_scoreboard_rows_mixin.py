"""Interface fan-out, source fixed colors, native text and timer boundaries."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.FLinearColor=lambda *a:a;native.load_class=lambda p:p
structs=types.ModuleType('unreal_engine.structs');structs.SlateColor=lambda **kw:types.SimpleNamespace(**kw)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
spec=importlib.util.spec_from_file_location('_scoreboard_rows_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/scoreboard_rows_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)


class ScoreboardRowsTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.value=0;self.team=1;self.implements=True;self.ps=types.SimpleNamespace(call_function=self.player);self.child=self.obj('child');self.pc=types.SimpleNamespace(get_property=lambda k:self.ps)
        self.data={'AssociatedPlayerState':self.ps,'Stat Tag':object(),'TeamId':1,'StatWidth':100.}
        for n in ('PlayerNameWidget','StatTextWidget','ForcedWidthSB','PlayerName','EntryBorder','MyHorizontalBox'):self.data[n]=self.obj(n)
        self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda fn,*a:self.backend(fn,a))
    def obj(self,name):return types.SimpleNamespace(call_function=lambda fn,*a:self.object_call(name,fn,a))
    def object_call(self,n,fn,args):
        self.calls.append((n,fn,*args))
        if fn=='GetAllChildren':return [self.child]
    def player(self,fn,*a):return self.team if fn=='GetTeamId' else 'Player-甲' if fn=='GetPlayerName' else self.value
    def write(self,k,v):self.data[k]=v;self.calls.append(('write',k,v))
    def call(self,fn,*a):
        if fn=='GetPlayerStateAwareChildren':return ([self.child,None],)
        if fn=='GetOwningPlayer':return self.pc
        self.calls.append(('widget',fn,*a))
    def backend(self,fn,args):
        if fn=='DoesImplementInterface':return self.implements
        if fn in ('Conv_StringToText','Conv_IntToText'):return ('native-text',args[0])
    def test_base_stores_then_forwards_interface_children(self):
        policy.base(self.w,self.ps);self.assertEqual(self.calls,[('write','AssociatedPlayerState',self.ps),('child','SetPlayerState',self.ps)])
    def test_nonimplementing_children_keep_message_noop(self):
        self.implements=False;policy.base(self.w,self.ps);self.assertEqual(len(self.calls),1)
    def test_name_uses_native_name_to_text_and_fixed_team_color(self):
        policy.name(self.w,self.ps);self.assertEqual(self.calls[1],('PlayerNameWidget','SetText',('native-text','Player-甲')));self.assertEqual(self.calls[-1][-1].SpecifiedColor,(1.,.539480,.318547,1.))
    def test_local_name_is_white_without_changing_associated_player(self):
        policy.local(self.w);self.assertEqual(self.calls[-1][-1].SpecifiedColor,(1,1,1,1));self.assertIs(self.data['AssociatedPlayerState'],self.ps)
    def test_icon_only_assigns_original_player_field(self):
        policy.icon(self.w,self.ps);self.assertEqual(self.calls,[('write','Player State',self.ps)])
    def test_stat_setter_reuses_original_timer_entry(self):
        policy.stat(self.w,None);self.assertEqual(self.calls,[('write','AssociatedPlayerState',None),('widget',policy.TIMER)])
    def test_invalid_stat_association_does_not_clear_old_text(self):
        self.data['AssociatedPlayerState']=None;self.assertIs(policy.update(self.w),False);self.assertFalse(self.calls)
    def test_zero_stat_team_tint_and_nonzero_white(self):
        policy.update(self.w);self.assertEqual(self.calls[-1][-1].SpecifiedColor,(1.,.539480,.318547,.4));self.value=1234;policy.update(self.w);self.assertEqual(self.calls[-1][-1].SpecifiedColor,(1.,1.,1.,1.))
    def test_construct_applies_nonpositive_width_but_preconstruct_retains_old_width(self):
        self.data['StatWidth']=-12.;policy.width(self.w,True);self.assertFalse(self.calls);policy.width(self.w,False);self.assertEqual(self.calls,[('ForcedWidthSB','SetWidthOverride',-12.)])
    def test_row_sets_team_then_marks_local_name(self):
        policy.row(self.w);self.assertEqual(self.calls,[('write','TeamId',1),('PlayerName','SetAsLocalPlayer')])
    def test_row_background_uses_original_odd_even_literals(self):
        policy.row_color(self.w,True);self.assertEqual(self.calls[-1],('EntryBorder','SetBrushColor',(.107023,.014444,.011612,.3)))
    def test_children_return_retains_typed_array_named_output(self):
        r=policy.children(self.w);self.assertEqual(r,dict(UseOriginal=False,Children=[self.child]))
    def test_derived_profiles_explicitly_include_base_gate(self):
        self.assertIs(policy.LyraScoreboardModePythonProfile.Base,policy.LyraScoreboardBasePythonProfile.Base);self.assertEqual(len([f for n,f in vars(policy.LyraScoreboardModePythonProfile).items() if callable(f) and not n.startswith('_')]),5)
