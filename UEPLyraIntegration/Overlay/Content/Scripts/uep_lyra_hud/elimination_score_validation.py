"""Real mounted TDM HUD, native score/countdown delegates and source differentials."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons import tdm_scoring_mixin as scoring_policy
from .message_widget_validation import model
from .scoreboard_style_mixin import BRUSH_FIELDS
from . import elimination_score_mixin as policy
from .elimination_score_contract import PROFILES,FALSE_FIELDS,require,validate

TAG='ShooterGame.Score.Eliminations'
BRUSHES=('AllyScoreGlow','EnemyScoreGlow','AllyLogo','EnemyLogo','AllyProgressBar','EnemyProgressBar','AllyProgressBarGlow','EnemyProgressBarGlow')


def count(w,key):return sum(policy.evidence(w)[p+'_'+key] for p in ('python','fallback'))
def text(w):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',w.call_function('GetText'))
def rgba(c):return [round(float(getattr(c,n)),5) for n in ('r','g','b','a')]


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],direct_policy_fixture_calls_used=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.states=[];self.observed_clocks={};self.index=0
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);self.cdo_profile=self.cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(self.cls);registry,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];self.sources={p:r['python_class'] for p,r in registry['profiles'].items()}
        for profile,base in self.sources.items():
            def around(fn):
                def invoke(w,Time):
                    if self.phase in ('native-tick','removed'):self.observed_clocks.setdefault(w,[]).append((self.game_time(),float(Time)))
                    return fn(w,Time)
                invoke.override=policy.GATES['clock'];return invoke
            methods={n:getattr(base,n) for n in ('Ally','Enemy','Style','Sides','Clock','Sound','Score','Team')};methods['Clock']=around(base.Clock);ue.register_mixin_profile(self.cls,profile,type('ObservedTDMHud'+profile,(),methods))
        self.scoring=self.statics.call_function('GetGameState',self.world).get_component_by_type(ue.load_class(scoring_policy.CLASS));require(policy.valid(self.scoring),'actual TDM scoring component missing');self.target=int(self.scoring.get_property('TargetScore'));self.countdown=float(self.scoring.get_property('CountDownTime'));self.team=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'));self.tag_before={i:self.get_tag(i) for i in (1,2)};self.start_profile()
    def get_tag(self,team):return int(self.team.call_function('GetTeamTagStackCount',team,GameplayTag(TagName=TAG)))
    def set_tag(self,team,value):
        current=self.get_tag(team)
        if current:self.team.call_function('RemoveTeamTagStack',team,GameplayTag(TagName=TAG),current)
        if value:self.team.call_function('AddTeamTagStack',team,GameplayTag(TagName=TAG),value)
    def start_profile(self):
        self.profile=PROFILES[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.scoring.set_property('TargetScore',1000);self.set_tag(1,11);self.set_tag(2,19);self.w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);self.w.add_to_root();self.widgets.append(self.w);ue.set_mixin_profile(self.w,self.profile);self.w.call_function('AddToPlayerScreen',0);self.frames=0;self.row=dict(profile=self.profile,style_cases=0,score_cases=0,clock_cases=0,score_sound_cases=0);self.report['pending_profile']=self.row;self.enter('bind')
    def canonical_brush(self,field):
        b=self.w.get_property(field).get_property('Brush');return {n:model(getattr(b,n)) for n in BRUSH_FIELDS+('ResourceObject',)}
    def seed_brush(self,field):
        image=self.w.get_property(field);b=image.get_property('Brush');size=b.ImageSize;size.X=137.;size.Y=43.;b.ImageSize=size;b.Tiling=1;b.Mirroring=2;b.Margin=ue.find_struct('Margin')(Left=.1,Top=.2,Right=.3,Bottom=.4);image.call_function('SetBrush',b)
    def style_cases(self):
        states=[]
        for team in (0,1,2):
            self.w.set_property('MyTeamID',team);self.w.set_property('EnemyTeamID',{0:0,1:2,2:1}[team])
            for field in BRUSHES:self.seed_brush(field)
            self.w.call_function('UpdateTeamStyles');self.w.call_function('UpdateStyleSides');states.append(dict(brushes={n:self.canonical_brush(n) for n in BRUSHES},tints={n:rgba(self.w.get_property(n).get_property('ColorAndOpacity').SpecifiedColor) for n in ('AllyScore','EnemyScore','AllyGoal','EnemyGoal')},inverse=float(self.w.get_property('ScoreBorder').call_function('GetDynamicMaterial').call_function('K2_GetScalarParameterValue','InverseGradient'))));self.row['style_cases']+=1
        self.w.set_property('MyTeamID',1);self.w.set_property('EnemyTeamID',2);self.w.call_function('UpdateTeamStyles');self.w.call_function('UpdateStyleSides');return states
    def numeric_state(self):return dict(numbers={n:dict(value=float(self.w.get_property(n).call_function('GetTargetValue')),text=text(self.w.get_property(n))) for n in ('AllyScore','AllyGoal','EnemyScore','EnemyGoal')},arcs={n:float(self.w.get_property(n).call_function('GetDynamicMaterial').call_function('K2_GetScalarParameterValue','AnimateArcFill')) for n in ('AllyProgressBar','AllyProgressBarGlow','EnemyProgressBar','EnemyProgressBarGlow')})
    def score_cases(self):
        states=[]
        for a,b,target in ((11,19,1000),(17,23,0),(12,20,8),(16777217,23,100000)):
            self.scoring.set_property('TargetScore',target);self.set_tag(1,a);self.set_tag(2,b);self.w.call_function('UpdateAllyTeamScore',self.scoring);self.w.call_function('Update Enemy Team Score',self.scoring);states.append(self.numeric_state());self.row['score_cases']+=1
        self.scoring.set_property('TargetScore',1000);return states
    def audio_objects(self,path):return {a for a in self.world.all_objects() if policy.valid(a) and a.is_a(ue.find_class('AudioComponent')) and a.get_property('Sound') is not None and a.get_property('Sound').get_path_name()==path}
    def audio_call(self,path,fn):
        before=self.audio_objects(path);fn();new=self.audio_objects(path)-before;rows=[{str(p.ParamName):int(p.IntParam) for p in a.get_property('InstanceParameters')} for a in new]
        for a in new:a.call_function('Stop')
        return rows
    def clock_cases(self):
        states=[];self.w.set_property('PreviousTime',0)
        for value in (720.,61.25,10.9,10.,9.99,9.1,9.1,8.,0.,-1.2,10.,5.):
            audio=self.audio_call(policy.CLOCK_SOUND,lambda:self.w.call_function('UpdateClock',value));states.append(dict(time=value,text=text(self.w.get_property('Clock')),previous=int(self.w.get_property('PreviousTime')),audio=audio));self.row['clock_cases']+=1
        return states
    def sound_cases(self):
        states=[];self.w.set_property('PreviousScoreLeft',0)
        for left in (7,5,5,4,1,0,-2,8):
            self.set_tag(1,1000-left);self.set_tag(2,0);audio=self.audio_call(policy.SCORE_SOUND,lambda:self.w.call_function('EvaluateSound_RoundEnding',self.scoring));states.append(dict(left=left,previous=int(self.w.get_property('PreviousScoreLeft')),audio=audio));self.row['score_sound_cases']+=1
        return states
    def run_cases(self):
        states=dict(styles=self.style_cases(),scores=self.score_cases(),clock=self.clock_cases(),sound=self.sound_cases());self.states.append(states);self.report['matrices']=self.states;self.scoring.set_property('TargetScore',1000);self.set_tag(1,31);self.set_tag(2,47);before=count(self.w,'score');self.scoring.call_function(scoring_policy.SET_TARGET,1001);self.row['native_player_counted_delegate']=count(self.w,'score')==before+1;self.scoring.call_function(scoring_policy.SET_TIME,self.countdown+20.);self.time_before=float(self.scoring.get_property('CountDownTime'));self.score_before=count(self.w,'score');self.enter('native-tick')
    def observe(self):
        require(time.monotonic()-self.phase_started<15.,'native TDM HUD phase timeout: '+self.phase)
        if self.phase=='bind':
            self.frames+=1
            if self.frames<3 or self.w.get_property('TDMScoring')!=self.scoring:return
            self.row['actual_construct_and_async_team_binding']=count(self.w,'team')>0 and count(self.w,'clock')>0;self.run_cases()
        elif self.phase=='native-tick':
            clocks=self.observed_clocks.get(self.w,[])
            if len(clocks)<4:return
            require([self.w.get_property(n).call_function('GetTargetValue') for n in ('AllyScore','AllyGoal','EnemyScore','EnemyGoal')]==[31.,1001.,47.,1001.],'actual native score Tick/target refresh missing');self.row['actual_native_score_ticks']=count(self.w,'score')>self.score_before;self.row['observed_native_clock_samples']=clocks[:];self.row['native_clock_interval']=clocks[-1][0]-clocks[-2][0];self.row['native_timer_handle_active']=bool(policy.lib('KismetSystemLibrary').call_function('K2_IsTimerActiveHandle',self.scoring,self.scoring.get_property('TimerCountdown')));self.row['native_countdown_timer_delegate']=self.row['native_timer_handle_active'] and self.scoring.get_property('CountDownTime')<self.time_before and int(self.w.get_property('PreviousTime'))==int(clocks[-1][1]);self.w.call_function('RemoveFromParent');self.removed_score=count(self.w,'score');self.removed_clock=count(self.w,'clock');self.enter('removed')
        elif self.phase=='removed':
            if count(self.w,'clock')<=self.removed_clock:return
            self.row['removed_tick_stops_but_countdown_binding_remains']=count(self.w,'score')==self.removed_score;self.w.call_function('AddToPlayerScreen',0);self.frames=0;self.enter('remount')
        elif self.phase=='remount':
            self.frames+=1
            if self.frames<3:return
            before=count(self.w,'clock');self.scoring.call_function(scoring_policy.SET_TIME,self.countdown+10.);self.row['remount_callback_count']=count(self.w,'clock')-before;self.row['diagnostic_fallbacks']=sum(policy.evidence(w)['diagnostic_fallbacks'] for w in self.widgets);self.w.call_function('RemoveFromParent');self.report['profiles'].append(self.row);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:
                self.report['native_source_pairs_match']=self.states[0]==self.states[1]
                for row in self.report['profiles']:row.update(full_brush_fields_and_tints_match=self.states[0]['styles']==self.states[1]['styles'],numeric_values_and_unclamped_arcs_match=self.states[0]['scores']==self.states[1]['scores'],localized_clock_floor_and_audio_match=self.states[0]['clock']==self.states[1]['clock'],score_audio_parameters_match=self.states[0]['sound']==self.states[1]['sound'],remount_callback_count_matches_source=self.report['profiles'][0]['remount_callback_count']==self.report['profiles'][1]['remount_callback_count']>=1)
                self.finish()
    def cleanup(self):
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        self.cls.get_cdo().set_property('PythonMixinProfile',self.cdo_profile)
        for p,base in self.sources.items():ue.register_mixin_profile(self.cls,p,base)
        registered,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];wrappers_restored=all(registered['profiles'][p]['python_class'] is base for p,base in self.sources.items())
        for team,value in self.tag_before.items():self.set_tag(team,value)
        self.scoring.call_function(scoring_policy.SET_TARGET,self.target);self.scoring.call_function(scoring_policy.SET_TIME,self.countdown);self.report.update(widget_roots_removed=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets),profile_selectors_and_wrappers_restored=wrappers_restored and self.cls.get_cdo().get_property('PythonMixinProfile')==self.cdo_profile,team_tag_deltas_restored=all(self.get_tag(i)==v for i,v in self.tag_before.items()),real_target_score_restored=self.scoring.get_property('TargetScore')==self.target,real_countdown_value_restored=self.scoring.get_property('CountDownTime')==self.countdown,original_health_unchanged=self.healths()==self.health_before)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native TDM HUD timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ELIMINATION_SCORE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ELIMINATION_SCORE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPEliminationScoreResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
