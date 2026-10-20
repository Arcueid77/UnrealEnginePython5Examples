"""Guard score boundaries, audio failure semantics and retained material state."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.FLinearColor=lambda *v:v;native.find_class=lambda n:n;native.load_class=lambda n:n;native.load_object=lambda c,p:p
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
rows=types.ModuleType('uep_lyra_hud.scoreboard_rows_mixin');rows.slate=lambda c:c;rows.text=lambda n:('native-text',n)
styles=types.ModuleType('uep_lyra_hud.scoreboard_style_mixin');styles.brush=lambda *a:None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._cp_widget_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/control_point_widgets_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_hud.scoreboard_rows_mixin':rows,'uep_lyra_hud.scoreboard_style_mixin':styles}):spec.loader.exec_module(policy)


class CPWidgetPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.data=dict(MyTeamID=1,EnemyTeamID=2,PreviousScoreLeft=0,PointOwnerTeamId=1,PreviousPointOwnerTeamId=1,OnPointOwnerChanged=object());self.scores={1:(1017,1000,True),2:(23,1000,False)};self.scoring=types.SimpleNamespace(call_function=lambda f,t:self.scores[t]);self.data['ControlPointMode']=self.scoring
        self.widget=types.SimpleNamespace(get_property=self.data.get,set_property=self.data.__setitem__,call_function=lambda f,*a:self.calls.append(('widget',f,*a)))
        for field in ('Goal','AllyScore','EnemyScore','PointLetter')+tuple(n+'MID' for n in policy.MATERIALS):self.data[field]=types.SimpleNamespace(call_function=lambda f,*a,field=field:self.calls.append((field,f,*a)))
        self.volume_data=dict(OwnerTeamID=1,OverlappingTeams=[]);self.volume=types.SimpleNamespace(get_property=self.volume_data.get);self.audio=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('audio',f,*a)));policy.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:self.audio)
    def test_score_uses_three_native_outputs_and_clamps_only_display(self):
        policy.score(self.widget);self.assertEqual(self.calls[:3],[('Goal','SetText',('native-text',1000)),('AllyScore','SetText',('native-text',1000)),('EnemyScore','SetText',('native-text',23))]);self.assertEqual(self.scores[1][0],1017)
    def test_invalid_scoring_does_not_write_text_or_fall_through(self):
        self.data['ControlPointMode']=None;self.assertIs(policy.score(self.widget),False);self.assertFalse(self.calls)
    def test_audio_minimum_uses_both_raw_scores_and_sets_native_int(self):
        self.scores={1:(996,1000,False),2:(999,1000,False)};policy.sound(self.widget,self.scoring);self.assertEqual(self.calls,[('audio','SetIntParameter','ScoreLeft',1)]);self.assertEqual(self.data['PreviousScoreLeft'],1)
    def test_unchanged_audio_score_does_not_spawn(self):
        self.scores={1:(995,1000,False),2:(0,1000,False)};self.data['PreviousScoreLeft']=5;policy.sound(self.widget,self.scoring);self.assertFalse(policy.evidence(self.widget)['audio'])
    def test_failed_spawn_preserves_previous_score_for_next_tick_retry(self):
        self.scores={1:(995,1000,False),2:(0,1000,False)};self.audio=None;policy.sound(self.widget,self.scoring);self.assertEqual(self.data['PreviousScoreLeft'],0)
    def test_out_of_audio_window_updates_previous_without_spawn(self):
        policy.sound(self.widget,self.scoring);self.assertEqual(self.data['PreviousScoreLeft'],-17);self.assertFalse(policy.evidence(self.widget)['audio'])
    def test_empty_point_updates_only_empty_scalar(self):
        policy.occupied(self.widget,self.volume);self.assertEqual(self.calls,[('RingMID','SetScalarParameterValue','IsEmptyPoint',1.),('RingGlowMID','SetScalarParameterValue','IsEmptyPoint',1.)])
    def test_contested_point_retains_last_team_color(self):
        self.volume_data['OverlappingTeams']=[1,2];policy.occupied(self.widget,self.volume);self.assertFalse(any(c[2]=='IsRedOrBlue' for c in self.calls));self.assertEqual(sum(c[2]=='IsContested' for c in self.calls),4)
    def test_enemy_single_occupier_flashes(self):
        self.volume_data['OverlappingTeams']=[2];policy.occupied(self.widget,self.volume);self.assertEqual([c[-1] for c in self.calls if c[2]=='IsFlashing'],[1.,1.])
    def test_unchanged_owner_does_not_restart_animation_or_touch_burst(self):
        policy.owner(self.widget,self.volume);self.assertFalse(self.calls)
    def test_owner_change_plays_original_animation_then_reads_volume_owner(self):
        self.data['PreviousPointOwnerTeamId']=2;policy.owner(self.widget,self.volume);self.assertEqual(self.calls[0],('widget','PlayAnimationForward',self.data['OnPointOwnerChanged'],1.,False));self.assertEqual(self.data['PreviousPointOwnerTeamId'],1)
    def test_negative_team_status_skips_points(self):
        self.data['MyTeamID']=-1;self.assertIs(policy.status(self.widget),False);self.assertFalse(self.calls)
    def test_status_preserves_array_indexes_and_reuses_c_for_later_entries(self):
        points=[types.SimpleNamespace(is_a=lambda c:True) for _ in range(4)];self.scoring.get_property=lambda f:points
        for letter in 'ABC':self.data['W_ControlPointMarker_'+letter]=types.SimpleNamespace(call_function=lambda f,v,letter=letter:self.calls.append((letter,f,v)))
        policy.status(self.widget);self.assertEqual([c[0] for c in self.calls],['A','B','C','C'])
