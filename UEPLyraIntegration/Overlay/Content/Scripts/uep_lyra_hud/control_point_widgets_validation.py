"""Mounted native widgets plus explicit original-BP/Python policy differentials."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from .message_widget_validation import model
from . import control_point_widgets_mixin as policy
from .control_point_widgets_contract import PROFILES,FALSE_FIELDS,TRUE_FIELDS,require,validate

TAG='ShooterGame.ControlPoint.TeamScore'
PARAMS={'Fill':('IsEmptyPoint','IsRedOrBlue'),'SoftGlow':('IsEmptyPoint','IsRedOrBlue'),'PointLetter':('Hover_Animate','bIsDisabled'),'Ring':('IsEmptyPoint','IsRedOrBlue','IsContested','IsFlashing'),'RingGlow':('IsEmptyPoint','IsRedOrBlue','IsContested','IsFlashing'),'BurstRing':('IsEmptyPoint','IsRedOrBlue')}


def text(w):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',w.call_function('GetText'))
def count(w,k):return sum(policy.evidence(w)[p+'_'+k] for p in ('python','fallback'))
def rgba(c):return [round(float(getattr(c,n)),5) for n in ('r','g','b','a')]


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],direct_tick_fixture_used=True);self.widgets=[];self.states=[];self.index=0
        self.report.update(dict.fromkeys(FALSE_FIELDS,False))
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.scoring=self.statics.call_function('GetGameState',self.world).get_component_by_type(ue.load_class('/ShooterCore/ControlPoint/B_ControlPointScoring.B_ControlPointScoring_C'));require(policy.valid(self.scoring),'actual CP scoring component missing');self.target=int(self.scoring.get_property('TargetScore'));self.points=list(self.scoring.get_property('ControlPoints'));require(len(self.points)>=3,'three actual map control points required');self.point_state={v:(int(v.get_property('OwnerTeamID')),list(v.get_property('OverlappingTeams'))) for v in self.points};self.team=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'));self.tag_before={i:self.get_tag(i) for i in (1,2)};self.start_profile()
    def get_tag(self,team):return int(self.team.call_function('GetTeamTagStackCount',team,GameplayTag(TagName=TAG)))
    def set_tag(self,team,value):
        current=self.get_tag(team)
        if current:self.team.call_function('RemoveTeamTagStack',team,GameplayTag(TagName=TAG),current)
        if value:self.team.call_function('AddTeamTagStack',team,GameplayTag(TagName=TAG),value)
    def create(self,key):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[key],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile);w.call_function('AddToPlayerScreen',0);return w
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.scoring.set_property('TargetScore',1000);self.set_tag(1,11);self.set_tag(2,19);self.current={k:self.create(k) for k in ('score','marker','status')};self.row=dict(profile=self.profile,style_cases=0,marker_cases=0,sound_cases=0,status_cases=0);self.report['pending_profile']=self.row;self.frames=0;self.enter('bind')
    def marker_state(self,w):return dict(owner=int(w.get_property('PointOwnerTeamId')),previous=int(w.get_property('PreviousPointOwnerTeamId')),parameters={f:{n:round(float(w.get_property(f+'MID').call_function('K2_GetScalarParameterValue',n)),5) for n in names} for f,names in PARAMS.items()})
    def marker_cases(self):
        w=self.current['marker'];v=self.points[0];states=[];conditions=[]
        for owner,teams in ((0,()),(1,()),(1,(1,)),(1,(2,)),(1,(1,2)),(1,()),(2,(2,)),(2,(1,)),(2,(2,1)),(0,(1,)),(0,(2,)),(0,(1,2)),(0,())):
            old=(v.get_property('OwnerTeamID'),list(v.get_property('OverlappingTeams')));v.set_property('OwnerTeamID',owner);v.set_property('OverlappingTeams',list(teams));before=int(w.get_property('PreviousPointOwnerTeamId'));w.call_function('StopAllAnimations');w.call_function('UpdateControlPointStatus',v);conditions.append(bool(w.call_function('IsAnimationPlayingForward',w.get_property('OnPointOwnerChanged')))==(before!=owner));states.append(self.marker_state(w));v.set_property('OwnerTeamID',old[0]);v.set_property('OverlappingTeams',old[1])
        self.row['marker_cases']=len(states);self.row['immediate_animation_queries']=conditions;return states
    def brush_state(self,w,field):
        b=w.get_property(field).get_property('Brush');return {n:model(getattr(b,n)) for n in policy.brush.__globals__['BRUSH_FIELDS']+('ResourceObject',)}
    def style_cases(self):
        w=self.current['score'];states=[]
        for team in (0,1,2):
            w.set_property('MyTeamID',team);w.set_property('EnemyTeamID',{0:0,1:2,2:1}[team]);w.call_function('UpdateStyleSides');w.call_function('UpdateTeamStyles');states.append(dict(colors={n:rgba(w.get_property(n).get_property('ColorAndOpacity').SpecifiedColor) for n in ('AllyScore','EnemyScore')},brushes={n:self.brush_state(w,n) for n in ('AllyLogo','EnemyLogo','AllyScoreGlow','EnemyScoreGlow')},inverse=float(w.get_property('ScoreBorder').call_function('GetDynamicMaterial').call_function('K2_GetScalarParameterValue','InverseGradient'))));self.row['style_cases']+=1
        return states
    def audio_objects(self):return {a for a in self.world.all_objects() if policy.valid(a) and a.is_a(ue.find_class('AudioComponent')) and a.get_property('Sound') is not None and a.get_property('Sound').get_path_name()==policy.SOUND}
    def sound_cases(self):
        w=self.current['score'];w.set_property('MyTeamID',1);w.set_property('EnemyTeamID',2);w.set_property('PreviousScoreLeft',0);states=[]
        for left in (7,5,5,4,1,0,-2,8):
            self.set_tag(1,1000-left);self.set_tag(2,0);before=self.audio_objects();previous=int(w.get_property('PreviousScoreLeft'));w.call_function('EvaluateSound_RoundEnding',self.scoring);new=self.audio_objects()-before;parameters=[{str(p.ParamName):int(p.IntParam) for p in a.get_property('InstanceParameters')} for a in new];expected=int(0<left<=5 and previous!=left);require(len(new)==expected and all(p.get('ScoreLeft')==left for p in parameters),'native score-left audio differs');states.append(dict(left=left,previous=int(w.get_property('PreviousScoreLeft')),spawned=len(new),parameters=parameters));self.row['sound_cases']+=1
            for a in new:a.call_function('Stop')
        self.row['unchanged_score_does_not_retrigger']=states[2]['spawned']==0;self.row['score_left_native_audio_parameters_match']=True;return states
    def status_cases(self):
        w=self.current['status'];states=[]
        for team,points in ((1,self.points[:3]),(-1,list(reversed(self.points[:3]))),(0,self.points[:3]+self.points[:1])):
            self.scoring.set_property('ControlPoints',points);w.set_property('MyTeamID',team);before=[count(w.get_property('W_ControlPointMarker_'+n),'marker') for n in 'ABC'];w.call_function('Tick',w.call_function('GetCachedGeometry'),0.);after=[count(w.get_property('W_ControlPointMarker_'+n),'marker') for n in 'ABC'];expected=[0,0,0] if team<0 else [1,1,len(points)-2];require([a-b for a,b in zip(after,before)]==expected,'source status index/negative-team guard differs');states.append([int(w.get_property('W_ControlPointMarker_'+n).get_property('PointOwnerTeamId')) for n in 'ABC']);self.row['status_cases']+=1
        self.scoring.set_property('ControlPoints',self.points);return states
    def run_cases(self):
        marker=self.marker_cases();styles=self.style_cases();status=self.status_cases();sound=self.sound_cases();self.states.append(dict(marker=marker,styles=styles,status=status,sound=sound));self.report['matrices']=self.states;w=self.current['score'];w.set_property('MyTeamID',1);w.set_property('EnemyTeamID',2);self.set_tag(1,1017);self.set_tag(2,23);w.call_function('UpdateScore');self.row['native_text_and_clamp_match']=[text(w.get_property(n)) for n in ('Goal','AllyScore','EnemyScore')]==['1,000','1,000','23'];self.set_tag(1,31);self.set_tag(2,47);self.scoring.set_property('TargetScore',1001);self.tick_before=(count(w,'score'),count(self.current['status'],'status'));self.enter('native-tick')
    def animation_owner(self,owner):
        v=self.points[0];old=v.get_property('OwnerTeamID');v.set_property('OwnerTeamID',owner)
        try:self.current['marker'].call_function('UpdateControlPointStatus',v)
        finally:v.set_property('OwnerTeamID',old)
    def observe(self):
        require(time.monotonic()-self.phase_started<15.,'native CP HUD phase timeout: '+self.phase)
        if self.phase=='bind':
            self.frames+=1
            if self.frames<3 or any(self.current[k].get_property('ControlPointMode')!=self.scoring for k in ('score','status')):return
            self.row['actual_construct_and_native_async_binding']=all(count(self.current[k],'scoreteam' if k=='score' else 'statusteam')>0 for k in ('score','status')) and count(self.current['marker'],'initialize')>=2;self.run_cases()
        elif self.phase=='native-tick':
            w=self.current['score'];counts=(count(w,'score'),count(self.current['status'],'status'))
            if counts[0]<=self.tick_before[0] or counts[1]<=self.tick_before[1]:return
            require([text(w.get_property(n)) for n in ('Goal','AllyScore','EnemyScore')]==['1,001','31','47'],'actual native score Tick did not refresh');self.row['actual_score_and_status_ticks']=True;self.row['diagnostic_fallbacks']=sum(policy.evidence(w)['diagnostic_fallbacks'] for w in self.widgets);w=self.current['marker'];w.call_function('StopAllAnimations');w.set_property('PreviousPointOwnerTeamId',1);self.animation_owner(1);self.frames=0;self.enter('animation-idle')
        elif self.phase=='animation-idle':
            self.frames+=1
            if self.frames<3:return
            w=self.current['marker'];a=w.get_property('OnPointOwnerChanged');require(not w.call_function('IsAnimationPlaying',a),'unchanged owner started native animation');self.animation_owner(2);self.enter('animation-started')
        elif self.phase=='animation-started':
            w=self.current['marker'];a=w.get_property('OnPointOwnerChanged');position=float(w.call_function('GetAnimationCurrentTime',a))
            if position<.01:return
            require(w.call_function('IsAnimationPlayingForward',a),'changed owner did not start actual native animation');self.animation_position=position;self.row['native_owner_animation']=dict(position=position,end=float(a.call_function('GetEndTime')));self.animation_owner(2);self.enter('animation-unchanged')
        elif self.phase=='animation-unchanged':
            w=self.current['marker'];a=w.get_property('OnPointOwnerChanged');position=float(w.call_function('GetAnimationCurrentTime',a));require(position>=self.animation_position,'unchanged owner restarted native animation');self.row['native_owner_animation']['unchanged_owner_position']=position;self.row['owner_animation_condition_match']=True
            for w in self.current.values():w.call_function('RemoveFromParent')
            self.removed_before=(count(self.current['score'],'score'),count(self.current['status'],'status'));self.frames=0;self.enter('removed')
        elif self.phase=='removed':
            self.frames+=1
            if self.frames<3:return
            self.row['removed_widgets_stop_native_ticks']=self.removed_before==(count(self.current['score'],'score'),count(self.current['status'],'status'));self.report['profiles'].append(self.row);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:
                match=self.states[0]==self.states[1];self.report['native_source_pairs_match']=match
                for row in self.report['profiles']:row.update(style_brush_fields_and_colors_match=self.states[0]['styles']==self.states[1]['styles'],all_marker_scalar_states_match=self.states[0]['marker']==self.states[1]['marker'],status_index_and_negative_team_guard_match=self.states[0]['status']==self.states[1]['status'])
                self.finish()
    def cleanup(self):
        for w in self.widgets:
            ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for i,v in self.tag_before.items():self.set_tag(i,v)
        self.scoring.set_property('TargetScore',self.target);self.scoring.set_property('ControlPoints',self.points)
        for v,(owner,teams) in self.point_state.items():v.set_property('OwnerTeamID',owner);v.set_property('OverlappingTeams',teams)
        self.report.update(widget_roots_removed=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets),profile_selectors_restored=all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items()),team_tag_deltas_restored=all(self.get_tag(i)==v for i,v in self.tag_before.items()),real_target_score_restored=self.scoring.get_property('TargetScore')==self.target,original_point_state_restored=list(self.scoring.get_property('ControlPoints'))==self.points and all((int(v.get_property('OwnerTeamID')),list(v.get_property('OverlappingTeams')))==s for v,s in self.point_state.items()),original_health_unchanged=self.healths()==self.health_before)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native CP HUD timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_CONTROL_POINT_WIDGETS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_CONTROL_POINT_WIDGETS_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPControlPointWidgetsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
