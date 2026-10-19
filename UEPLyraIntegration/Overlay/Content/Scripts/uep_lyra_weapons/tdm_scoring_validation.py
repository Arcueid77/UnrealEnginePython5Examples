"""Actual TDM timers/RepNotify/GAS/GMS and final native PostGame transition."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import LyraVerbMessage
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import tdm_scoring_mixin as policy
from .tdm_scoring_contract import PROFILES,COUNTDOWN_CASES,require,validate


def path(value):return value.get_path_name() if valid(value) else None
def count(c,name):return sum(policy.evidence(c)[p+'_'+name] for p in ('python','fallback'))


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,query_cases=[],countdown_cases=[],damage_cases=[],cue_cases=[],message_cases=[]);self.components=[];self.bindings=[];self.winners=[];self.index=0;self.suppress=True;self.units=[]
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callback_replayed','timer_callbacks_replayed','health_properties_written'):self.report[k]=False
        self.report['controlled_victory_receiver_used_for_decision_matrix']=True
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.state=self.statics.call_function('GetGameState',self.world);self.real=self.state.get_component_by_type(self.cls);require(valid(self.real),'actual native TDM component absent')
        self.report['natural_startup']=dict(policy.evidence(self.real));self.real_profile=str(ue.get_mixin_profile(self.real));self.real_target=int(self.real.get_property('TargetScore'));self.real_time=float(self.real.get_property('CountDownTime'));self.health_before=self.healths()
        self.team=policy.base.teams(self.real);self.score_before=self.team_scores();self.sources={};row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];self.sources={p:r['python_class'] for p,r in row['profiles'].items()};owner=self
        for profile,source in self.sources.items():
            methods={n:v for n,v in vars(source).items() if not n.startswith('__') and callable(v)}
            def observe(handler):
                def invoke(c,TeamId):
                    if owner.suppress:owner.winners.append((c,int(TeamId)));return False
                    return handler(c,TeamId)
                invoke.override=policy.GATES['Victory'];return invoke
            methods['Victory']=observe(source.Victory);ue.register_mixin_profile(self.cls,profile,type('ObservedTDM'+profile,(),methods))
        self.query_trials();self.damage_trials();self.cue_trials();self.message_trials();self.start_countdown()
    def team_scores(self):return [int(self.team.call_function('GetTeamTagStackCount',i,policy.base.tag('ShooterGame.Score.Eliminations'))) for i in (1,2)]
    def set_scores(self,values):
        for team,before,after in zip((1,2),self.team_scores(),values):
            delta=after-before
            if delta:self.team.call_function('AddTeamTagStack' if delta>0 else 'RemoveTeamTagStack',team,policy.base.tag('ShooterGame.Score.Eliminations'),abs(delta))
    def bind(self,c,event,fn):c.bind_event(event,fn);self.bindings.append((c,event,fn))
    def component(self,profile):
        c=ue.new_object(self.cls,self.state);c.add_to_root();self.components.append(c);ue.set_mixin_profile(c,profile);return c
    def query_trials(self):
        for profile in PROFILES:
            c=self.component(profile);notifications=[];self.bind(c,'PlayerCounted',lambda:notifications.append(True));c.call_function(policy.SET_TARGET,15)
            for score in (14,15,16):
                self.set_scores((score,0));out=c.call_function('GetTeamScore',1);self.report['query_cases'].append(dict(profile=profile,score=score,outputs=list(out),native_target_notify_count=len(notifications)))
        self.set_scores(self.score_before)
    def damage_trials(self):
        effect=ue.load_class(policy.IMMUNITY);asc=ability_system(self.pawn)
        require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(effect.get_cdo(),str(self.path.parent/'mode-immunity-effect.t3d')),'mode immunity CDO export failed')
        for profile in PROFILES:
            systems=[policy.lib('AbilitySystemBlueprintLibrary').call_function('GetAbilitySystemComponent',self.statics.call_function('GetPlayerState',self.world,i)) for i in range(int(self.statics.call_function('GetNumPlayerStates',self.world)))];systems=[s for s in systems if valid(s)]
            before=[int(s.call_function('GetGameplayEffectCount',effect,None,False)) for s in systems];require(all(n==0 for n in before),'damage fixture requires no preexisting mode immunity effects')
            initial=int(asc.call_function('GetGameplayEffectCount',effect,None,False))
            c=self.component(profile);c.call_function('SetDamageEnabled',False);applied=int(asc.call_function('GetGameplayEffectCount',effect,None,False));c.call_function('SetDamageEnabled',True);removed=int(asc.call_function('GetGameplayEffectCount',effect,None,False))
            for system in systems:system.call_function('RemoveActiveGameplayEffectBySourceEffect',effect,None,-1)
            restored=[int(s.call_function('GetGameplayEffectCount',effect,None,False)) for s in systems]==before
            self.report['damage_cases'].append(dict(profile=profile,initial_count=initial,after_apply=applied,after_remove=removed,fixture_effects_restored=restored))
    def cue_trials(self):
        cls=ue.load_class('/ShooterCore/GameplayCues/GCNL_WaitingForPlayers.GCNL_WaitingForPlayers_C');tag=cls.get_cdo().get_property('GameplayCueTag')
        for profile in PROFILES:
            c=self.component(profile);c.call_function('ActivateUserFacingCue',tag,policy.params());stored=str(c.get_property('ActiveUserFacingCue').TagName);found=[a for a in self.world.all_actors() if valid(a) and a.is_a(cls) and a.call_function('GetOwner')==self.state]
            c.call_function('ClearUserFacingCue');self.report['cue_cases'].append(dict(profile=profile,stored_tag=stored,actual_manager_actors=len(found),cleared=not policy.lib('BlueprintGameplayTagLibrary').call_function('IsGameplayTagValid',c.get_property('ActiveUserFacingCue'))))
    def unit(self,index):
        controller=self.world.actor_spawn(ue.find_class('LyraPlayerController'));state=controller.get_property('PlayerState');self.actors.extend((controller,state));manager=ue.new_object(ue.find_class('CheatManager'),controller);cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager);cheats.call_function('SetTeam',index+1);return dict(controller=controller,state=state,manager=manager,cheats=cheats)
    def message_trials(self):
        self.units=[self.unit(0),self.unit(1)];router=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'));self.sender=ue.load_class('/Game/UEPValidation/BP_MusicListenerProbe.BP_MusicListenerProbe_C').get_cdo();self.sender_root=not self.sender.is_rooted()
        if self.sender_root:self.sender.add_to_root()
        for profile in PROFILES:
            for winner in (1,2):
                self.set_scores((4,4));ue.set_mixin_profile(self.real,profile);self.real.call_function(policy.SET_TARGET,5);before=len(self.winners);a=self.units[winner-1]['state'];b=self.units[2-winner]['state'];kills=int(a.call_function('GetStatTagStackCount',policy.base.tag('ShooterGame.Score.Eliminations')));deaths=int(b.call_function('GetStatTagStackCount',policy.base.tag('ShooterGame.Score.Deaths')))
                self.sender.call_function('BroadcastVerb',router,policy.base.tag('Lyra.Elimination.Message'),LyraVerbMessage(Instigator=a,Target=b));events=[team for c,team in self.winners[before:] if c==self.real]
                self.report['message_cases'].append(dict(profile=profile,winner=winner,actual_winners=events,team_scores=self.team_scores()));a.call_function('RemoveStatTagStack',policy.base.tag('ShooterGame.Score.Eliminations'),int(a.call_function('GetStatTagStackCount',policy.base.tag('ShooterGame.Score.Eliminations')))-kills);b.call_function('RemoveStatTagStack',policy.base.tag('ShooterGame.Score.Deaths'),int(b.call_function('GetStatTagStackCount',policy.base.tag('ShooterGame.Score.Deaths')))-deaths)
        self.set_scores(self.score_before);self.real.call_function(policy.SET_TARGET,self.real_target);ue.set_mixin_profile(self.real,self.real_profile)
        for unit in self.units:
            for key in ('controller','state'):
                if not dead(unit[key]):unit[key].actor_destroy()
        self.units=[]
    def start_countdown(self):
        self.profile,self.a,self.b,self.expected=COUNTDOWN_CASES[self.index];self.set_scores((self.a,self.b));self.current=self.component(self.profile);self.notifications=[];self.bind(self.current,'CountDownUpdate',lambda value:self.notifications.append(float(value)))
        self.current.call_function(policy.SET_TIME,1.);self.winner_start=len(self.winners);self.start=time.monotonic();self.current.call_function(policy.TIMER);self.enter('countdown')
    def countdown(self):
        events=[team for c,team in self.winners[self.winner_start:] if c==self.current]
        if not events:require(time.monotonic()-self.start<5.,'original native countdown timer did not fire');return
        handle=self.current.get_property('TimerCountdown');active=bool(policy.lib('KismetSystemLibrary').call_function('K2_IsTimerActiveHandle',self.current,handle));valid_handle=bool(policy.lib('KismetSystemLibrary').call_function('K2_IsValidTimerHandle',handle))
        self.report['countdown_cases'].append(dict(profile=self.profile,scores=[self.a,self.b],expected=self.expected,winners=events,notifications=self.notifications[:],time=float(self.current.get_property('CountDownTime')),timer_active=active,handle_valid=valid_handle,gate_entries=count(self.current,'CountDown'),cached_scores=[int(self.current.get_property(n)) for n in ('Team0Score','Team1Score')]))
        self.index+=1
        if self.index<len(COUNTDOWN_CASES):self.start_countdown()
        else:
            self.set_scores(self.score_before);self.restart_trials();self.suppress=False;ue.set_mixin_profile(self.real,'Python');self.real.call_function('HandleVictory',2);self.enter('victory')
    def restart_trials(self):
        before=path(self.controller.get_controlled_pawn());rows=[]
        for profile in PROFILES:
            c=self.component(profile);c.call_function('RestartAllPlayers');rows.append(dict(profile=profile,pawn_still_valid=valid(self.controller.get_controlled_pawn()),entries=count(c,'Restart')))
        self.report['restart_cases']=rows;self.report['pawn_before_restart']=before
    def victory(self):
        subsystem=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraGamePhaseSubsystem'));phase=ue.load_class('/ShooterCore/Experiences/Phases/Phase_PostGame.Phase_PostGame_C').get_cdo().get_property('GamePhaseTag')
        if not subsystem.call_function('IsPhaseActive',phase):require(time.monotonic()-self.phase_started<10.,'actual native PostGame phase did not start');return
        cue_cls=ue.load_class('/ShooterCore/GameplayCues/GCNL_MatchDecided.GCNL_MatchDecided_C');cues=[a for a in self.world.all_actors() if valid(a) and a.is_a(cue_cls) and a.call_function('GetOwner')==self.state]
        self.report['actual_victory']=dict(winning_team=int(self.real.get_property('WinningTeamId')),phase_active=True,cue_tag=str(self.real.get_property('ActiveUserFacingCue').TagName),manager_cue_count=len(cues),python_victory_entries=policy.evidence(self.real)['python_Victory']);self.finish()
    def cleanup(self):
        for c,event,fn in self.bindings:
            if valid(c):c.unbind_event(event,fn)
        for c in self.components:
            if valid(c):c.call_function(policy.CLEAR_TIMER);c.remove_from_root();c.call_function('K2_DestroyComponent',self.state)
        for actor in self.actors:
            if not dead(actor):actor.actor_destroy()
        if hasattr(self,'score_before'):self.set_scores(self.score_before)
        if hasattr(self,'sources'):
            for p,source in self.sources.items():ue.register_mixin_profile(self.cls,p,source)
        if hasattr(self,'real') and valid(self.real):ue.clear_mixin_profile(self.real)
        if getattr(self,'sender_root',False) and valid(self.sender):self.sender.remove_from_root();self.sender_root=False
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),owned_components_destroyed=all(not valid(c) for c in self.components),diagnostic_sender_root_removed=not getattr(self,'sender_root',False),native_scores_restored=hasattr(self,'score_before') and self.team_scores()==self.score_before,
            production_profiles_restored=hasattr(self,'sources') and any(r['target_class']==self.cls and all(r['profiles'][p]['python_class'] is source and len(r['profiles'][p]['functions'])==16 for p,source in self.sources.items()) for r in ue.get_registered_mixins()))
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native TDM total timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='countdown':self.countdown()
            elif self.phase=='victory':self.victory()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_TDM_SCORING_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_TDM_SCORING_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPTDMScoringResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
