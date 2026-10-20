"""Stable native-score sorting, pool reset, team filtering and ping boundaries."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.load_class=lambda n:n;native.find_struct=lambda n:lambda **kw:types.SimpleNamespace(**kw)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda *a:a[-1]
rows=types.ModuleType('uep_lyra_hud.scoreboard_rows_mixin');rows.INTERFACE='interface';rows.one=lambda v:v[0] if isinstance(v,tuple) and len(v)==1 else v;rows.color=lambda t,a:(t,a);rows.slate=lambda c:c;rows.text=lambda n:('native-text',n)
spec=importlib.util.spec_from_file_location('uep_lyra_hud._scoreboard_list_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/scoreboard_list_mixin.py');policy=importlib.util.module_from_spec(spec)
import uep_lyra_hud
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_hud.scoreboard_rows_mixin':rows}),patch.object(uep_lyra_hud,'scoreboard_rows_mixin',rows,create=True):spec.loader.exec_module(policy)


class ScoreboardListTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.scores={};self.team=1;self.part=True;self.fresh=[];self.entries=[];self.created=[];self.data={'TeamIdFilter':-1,'PlayerStates':[],'PlayerRowClass':object()};self.data['PlayerList']=types.SimpleNamespace(call_function=self.box);self.data['ConnectionStatus']=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('ping',f,*a)));self.gs=types.SimpleNamespace(get_property=lambda k:self.fresh);self.pc=types.SimpleNamespace(get_property=lambda k:object());self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=self.library)
    def player(self,name,score):
        p=types.SimpleNamespace(is_a=lambda c:True,call_function=lambda f,*a:score);self.scores[name]=p;return p
    def write(self,k,v):self.data[k]=v;self.calls.append(('write',k,list(v) if isinstance(v,list) else v))
    def call(self,f,*a):
        if f=='PassesFilter':return (a[0] is not None,)
        if f=='GetOwningPlayer':return self.pc
        if f==policy.FORMAT:return ('native-format',a[0])
        self.calls.append(('widget',f,*a))
    def box(self,f,*a):
        self.calls.append(('box',f,*a))
        if f=='GetAllEntries':return list(self.entries)
        if f=='BP_CreateEntryOfClass':
            entry=types.SimpleNamespace(call_function=lambda f,*a:self.created.append((f,*a)));return entry
    def library(self,f,*a):
        if f=='GetGameState':return self.gs
        if f=='GetWorldSubsystem':return types.SimpleNamespace(call_function=lambda f,*a:dict(bIsPartOfTeam=self.part,TeamId=self.team))
        if f=='DoesImplementInterface':return True
        if f=='Round':return int(a[0]+.5)
    def test_unfiltered_accepts_null_without_team_lookup(self):self.assertEqual(policy.passes(self.w,None),dict(UseOriginal=False,Passes=True))
    def test_filtered_requires_membership_and_matching_native_team(self):
        self.data['TeamIdFilter']=1;self.assertTrue(policy.passes(self.w,object())['Passes']);self.part=False;self.assertFalse(policy.passes(self.w,object())['Passes'])
    def test_construct_omits_native_timer_for_unfiltered(self):
        policy.construct(self.w);self.assertEqual(self.calls,[('widget','PollPlayerStates'),('widget','SortPlayerList')]);self.calls=[];self.data['TeamIdFilter']=2;policy.construct(self.w);self.assertEqual(self.calls[-1],('widget',policy.LIST_TIMER))
    def test_stable_descending_rank_and_pooled_reset(self):
        a,b,c=self.player('a',5),self.player('b',9),self.player('c',5);self.data['PlayerStates']=[a,b,c];policy.sort(self.w);self.assertIn(('box','Reset',False),self.calls);self.assertEqual([v[1] for v in self.created if v[0]=='SetPlayerState'],[b,a,c]);self.assertEqual([v[1] for v in self.created if v[0]=='SetRowColor'],[False,True,False])
    def test_poll_reverse_removal_and_native_roster_append(self):
        a,b=self.player('a',0),self.player('b',0);self.data['PlayerStates']=[None,a];self.entries=['entry0','entry1','orphan'];self.fresh=[a,b];policy.poll(self.w);self.assertEqual(self.data['PlayerStates'],[a,b]);self.assertIn(('box','RemoveEntry','orphan'),self.calls);self.assertIn(('box','RemoveEntry','entry0'),self.calls)
    def test_set_ping_player_colors_once_before_native_timer(self):
        ps=types.SimpleNamespace(call_function=lambda f:2);policy.set_player(self.w,ps);self.assertEqual(self.calls[-2:], [('ping','SetDefaultColorAndOpacity',(2,.4)),('widget',policy.PING_TIMER)])
    def test_periodic_ping_formats_native_rounded_text_without_recoloring(self):
        self.data['AssociatedPlayerState']=types.SimpleNamespace(call_function=lambda f:47.6);policy.ping(self.w);self.assertEqual(self.calls,[('ping','SetText',('native-format',('native-text',48)))])
    def test_null_periodic_association_preserves_previous_text(self):
        self.data['AssociatedPlayerState']=None;self.assertIs(policy.ping(self.w),False);self.assertFalse(self.calls)
