"""Current-map native target sources, full reflected styling and UMG activation."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from .message_widget_validation import model
from . import scoreboard_style_mixin as policy
from .scoreboard_style_contract import PROFILES,require,validate

TAG='ShooterGame.Score.Assists'


def text(w):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',w.call_function('GetText'))
def rgba(c):return [float(getattr(c,n)) for n in ('r','g','b','a')]
def near(a,b):return all(abs(x-y)<.00001 for x,y in zip(a,b))
def count(w,k):return sum(policy.evidence(w)[p+'_'+k] for p in ('python','fallback'))


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.mode=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPScoreboardStyleMode='));self.report=dict(status='running',error=None,mode=self.mode,profiles=[]);self.widgets=[];self.index=0;self.states=[];self.ticks={}
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','activation_callbacks_replayed','localized_team_name_roundtripped','health_properties_written'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        registry,=[r for r in ue.get_registered_mixins() if r['target_class']==self.classes['team']];self.team_sources={p:r['python_class'] for p,r in registry['profiles'].items()}
        for profile,base in self.team_sources.items():
            def around(fn):
                def invoke(w):
                    self.ticks.setdefault(w,[]).append(self.game_time());return fn(w)
                invoke.override=policy.GATES['update'];return invoke
            ue.register_mixin_profile(self.classes['team'],profile,type('ObservedScoreboardTeam'+profile,(),dict(Style=base.Style,Update=around(base.Update),Goal=base.Goal)))
        self.team=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'));name='B_TeamDeathMatchScoring' if self.mode=='tdm' else 'B_ControlPointScoring';folder='Elimination' if self.mode=='tdm' else 'ControlPoint';self.scoring=self.statics.call_function('GetGameState',self.world).get_component_by_type(ue.load_class('/ShooterCore/'+folder+'/'+name+'.'+name+'_C'));require(self.scoring is not None,'actual mode score component missing');self.target=int(self.scoring.get_property('TargetScore'));self.tag_before={i:int(self.team.call_function('GetTeamTagStackCount',i,GameplayTag(TagName=TAG))) for i in (1,2)};self.start_profile()
    def create(self,key,team=1):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[key],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile)
        if key=='team':w.set_property('TeamId',team);w.set_property('StatId',GameplayTag(TagName=TAG));w.set_property('IsTDMScoring',self.mode=='tdm')
        elif key.startswith('header'):w.set_property('TeamId',team)
        w.call_function('AddToPlayerScreen',0);return w
    def color_matches(self,w,field,team,alpha):return near(rgba(w.get_property(field).get_property('ColorAndOpacity').SpecifiedColor),rgba(policy.color(team,alpha)))
    def brush_state(self,w,field,is_border):return w.get_property(field).get_property('Background' if is_border else 'Brush')
    def seed(self,w,field,is_border):
        control=w.get_property(field);b=self.brush_state(w,field,is_border);size=b.ImageSize;size.X=137.;size.Y=43.;b.ImageSize=size;b.Margin=ue.find_struct('Margin')(Left=.1,Top=.2,Right=.3,Bottom=.4);b.Tiling=1;b.Mirroring=2;control.call_function('SetBrush',b);return b
    def check_brush(self,w,field,is_border,before,kind,team):
        after=self.brush_state(w,field,is_border);same=all(model(getattr(after,n))==model(getattr(before,n)) for n in policy.BRUSH_FIELDS);resource=after.ResourceObject
        if kind=='icon':same &= resource is not None and resource.get_property('Parent').get_path_name()==policy.RESOURCES[kind][team] and resource.call_function('K2_GetScalarParameterValue','RotationSpeed')==-2.
        else:same &= resource is not None and resource.get_path_name()==policy.RESOURCES[kind][team]
        return same
    def canonical_brush(self,w,field,is_border):
        b=self.brush_state(w,field,is_border);value=model(b);resource=b.ResourceObject
        if resource is not None and resource.is_a(ue.find_class('MaterialInstanceDynamic')):value['ResourceObject']=dict(parent=resource.get_property('Parent').get_path_name(),rotation=float(resource.call_function('K2_GetScalarParameterValue','RotationSpeed')))
        return value
    def animation_state(self):
        a=self.board.get_property('OnActivated');return dict(playing=bool(self.board.call_function('IsAnimationPlaying',a)),forward=bool(self.board.call_function('IsAnimationPlayingForward',a)),position=float(self.board.call_function('GetAnimationCurrentTime',a)),end=float(a.call_function('GetEndTime')))
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        row=dict(profile=self.profile,team_names_match_native_literals=True,all_text_tints_match=True,all_brush_resources_and_source_fields_match=True,glow_rotation_speed_match=True,target_score_matches_mode=True);self.row=row;self.report['pending_profile']=row;self.current=[];states=[]
        for team in (1,2):
            w=self.create('team',team);self.current.append(w);seeds={n:self.seed(w,n,border) for n,border in (('TeamIcon',False),('BodyBorder',True),('HeaderBorder',True),('StatGlow',False))};w.call_function('SetTeamStyle');row['team_names_match_native_literals'] &= text(w.get_property('TeamName'))==('Red' if team==1 else 'Blue');row['all_text_tints_match'] &= all(self.color_matches(w,n,team,a) for n,a in (('TeamName',.1),('StatGoalText',.6),('TeamText',.4),('StatTextWidget',1.)))
            row['all_brush_resources_and_source_fields_match'] &= all(self.check_brush(w,n,border,seeds[n],kind,team) for n,border,kind in (('TeamIcon',False,'icon'),('BodyBorder',True,'fill'),('HeaderBorder',True,'header'),('StatGlow',False,'glow')));row['glow_rotation_speed_match'] &= float(w.get_property('TeamIcon').call_function('GetDynamicMaterial').call_function('K2_GetScalarParameterValue','RotationSpeed'))==-2.;row['target_score_matches_mode'] &= text(w.get_property('StatGoalText'))==str(self.scoring.get_property('TargetScore'));states.append(dict(kind='team',team=team,tints={n:rgba(w.get_property(n).get_property('ColorAndOpacity').SpecifiedColor) for n in ('TeamName','StatGoalText','TeamText','StatTextWidget')},brushes={n:self.canonical_brush(w,n,b) for n,b in (('TeamIcon',False),('BodyBorder',True),('HeaderBorder',True))}))
            for key in ('headercp','headertdm'):
                header=self.create(key,team);seed=self.seed(header,'HeaderBorder',True);header.call_function('SetTeamStyle');row['all_text_tints_match'] &= all(self.color_matches(header,n,team,.4) for n in ('PlayerNameWidget','ElimCount','BeenEliminatedCount','AssistCount','ConnectionStatus'));row['all_brush_resources_and_source_fields_match'] &= self.check_brush(header,'HeaderBorder',True,seed,'header',team);states.append(dict(kind=key,team=team,brush=model(self.brush_state(header,'HeaderBorder',True))))
        self.states.append(states);self.board=self.create('board'+self.mode);self.board.call_function('DeactivateWidget');self.settle_frames=0;self.enter('settle-activation')
    def set_tag(self,team,value):
        current=int(self.team.call_function('GetTeamTagStackCount',team,GameplayTag(TagName=TAG)))
        if current:self.team.call_function('RemoveTeamTagStack',team,GameplayTag(TagName=TAG),current)
        if value:self.team.call_function('AddTeamTagStack',team,GameplayTag(TagName=TAG),value)
    def observe(self):
        require(time.monotonic()-self.phase_started<8.,'native scoreboard style phase timeout: '+self.phase)
        if self.phase=='settle-activation':
            self.settle_frames+=1
            if self.settle_frames<3:return
            before=count(self.board,'activate');self.board.call_function('ActivateWidget');self.row['actual_activation_callback']=count(self.board,'activate')==before+1;self.row['immediate_animation_state']=self.animation_state();self.enter('reactivate')
        elif self.phase=='reactivate':
            if self.animation_state()['position']<.05:return
            a=self.board.get_property('OnActivated');self.row['delayed_animation_state']=self.animation_state();self.row['native_animation_playing']=bool(self.board.call_function('IsAnimationPlayingForward',a));self.board.call_function('DeactivateWidget');before=self.board.call_function('IsAnimationPlayingForward',a);stops=policy.evidence(self.board)['stops'];self.board.call_function('ActivateWidget');self.row['reactivated_animation_state']=self.animation_state();self.row['reactivation_matches_native_source_condition']=bool(self.board.call_function('IsAnimationPlayingForward',a)) and (self.profile!='Python' or policy.evidence(self.board)['stops']-stops==int(before));self.goal_before=[text(w.get_property('StatGoalText')) for w in self.current];self.update_before=[count(w,'update') for w in self.current];self.change_time=self.game_time();self.scoring.set_property('TargetScore',self.target+3);self.set_tag(1,7);self.set_tag(2,11);self.enter('native-timer')
        elif self.phase=='native-timer':
            if [text(w.get_property('StatTextWidget')) for w in self.current]!=['7','11'] or any(count(w,'update')<=n or len(self.ticks.get(w,[]))<2 for w,n in zip(self.current,self.update_before)):return
            intervals=[self.ticks[w][-1]-self.ticks[w][-2] for w in self.current];self.row.update(native_stat_tag_updates=True,target_not_refreshed_by_timer=[text(w.get_property('StatGoalText')) for w in self.current]==self.goal_before,native_update_elapsed_seconds=min(intervals),native_update_intervals=intervals,diagnostic_fallbacks=sum(policy.evidence(w)['diagnostic_fallbacks'] for w in self.widgets));self.report['profiles'].append(self.row);self.scoring.set_property('TargetScore',self.target)
            for i,v in self.tag_before.items():self.set_tag(i,v)
            self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report['native_source_style_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for profile,base in self.team_sources.items():ue.register_mixin_profile(self.classes['team'],profile,base)
        for i,v in self.tag_before.items():self.set_tag(i,v)
        self.scoring.set_property('TargetScore',self.target);self.report.update(widget_roots_removed=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets),profile_selectors_restored=all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items()),team_tag_deltas_restored=all(int(self.team.call_function('GetTeamTagStackCount',i,GameplayTag(TagName=TAG)))==v for i,v in self.tag_before.items()),real_target_score_restored=self.scoring.get_property('TargetScore')==self.target,original_health_unchanged=self.healths()==self.health_before)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native scoreboard style timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SCOREBOARD_STYLE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SCOREBOARD_STYLE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPScoreboardStyleResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
