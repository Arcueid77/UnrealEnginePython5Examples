"""Actual named listener callbacks, native team changes and deferred readiness."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .explorer_helpers_validation import Validation as Helpers
from .team_observer_observation import proxies,query
from . import explorer_init_mixin as policy,team_cosmetics_mixin as team_policy
from .explorer_helpers_mixin import evidence as grants
from .explorer_init_late import LateCase,SCENARIOS
from .inventory_wait_transitions import end_owned_respawn
from .explorer_init_contract import require,validate,FALSE_FIELDS

def path(obj):return obj.get_path_name() if valid(obj) else None
def observed(actor):return sum(policy.evidence(actor)[n] for n in ('python_observed','fallback_observed'))
def normalized(payload):return dict(team_set=payload['assigned'],team_id=payload['team'],display_asset=payload['display'])

class Validation(Helpers):
    def __init__(self,result):
        super().__init__(result);self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerInitProfile=')),'Python');self.report=dict(status='running',error=None,profile=self.profile,characters=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.scope=SubscriptionScope();self.explicit_proxies=[];self.late=None;self.original_proxies=None;self.original_pooled={};self.raw=[[],[]]
    def begin(self):
        phases=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraGamePhaseSubsystem'))
        if not valid(phases) or not phases.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.Playing')):return
        asc=ability_system(self.pawn)
        if not valid(asc) or asc.get_property('AvatarActor')!=self.pawn:return
        if self.original_proxies is None:
            self.original_proxies=set(proxies())
            for cue in ue.tobject_iterator(ue.load_class('/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C')):
                if valid(cue):
                    handle=cue.get_property('TeamColorWatcherHandle')
                    if path(handle) in self.original_proxies:self.original_pooled[path(handle)]=path(cue)
        super().begin()
    def start_matrix(self):
        counts=policy.evidence(self.subject);self.row['natural_possession_factory_and_grant']=counts['python_possessed']+counts['fallback_possessed']>=1 and sum(grants(self.subject)[n] for n in ('python_grants','fallback_grants'))>=1;self.row['resolved_callbacks']={k:policy.resolve(self.subject.get_class(),k) for k in ('team','experience')};self.row['named_actor_specific_callbacks_resolved']=all(self.subject.get_class().get_path_name()==ue.describe_function(self.subject.get_class(),name)['owner'] for name in self.row['resolved_callbacks'].values())
        self.current=[];before_observed=observed(self.subject);native_query=query(self.subject)
        for index in range(2):
            before=set(proxies());self.subject.call_function('ListenForTeam');added=[p for name,p in proxies().items() if name not in before];require(len(added)==1,'original ListenForTeam did not produce one distinct native proxy');self.current.extend(added);self.explicit_proxies.extend(added)
            def received(assigned,team,display,index=index):self.raw[index].append(dict(team_set=bool(assigned),team_id=int(team),display_asset=path(display)))
            self.scope.bind_event(added[0],'OnTeamChanged',received)
        self.row['two_listeners_create_two_native_proxies']=len(self.current)==2 and self.current[0]!=self.current[1] and all(p.call_function('IsActive') for p in self.current);self.row['initial_callbacks_match_native_team']=observed(self.subject)-before_observed==2 and normalized(policy.evidence(self.subject)['last_team'])==native_query
        self.original_team=native_query['team_id'];end_owned_respawn(self.subject);self.change_observed_before=observed(self.subject);self.owner.call_function('UnPossess');self.changed_query=query(self.subject)
        require(self.raw[0] and self.raw[1] and self.raw[0][-1]==self.raw[1][-1]==self.changed_query and self.changed_query['team_set'] is False,'native unpossession did not deliver actual no-team state')
        self.changed_delta=observed(self.subject)-self.change_observed_before;self.current[0].call_function('Cancel');self.raw_counts=[len(v) for v in self.raw];self.cancel_observed_before=observed(self.subject);self.owner.call_function('Possess',self.subject);restored=query(self.subject)
        restored_deliveries=len(self.raw[1])-self.raw_counts[1]
        self.row['native_team_change_and_cancel_isolation']=restored['team_id']==self.original_team and len(self.raw[0])==self.raw_counts[0] and restored_deliveries>=1 and self.raw[1][-1]==restored and observed(self.subject)-self.cancel_observed_before==(self.changed_delta-1)*restored_deliveries
        self.row['native_repossession_notifications']=copy.deepcopy(self.raw[1][self.raw_counts[1]:])
        self.row['team_cancel_diagnostics']=dict(original_team=self.original_team,changed_query=self.changed_query,restored_query=restored,raw_counts_before_cancel=self.raw_counts,raw_counts_after_restore=[len(v) for v in self.raw],latest_payloads=[v[-1] if v else None for v in self.raw],changed_observed_delta=self.changed_delta,restored_observed_delta=observed(self.subject)-self.cancel_observed_before)
        require(self.row['native_team_change_and_cancel_isolation'],'native team restoration/cancellation relation differs')
        self.row['native_team_change_producer']='UnPossess/Possess';self.current[1].call_function('Cancel');require(all(not p.call_function('IsActive') for p in self.current),'native explicit listener cancellation failed')
        bare=self.world.actor_spawn(self.classes[self.kind],ue.FVector(200000.,200000.,2000.));self.owned.append(bare);bare.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);ue.set_mixin_profile(bare,self.profile);before=set(proxies());seen=observed(bare);team_before=sum(team_policy.evidence(bare)[n] for n in ('python_calls','fallback_calls'));bare.call_function('ListenForTeam');created=[p for name,p in proxies().items() if name not in before];self.explicit_proxies.extend(created);self.row['native_no_team_callback_is_noop']=len(created)==1 and observed(bare)-seen==1 and policy.evidence(bare)['last_team']['assigned'] is False and sum(team_policy.evidence(bare)[n] for n in ('python_calls','fallback_calls'))==team_before
        for p in created:p.call_function('Cancel')
        self.row['readiness']=[];self.late_index=0;self.start_late()
    def start_late(self):self.late=LateCase(self,SCENARIOS[self.late_index]);self.enter('late')
    def observe(self):
        self.silence_owned_ui()
        if self.phase=='startup':
            asc=ability_system(self.subject)
            if valid(asc) and asc.get_property('AvatarActor')==self.subject:super().observe()
        elif self.phase=='late':
            if self.late.step():
                self.row['readiness'].append(copy.deepcopy(self.late.row));self.late=None;self.late_index+=1
                if self.late_index<len(SCENARIOS):self.start_late()
                else:self.finish_character()
    def finish_character(self):
        self.subject.call_function('ClearInventory');self.statics.call_function('RemovePlayer',self.owner,True);self.owner=None;self.subject=None;self.index+=1;self.raw=[[],[]]
        if self.index<2:super().spawn_character()
        else:self.finish()
    def cleanup(self):
        if self.late is not None:self.late.close();self.late=None
        self.scope.close()
        # Original pre-fixture actors keep their observers; pooled native Cue fields
        # are never rewritten. Only new fixture-era, non-pooled proxies are cancelled.
        if self.original_proxies is not None:
            pooled={path(cue.get_property('TeamColorWatcherHandle')) for cue in ue.tobject_iterator(ue.load_class('/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C')) if valid(cue)}
            owned=[p for name,p in proxies().items() if name not in self.original_proxies and name not in pooled]
            for p in self.explicit_proxies+owned:
                if valid(p) and p.call_function('IsActive'):p.call_function('Cancel')
            self.report['proxy_cleanup_diagnostics']=dict(scope_count=self.scope.count,original_missing=sorted(self.original_proxies-set(proxies())),explicit_active=[path(p) for p in self.explicit_proxies if valid(p) and p.call_function('IsActive')],owned_active=[path(p) for p in owned if valid(p) and p.call_function('IsActive')],pooled_paths=sorted(p for p in pooled if p is not None))
            missing=self.original_proxies-set(proxies());pooled_witnesses=[]
            for cue in ue.tobject_iterator(ue.load_class('/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C')):
                if not valid(cue):continue
                handle=cue.get_property('TeamColorWatcherHandle');key=path(handle)
                if key in missing and self.original_pooled.get(key)==path(cue):
                    pooled_witnesses.append(dict(observer=key,cue=path(cue),same_native_cue_handle=True,inactive=not handle.call_function('IsActive'),unrooted=not handle.is_rooted(),cue_hidden=bool(cue.get_property('bHidden')),owner_cleared=not valid(cue.call_function('GetOwner'))))
            natural_retired={row['observer'] for row in pooled_witnesses if all(row[n] for n in ('same_native_cue_handle','inactive','unrooted','cue_hidden','owner_cleared'))};self.report['original_pooled_observer_retirement_witnesses']=pooled_witnesses
            self.report['owned_native_proxies_and_observers_closed']=self.scope.count==0 and all(not valid(p) or not p.call_function('IsActive') for p in self.explicit_proxies+owned) and missing==natural_retired
        super().cleanup()
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<420.,'Explorer initialization timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_INIT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_INIT_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerInitResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
