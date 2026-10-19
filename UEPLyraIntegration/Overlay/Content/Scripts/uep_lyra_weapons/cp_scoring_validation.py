"""Actual CP Experience, typed capture API, native scoring clock and PostGame."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead,color
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import cp_scoring_mixin as policy
from .cp_scoring_contract import PROFILES,TIMER_CASES,require,validate

TIMER='UEPCPNativeStartScoring'


def count(c,n):return sum(policy.evidence(c)[p+'_'+n] for p in ('python','fallback'))
def path(o):return o.get_path_name() if valid(o) else None


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,array_cases=[],capture_cases=[],query_cases=[],palette_cases=[],timer_cases=[],cue_cases=[]);self.components=[];self.winners=[];self.suppress=True;self.index=0;self.sources={};self.units=[]
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callback_replayed','timer_callback_replayed','physical_capture_overlap_tested','health_properties_written'):self.report[k]=False
        self.report['controlled_victory_receiver_for_intermediate_timer_cases']=True
    def scores(self):return [int(self.team.call_function('GetTeamTagStackCount',i,policy.base.tag('ShooterGame.ControlPoint.TeamScore'))) for i in (1,2)]
    def set_scores(self,values):
        for team,a,b in zip((1,2),self.scores(),values):
            delta=b-a
            if delta:self.team.call_function('AddTeamTagStack' if delta>0 else 'RemoveTeamTagStack',team,policy.base.tag('ShooterGame.ControlPoint.TeamScore'),abs(delta))
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.state=self.statics.call_function('GetGameState',self.world);self.real=self.state.get_component_by_type(self.cls);require(valid(self.real),'actual CP Experience component absent')
        self.report['natural_startup']=dict(policy.evidence(self.real));self.report['actual_point_count']=len(self.real.get_property('ControlPoints'));self.real_target=int(self.real.get_property('TargetScore'));self.real.set_property('TargetScore',2000000000);self.team=policy.base.teams(self.real);self.score_before=self.scores()
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];self.sources={p:r['python_class'] for p,r in row['profiles'].items()};owner=self
        for profile,source in self.sources.items():
            methods={n:v for n,v in vars(source).items() if not n.startswith('__') and callable(v)}
            def observe(handler):
                def invoke(c,TeamId):
                    if owner.suppress:owner.winners.append((c,int(TeamId)));return False
                    return handler(c,TeamId)
                invoke.override=policy.GATES['Victory'];return invoke
            methods['Victory']=observe(source.Victory);ue.register_mixin_profile(self.cls,profile,type('ObservedCP'+profile,(),methods))
        self.points=[self.own() for _ in range(3)];self.units=[self.unit(i) for i in (0,1)];self.array_trials();self.capture_trials();self.query_trials();self.palette_trials();self.cue_trials();self.start_timer()
    def component(self,profile):
        c=ue.new_object(self.cls,self.state);c.add_to_root();self.components.append(c);ue.set_mixin_profile(c,profile);return c
    def unit(self,index):
        pc=self.world.actor_spawn(ue.find_class('LyraPlayerController'));ps=pc.get_property('PlayerState');pawn=self.world.actor_spawn(ue.find_class('LyraCharacter'),ue.FVector(250000.+index*10000.,250000.,3000.));self.actors.extend((pc,ps,pawn));pc.call_function('Possess',pawn);manager=ue.new_object(ue.find_class('CheatManager'),pc);cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager);cheats.call_function('SetTeam',index+1);return dict(controller=pc,state=ps,pawn=pawn,manager=manager,cheats=cheats)
    def array_trials(self):
        for profile in PROFILES:
            c=self.component(profile)
            for p in (self.points[0],self.points[0],self.points[1]):c.call_function('RegisterControlPoint',p)
            initial=list(c.get_property('ControlPointOwnerTeams'));c.call_function('RecapturePointByTeam',self.points[0],2);recaptured=list(c.get_property('ControlPointOwnerTeams'));c.call_function('ContestPoint',self.points[0]);contested=list(c.get_property('ControlPointOwnerTeams'))
            self.report['array_cases'].append(dict(profile=profile,point_count=len(c.get_property('ControlPoints')),initial=initial,recaptured=recaptured,contested=contested))
    def capture_trials(self):
        tag=policy.base.tag('ShooterGame.Score.ControlPointCapture')
        for profile in PROFILES:
            c=self.component(profile);c.call_function('RegisterControlPoint',self.points[0]);before=[int(u['state'].call_function('GetStatTagStackCount',tag)) for u in self.units]
            c.call_function('CapturePoint',[self.units[1]['pawn'],self.units[0]['pawn'],self.units[1]['pawn']],self.points[0]);after=[int(u['state'].call_function('GetStatTagStackCount',tag)) for u in self.units]
            self.report['capture_cases'].append(dict(profile=profile,owners=list(c.get_property('ControlPointOwnerTeams')),stat_deltas=[a-b for a,b in zip(after,before)],native_gate_entries=count(c,'Capture')))
            for unit,a,b in zip(self.units,after,before):
                if a>b:unit['state'].call_function('RemoveStatTagStack',tag,a-b)
    def query_trials(self):
        for profile in PROFILES:
            c=self.component(profile);c.set_property('ControlPointOwnerTeams',[-1,1,2,8]);c.call_function(policy.SET_TARGET,5)
            for team in (-1,1,2):self.report['query_cases'].append(dict(profile=profile,kind='status',team=team,outputs=list(c.call_function('GetPointStatus',team))))
            for score in (4,5,6):
                self.set_scores((score,0));self.report['query_cases'].append(dict(profile=profile,kind='score',score=score,outputs=list(c.call_function('GetTeamScoreCP',1))))
        self.set_scores(self.score_before)
    def palette_trials(self):
        for profile in PROFILES:
            c=self.component(profile);c.set_property('TeamColors',{});c.set_property('RawTeamColors',[ue.FLinearColor(.2,.4,.6,.8),ue.FLinearColor(.7,.5,.3,1.)]);c.set_property('TeamColorAssignIndex',0);values=[]
            for team in (7,8,7):
                result=c.call_function('GetTeamColor',team);values.append(color(result[0] if isinstance(result,tuple) else result))
            self.report['palette_cases'].append(dict(profile=profile,colors=values,index=int(c.get_property('TeamColorAssignIndex')),cached_teams=sorted(c.get_property('TeamColors'))))
    def cue_trials(self):
        cls=ue.load_class('/ShooterCore/GameplayCues/GCNL_WaitingForPlayers.GCNL_WaitingForPlayers_C');tag=cls.get_cdo().get_property('GameplayCueTag')
        for profile in PROFILES:
            c=self.component(profile);c.call_function('ActivateUserFacingCue',tag,policy.params());found=[a for a in self.world.all_actors() if valid(a) and a.is_a(cls) and a.call_function('GetOwner')==self.state];c.call_function('ClearUserFacingCue');self.report['cue_cases'].append(dict(profile=profile,manager_actor_count=len(found),cleared=not policy.lib('BlueprintGameplayTagLibrary').call_function('IsGameplayTagValid',c.get_property('ActiveUserFacingCue'))))
    def start_timer(self):
        self.profile,self.owners,self.expected=TIMER_CASES[self.index];self.set_scores((0,0));self.current=self.component(self.profile);self.current.set_property('ControlPointOwnerTeams',self.owners);self.current.set_property('LeadingTeam',9);self.current.call_function(policy.SET_TARGET,1);self.start=time.monotonic();self.winner_start=len(self.winners);self.current.call_function(TIMER);self.enter('timer')
    def timer(self):
        ticks=count(self.current,'Scoring')
        if ticks==0:require(time.monotonic()-self.start<5.,'native CP scoring timer did not fire');return
        scores=self.scores();leading=int(self.current.get_property('LeadingTeam'));events=[team for c,team in self.winners[self.winner_start:] if c==self.current];self.current.call_function(policy.CLEAR_TIMER)
        handle=self.current.get_property('ScoringTimer');active=bool(policy.lib('KismetSystemLibrary').call_function('K2_IsTimerActiveHandle',self.current,handle));valid_handle=bool(policy.lib('KismetSystemLibrary').call_function('K2_IsValidTimerHandle',handle))
        self.report['timer_cases'].append(dict(profile=self.profile,owners=self.owners,expected=self.expected,ticks=ticks,scores=scores,leading=leading,winners=events,timer_active=active,handle_valid=valid_handle))
        self.index+=1
        if self.index<len(TIMER_CASES):self.start_timer()
        else:
            self.set_scores(self.score_before);self.suppress=False;ue.set_mixin_profile(self.real,'Python');self.real.call_function('HandleVictory',2);self.enter('victory')
    def victory(self):
        system=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraGamePhaseSubsystem'));phase=ue.load_class('/ShooterCore/Experiences/Phases/Phase_PostGame.Phase_PostGame_C').get_cdo().get_property('GamePhaseTag')
        if not system.call_function('IsPhaseActive',phase):require(time.monotonic()-self.phase_started<10.,'native CP PostGame phase absent');return
        handle=self.real.get_property('ScoringTimer');cls=ue.load_class('/ShooterCore/GameplayCues/GCNL_MatchDecided.GCNL_MatchDecided_C');found=[a for a in self.world.all_actors() if valid(a) and a.is_a(cls) and a.call_function('GetOwner')==self.state]
        self.report['actual_victory']=dict(winner=int(self.real.get_property('WinningTeamId')),phase_active=True,manager_cue_count=len(found),timer_active=bool(policy.lib('KismetSystemLibrary').call_function('K2_IsTimerActiveHandle',self.real,handle)),handle_valid=bool(policy.lib('KismetSystemLibrary').call_function('K2_IsValidTimerHandle',handle)));self.finish()
    def cleanup(self):
        for c in self.components:
            if valid(c):c.call_function(policy.CLEAR_TIMER);c.remove_from_root();c.call_function('K2_DestroyComponent',self.state)
        for actor in self.actors:
            if not dead(actor):actor.actor_destroy()
        if hasattr(self,'score_before'):self.set_scores(self.score_before)
        for profile,source in self.sources.items():ue.register_mixin_profile(self.cls,profile,source)
        if hasattr(self,'real') and valid(self.real):self.real.set_property('TargetScore',self.real_target);ue.clear_mixin_profile(self.real)
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),owned_components_destroyed=all(not valid(c) for c in self.components),native_scores_restored=hasattr(self,'score_before') and self.scores()==self.score_before,production_profiles_restored=bool(self.sources) and any(r['target_class']==self.cls and all(r['profiles'][p]['python_class'] is source and len(r['profiles'][p]['functions'])==18 for p,source in self.sources.items()) for r in ue.get_registered_mixins()))
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native CP total timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='timer':self.timer()
            elif self.phase=='victory':self.victory()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_CP_SCORING_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_CP_SCORING_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPCPScoringResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
