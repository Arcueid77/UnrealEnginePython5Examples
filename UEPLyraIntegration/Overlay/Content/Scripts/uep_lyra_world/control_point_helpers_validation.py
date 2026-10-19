"""Natural volume construction, actual Niagara and CP scoring helper calls."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead,vector
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_weapons.cp_scoring_mixin import CLASS as SCORING
from . import control_point_helpers_mixin as policy
from .control_point_helpers_contract import PLAN,require,validate,close


def path(value):return value.get_path_name() if valid(value) else None
def count(a,n):return sum(policy.evidence(a)[p+'_'+n] for p in ('python','fallback'))


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,pairs=[],helper_cases=[]);self.sources={};self.volumes=[];self.index=0
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','construction_replayed','overlap_replayed','timeline_callbacks_replayed','remaining_volume_business_migrated','health_properties_written'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];self.sources={p:r['python_class'] for p,r in row['profiles'].items()}
        self.game_state=self.statics.call_function('GetGameState',self.world);self.scoring=self.game_state.get_component_by_type(ue.load_class(SCORING));require(valid(self.scoring),'actual CP scoring component absent')
        initial=[a for a in self.world.all_actors() if valid(a) and a.is_a(self.cls)];self.report['natural_map_volumes']=len(initial);self.report['natural_map_python_construction']=sum(policy.evidence(a)['python_Construct'] for a in initial)
        self.original_points=list(self.scoring.get_property('ControlPoints'));self.original_owners=list(self.scoring.get_property('ControlPointOwnerTeams'));self.start_pair()
    def value(self,component,name,method):
        fields=native_outputs('NiagaraComponent',method,component.call_function(method,name));require(fields['bIsValid'],'actual Niagara override absent: '+name);return fields['ReturnValue']
    def spawn(self,profile,area,duration):
        transform=ue.FTransform();transform.translation=ue.FVector(250000.+self.index*10000.,250000.,3000.)
        actor=self.statics.call_function('BeginDeferredActorSpawnFromClass',self.world,self.cls,transform,1,None);self.actors.append(actor);self.volumes.append(actor);ue.set_mixin_profile(actor,profile)
        actor.set_property('AreaScale',policy.lib('KismetMathLibrary').call_function('MakeVector',*area));actor.set_property('TimeRequiredForCapture',duration);actor.call_function('SetActorEnableCollision',False);self.statics.call_function('FinishSpawningActor',actor,transform);actor.call_function('SetActorTickEnabled',False);return actor
    def state(self,a):
        cube=a.get_property('Cube');fx=a.get_property('NS_CapturePoint');counter=a.get_property('NS_CapturePointCounter');offset=self.value(fx,'SidesOffset','GetVariableVec4')
        return dict(scale=vector(cube.get_property('RelativeScale3D')),location=vector(cube.get_property('RelativeLocation')),offset=[float(getattr(offset,n)) for n in ('x','y','z','w')],ribbon=float(self.value(counter,'RibbonProgression','GetVariableFloat')),lifetime=float(self.value(counter,'LifeTime','GetVariableFloat')))
    def start_pair(self):
        self.area,self.duration=PLAN[self.index];self.current=[self.spawn(p,self.area,self.duration) for p in ('BlueprintFallback','Python')];states=[self.state(a) for a in self.current]
        self.row=dict(area=self.area,duration=self.duration,constructor_entries=[count(a,'Construct') for a in self.current],initial_states=states,paired_native_state_matches=close(states[0],states[1]));self.report['pending_pair']=self.row;self.started_pair=time.monotonic()
        for a in self.current:
            counter=a.get_property('NS_CapturePointCounter');counter.call_function('SetAllowScalability',False);counter.call_function('SetForceSolo',True);counter.call_function('Deactivate')
        self.row['fixture_niagara_scalability_disabled_and_solo']=True
        self.enter('inactive')
    def inactive(self):
        if any(a.get_property('NS_CapturePointCounter').call_function('IsActive') for a in self.current):require(time.monotonic()-self.phase_started<10.,'native counter did not deactivate/drain');return
        observations=[]
        for a in self.current:
            counter=a.get_property('NS_CapturePointCounter');before=bool(counter.call_function('IsActive'));a.call_function('CheckTimerNS');first=bool(counter.call_function('IsActive'));a.call_function('CheckTimerNS');second=bool(counter.call_function('IsActive'));counter.call_function('Activate',True);direct=bool(counter.call_function('IsActive'))
            observations.append(dict(before=before,after_first=first,after_second=second,after_direct_native=direct,registered=bool(counter.component_is_registered()),system=path(counter.get_property('Asset')),selected_profile=str(ue.get_mixin_profile(a)),helper_evidence=dict(policy.evidence(a))))
        self.row['counter_activation_observations']=observations;self.row['counter_check_entries']=[count(a,'CheckCounter') for a in self.current]
        self.row['counter_active_after_two_checks']=all(x['after_second'] for x in observations)
        for a in self.current:
            a.set_property('ControlPointGameMode',self.scoring);points=list(self.scoring.get_property('ControlPoints'));require(a in points,'source natural BeginPlay did not register owned volume');index=points.index(a)
            a.set_property('OwnerTeamID',2);a.call_function('MarkThisPointRecaptured');recaptured=int(self.scoring.get_property('ControlPointOwnerTeams')[index]);a.call_function('MarkThisPointContested');contested=int(self.scoring.get_property('ControlPointOwnerTeams')[index])
            self.report['helper_cases'].append(dict(profile=str(ue.get_mixin_profile(a)),recaptured=recaptured,contested=contested,recapture_entries=count(a,'Recapture'),contest_entries=count(a,'Contest')))
        self.report['pairs'].append(self.row)
        for a in self.current:
            counter=a.get_property('NS_CapturePointCounter');counter.call_function('Deactivate');ue.clear_mixin_profile(a);a.actor_destroy()
        self.scoring.set_property('ControlPoints',self.original_points);self.scoring.set_property('ControlPointOwnerTeams',self.original_owners);self.index+=1
        if self.index<len(PLAN):self.start_pair()
        else:self.finish()
    def cleanup(self):
        for a in self.actors:
            if not dead(a):ue.clear_mixin_profile(a);a.actor_destroy()
        if hasattr(self,'scoring') and valid(self.scoring):self.scoring.set_property('ControlPoints',self.original_points);self.scoring.set_property('ControlPointOwnerTeams',self.original_owners)
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),scoring_arrays_restored=hasattr(self,'scoring') and list(self.scoring.get_property('ControlPoints'))==self.original_points and list(self.scoring.get_property('ControlPointOwnerTeams'))==self.original_owners,original_health_unchanged=self.healths()==self.health_before,
            production_profiles_restored=any(r['target_class']==self.cls and all(r['profiles'][p]['python_class'] is source and len(r['profiles'][p]['functions'])==4 for p,source in self.sources.items()) for r in ue.get_registered_mixins()))
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native control point helper total timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='inactive':self.inactive()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_CONTROL_POINT_HELPERS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_CONTROL_POINT_HELPERS_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPControlPointHelpersResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
