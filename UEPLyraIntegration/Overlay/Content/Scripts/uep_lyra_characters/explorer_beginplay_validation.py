"""Real BeginPlay/Spawned delegates, native next-tick actions and owned teardown."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .explorer_init_validation import Validation as Initialization
from . import begin_play_mixin as beginning,visibility_mixin as visibility
from .explorer_beginplay_mixin import REQUIRED_STATE
from .explorer_beginplay_contract import FALSE_FIELDS,require,validate

def frame():return int(lib('KismetSystemLibrary').call_function('GetFrameCount'))
def entries(values):return values['python_calls']+values['fallback_calls']

class Validation(Initialization):
    def __init__(self,result):
        super().__init__(result);self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerBeginPlayProfile=')),'Python');self.report=dict(status='running',error=None,profile=self.profile,characters=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.destroyed_values=None;self.destroyed_snapshot=None
    def spawn_character(self):
        super().spawn_character();self.row.update(required_state=REQUIRED_STATE,static_parent='/Game/Characters/Character_Default.Character_Default_C',spawn_return_frame=frame(),hidden_at_spawn_return=bool(self.subject.get_property('bHidden')),visibility_cases=[]);self.natural_values=visibility.evidence(self.subject);self.first_shown_frame=None
    def start_matrix(self):
        begin=beginning.evidence(self.subject);traces=self.natural_values['trace'];received=[v for v in traces if v['event']=='received'];self.row['natural_begin_once']=begin['python_calls']+begin['fallback_calls']==1
        self.row['original_spawned_registration']=self.profile=='BlueprintFallback' or begin['order']==['parent','listen','hide','register']
        self.row['natural_next_frame_show']=self.row['hidden_at_spawn_return'] and received and self.first_shown_frame is not None and self.first_shown_frame>received[0]['frame'];self.row['natural_visibility_trace']=copy.deepcopy(traces);self.row['natural_first_shown_frame']=self.first_shown_frame;self.case_index=0;self.start_visibility()
    def start_visibility(self):
        self.case_name=('repeat','switch-pending','destroy-pending')[self.case_index];ue.set_mixin_profile(self.subject,self.profile);self.target=self.subject
        if self.case_name=='destroy-pending':
            self.target=self.world.actor_spawn(self.classes[self.kind],ue.FVector(200000.,200000.,2000.));ue.set_mixin_profile(self.target,self.profile);self.target.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0)
        self.target.call_function('SetActorHiddenInGame',True);values=visibility.evidence(self.target);self.before_entries=entries(values);self.case_frame=frame()
        for _ in range(2):self.target.call_function(visibility.REGISTER,self.target.get_property('PawnExtComponent'),GameplayTag(TagName=REQUIRED_STATE),True)
        self.case=dict(name=self.case_name,native_registration_called=True,not_shown_synchronously=bool(self.target.get_property('bHidden')),received_callbacks=entries(values)-self.before_entries,native_next_frame_show=False)
        if self.case_name=='switch-pending':ue.set_mixin_profile(self.target,'Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback')
        if self.case_name=='destroy-pending':
            self.destroyed_values=values;self.target.actor_destroy();self.target=None;self.destroyed_snapshot=copy.deepcopy(values);self.case['destroy_frame']=frame();self.enter('visibility-destroy')
        else:self.enter('visibility-wait')
    def observe(self):
        self.silence_owned_ui();require(time.monotonic()-self.phase_started<20.,'Explorer visibility phase timeout: '+self.phase)
        if self.phase=='startup':
            if not self.subject.get_property('bHidden') and self.first_shown_frame is None:self.first_shown_frame=frame()
            super().observe()
        elif self.phase=='visibility-wait':
            if self.subject.get_property('bHidden'):return
            self.case.update(native_next_frame_show=frame()>self.case_frame,shown_frame=frame(),visibility_trace=copy.deepcopy(visibility.evidence(self.subject)['trace']));self.complete_visibility()
        elif self.phase=='visibility-destroy':
            if frame()<self.case['destroy_frame']+3:return
            self.case['no_late_script_work_after_destroy']=self.destroyed_values==self.destroyed_snapshot;self.complete_visibility()
    def complete_visibility(self):
        self.row['visibility_cases'].append(self.case);self.case_index+=1
        if self.case_index<3:self.start_visibility();return
        self.subject.call_function('ClearInventory');self.statics.call_function('RemovePlayer',self.owner,True);self.owner=None;self.subject=None;self.index+=1
        if self.index<2:self.spawn_character()
        else:self.finish()
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_BEGINPLAY_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_BEGINPLAY_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerBeginPlayResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
