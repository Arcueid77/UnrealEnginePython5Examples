"""Guard raw progress ratios, clock retry semantics and native backend arguments."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.FLinearColor=lambda *v:v;native.find_class=lambda n:n;native.load_object=lambda c,p:p
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
rows=types.ModuleType('uep_lyra_hud.scoreboard_rows_mixin');rows.slate=lambda c:c
styles=types.ModuleType('uep_lyra_hud.scoreboard_style_mixin');styles.brush=lambda *a:None
cp=types.ModuleType('uep_lyra_hud.control_point_widgets_mixin');cp.style_resource=lambda k,t:(k,t)
spec=importlib.util.spec_from_file_location('uep_lyra_hud._tdm_hud_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/elimination_score_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_hud.scoreboard_rows_mixin':rows,'uep_lyra_hud.scoreboard_style_mixin':styles,'uep_lyra_hud.control_point_widgets_mixin':cp}):spec.loader.exec_module(policy)


class TDMHudPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.data=dict(MyTeamID=1,EnemyTeamID=2,PreviousTime=10,PreviousScoreLeft=0);self.scores={1:(12,8,False),2:(20,8,False)};self.scoring=types.SimpleNamespace(call_function=lambda f,t:self.scores[t]);self.data['TDMScoring']=self.scoring;self.opaque=object();self.clock=(self.opaque,9);self.audio=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('audio',f,*a)));policy.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:self.audio)
        self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.set_property,call_function=self.call)
        for n in ('Clock','AllyScore','AllyGoal','EnemyScore','EnemyGoal','AllyProgressBar','AllyProgressBarGlow','EnemyProgressBar','EnemyProgressBarGlow'):self.data[n]=self.obj(n)
    def obj(self,name):
        return types.SimpleNamespace(call_function=lambda f,*a:self.obj(name+'MID') if f=='GetDynamicMaterial' else self.calls.append((name,f,*a)))
    def call(self,f,*a):
        if f==policy.CLOCK:self.calls.append(('formatter',f,*a));return self.clock
        self.calls.append(('widget',f,*a))
    def set_property(self,key,value):
        if key not in self.data:raise AssertionError('Original function locals cannot become widget properties: '+key)
        self.data[key]=value
    def test_progress_is_not_clamped_and_both_materials_receive_raw_ratio(self):
        policy.team_score(self.w,self.scoring,False);self.assertNotIn('PctToTargetScore',self.data);self.assertEqual([c[-1] for c in self.calls if c[1]=='SetScalarParameterValue'],[1.5,1.5])
    def test_zero_target_preserves_score_value_and_zeroes_only_ratio(self):
        self.scores[1]=(17,0,False);policy.team_score(self.w,self.scoring,False);self.assertEqual([c[-1] for c in self.calls if c[1]=='SetScalarParameterValue'],[0.,0.]);self.assertIn(('AllyScore','SetCurrentValue',17.),self.calls)
    def test_each_call_uses_a_fresh_local_ratio(self):
        policy.team_score(self.w,self.scoring,False);policy.team_score(self.w,self.scoring,True);self.assertNotIn('PctToTargetScore',self.data);self.assertEqual([c[-1] for c in self.calls if c[1]=='SetScalarParameterValue'],[1.5,1.5,2.5,2.5])
    def test_clock_uses_opaque_native_formatted_text_and_floor(self):
        policy.clock(self.w,9.99);self.assertIs(self.calls[1][-1],self.opaque);self.assertEqual(self.data['PreviousTime'],9);self.assertNotIn('CurrentTime',self.data);self.assertEqual(self.calls[0],('formatter',policy.CLOCK,9.99))
    def test_unchanged_floor_does_not_spawn(self):
        self.data['PreviousTime']=9;policy.clock(self.w,9.1);self.assertEqual(policy.evidence(self.w)['clock_audio_spawns'],0)
    def test_previous_nonpositive_suppresses_sound_even_for_positive_current(self):
        self.data['PreviousTime']=0;policy.clock(self.w,9.1);self.assertEqual(self.data['PreviousTime'],9);self.assertEqual(policy.evidence(self.w)['clock_audio_spawns'],0)
    def test_failed_clock_spawn_keeps_previous_for_retry(self):
        self.audio=None;policy.clock(self.w,9.1);self.assertEqual(self.data['PreviousTime'],10);self.assertNotIn('CurrentTime',self.data)
    def test_zero_second_can_sound_when_previous_was_positive(self):
        self.clock=(self.opaque,0);policy.clock(self.w,0.);self.assertIn(('audio','SetIntParameter','SecondsLeft',0),self.calls)
    def test_above_threshold_updates_previous_without_sound(self):
        self.clock=(self.opaque,11);policy.clock(self.w,11.);self.assertEqual(self.data['PreviousTime'],11);self.assertEqual(policy.evidence(self.w)['clock_audio_spawns'],0)
    def test_negative_team_does_not_read_scoring_or_fall_back(self):
        self.data['MyTeamID']=-1;self.assertIs(policy.score(self.w),False);self.assertFalse(self.calls)
    def test_team_callback_styles_then_sides_without_added_score_refresh(self):
        policy.team(self.w,2);self.assertEqual(self.calls,[('widget','UpdateTeamStyles'),('widget','UpdateStyleSides')]);self.assertEqual(self.data['EnemyTeamID'],1)
    def test_score_sound_uses_minimum_raw_remainder(self):
        self.scores={1:(999,1000,False),2:(996,1000,False)};policy.sound(self.w,self.scoring);self.assertEqual(self.data['PreviousScoreLeft'],1);self.assertEqual(self.calls,[('audio','SetIntParameter','ScoreLeft',1)])
    def test_failed_score_spawn_retains_previous(self):
        self.scores={1:(999,1000,False),2:(996,1000,False)};self.audio=None;policy.sound(self.w,self.scoring);self.assertEqual(self.data['PreviousScoreLeft'],0)
