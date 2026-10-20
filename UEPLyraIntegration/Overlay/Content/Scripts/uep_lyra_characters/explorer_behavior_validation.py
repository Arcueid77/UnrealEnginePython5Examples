"""Real constructor labels, native component destruction/BT and late async payloads."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from .explorer_input_validation import Validation as Initialization
from .health_changed_observation import OwnedAI
from .explorer_init_late import LateCase
from .explorer_init_mixin import evidence as init_evidence
from . import explorer_behavior_mixin as policy
from .explorer_behavior_contract import FALSE_FIELDS,require,validate

def path(obj):return obj.get_path_name() if valid(obj) else None
def brain(controller):return controller.get_property('BrainComponent')

class BehaviorLateCase(LateCase):
    def spawn(self):
        super().spawn();self.state_tree=self.actor.get_property('StateTree');require(valid(self.state_tree),'late Pawn StateTree missing before behavior');self.actor.set_property('UseBhvTree',True);self.actor.set_property('BhvTree',self.validation.bt_asset);self.row['native_behavior_tree_seen_running']=False
    def close(self):
        if self.closed:return
        if valid(self.actor):
            self.row.update(latest_controller_argument_matches=self.actor.get_property(policy.CONTROLLER)==self.owner.controller,state_tree_destroyed_after_grant=not valid(self.state_tree),behavior_counts=copy.deepcopy(policy.evidence(self.actor)))
        super().close()

class Validation(Initialization):
    def __init__(self,result):
        super().__init__(result);self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerBehaviorProfile=')),'Python');self.report=dict(status='running',error=None,profile=self.profile,characters=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.behavior_bot=None;self.behavior_bot_cleanup=None;self.behavior_late=None
    def start_matrix(self):
        if self.kind=='hero':
            before=len(lib('LyraSystemStatics').call_function('FindComponentsByClass',self.subject,ue.find_class('ActorComponent'),True));self.subject.call_function('AnimMotionEffect',Bone='None',MotionEffect=GameplayTag(),StaticMeshComponent=self.subject.get_property('Mesh'),LocationOffset=ue.FVector(),RotationOffset=ue.FRotator(),AnimationSequence=None,bHitSuccess=False,HitResult=ue.find_struct('HitResult')(),Contexts=GameplayTagContainer(),VFXScale=ue.FVector(1.,1.,1.),AudioVolume=1.,AudioPitch=1.)
            self.report['hero_empty_motion_override_and_parent_constructor_retained']=self.subject.find_function('AnimMotionEffect').get_class().get_name()!='PythonFunction' and self.subject.find_function('UserConstructionScript').get_class().get_name()!='PythonFunction' and len(lib('LyraSystemStatics').call_function('FindComponentsByClass',self.subject,ue.find_class('ActorComponent'),True))==before;self.remove_character();return
        self.report['pawn']=dict(late_behavior=[]);counts=policy.evidence(self.subject);self.report['pawn']['natural_false_constructor_label_and_parent']=str(self.subject.get_property('TextRender').get_property('Text'))=='StateTree' and counts['python_construction']+counts['fallback_construction']>=1 and (self.profile=='BlueprintFallback' or counts['trace'][-2:]==['state-label','parent'])
        controller_payload=self.subject.get_property(policy.CONTROLLER);init=init_evidence(self.subject);self.report['pawn']['natural_possession_grant_behavior_controller_order']=controller_payload==self.owner and init['python_possessed']+init['fallback_possessed']>=1 and counts['python_behavior']+counts['fallback_behavior']>=1
        self.behavior_bot=OwnedAI(self.world);self.enter('behavior-bot')
    def observe(self):
        self.silence_owned_ui();require(time.monotonic()-self.phase_started<45.,'Explorer behavior phase timeout: '+self.phase)
        if self.phase=='startup':super().observe()
        elif self.phase=='behavior-bot':
            if not self.behavior_bot.ready():return
            self.bt_asset=self.behavior_bot.controller.get_property('BTAsset');require(valid(self.bt_asset),'native real BehaviorTree fixture asset missing');self.exercise_behavior();self.late_index=0;self.start_behavior_late()
        elif self.phase=='behavior-late':
            if self.behavior_late.actor is not None and valid(self.behavior_late.actor) and self.behavior_late.phase=='released':
                value=brain(self.behavior_late.owner.controller)
                if valid(value) and value.call_function('IsRunning'):self.behavior_late.row['native_behavior_tree_seen_running']=True;value.call_function('StopLogic','UEP owned late behavior observation')
            if self.behavior_late.step():
                self.report['pawn']['late_behavior'].append(copy.deepcopy(self.behavior_late.row));self.behavior_late=None;self.late_index+=1
                if self.late_index<2:self.start_behavior_late()
                else:self.remove_character()
    def exercise_behavior(self):
        row=self.report['pawn'];controller=self.behavior_bot.controller;value=brain(controller)
        if valid(value):value.call_function('StopLogic','UEP owned behavior matrix')
        component=self.subject.get_property('StateTree');require(valid(component),'original Pawn StateTree component missing');self.subject.set_property('UseBhvTree',False);self.subject.call_function('UseBehaviorTree',controller);row['false_behavior_keeps_state_tree_and_stopped_brain']=valid(component) and not brain(controller).call_function('IsRunning')
        self.subject.set_property('UseBhvTree',True);self.subject.set_property('BhvTree',self.bt_asset);self.subject.call_function('UseBehaviorTree',controller);row['true_behavior_destroys_state_tree_and_uses_input_ai_controller']=not valid(component) and self.subject.call_function('GetController')==self.owner and brain(controller).call_function('IsRunning');brain(controller).call_function('StopLogic','UEP owned behavior matrix complete')
        self.subject.call_function('UseBehaviorTree',None);row['native_nil_controller_path_preserved']=not valid(component) and not brain(controller).call_function('IsRunning')
        cls=self.classes['pawn'];cdo=cls.get_cdo();old=cdo.get_property('UseBhvTree')
        try:cdo.set_property('UseBhvTree',True);extra=self.world.actor_spawn(cls,ue.FVector(200000.,200000.,2000.))
        finally:cdo.set_property('UseBhvTree',old)
        self.owned.append(extra);extra.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);counts=policy.evidence(extra);row['natural_true_constructor_label_and_parent']=str(extra.get_property('TextRender').get_property('Text'))=='BhvTree' and counts['python_construction']+counts['fallback_construction']>=1 and (self.profile=='BlueprintFallback' or counts['trace'][-2:]==['behavior-label','parent'])
    def start_behavior_late(self):
        scenario=('controller',0,False,False) if self.late_index==0 else ('switch-pending',0,True,False);self.behavior_late=BehaviorLateCase(self,scenario);self.enter('behavior-late')
    def remove_character(self):
        if self.behavior_bot is not None:self.behavior_bot_cleanup=self.behavior_bot.close();self.behavior_bot=None
        self.subject.call_function('ClearInventory');self.statics.call_function('RemovePlayer',self.owner,True);self.owner=None;self.subject=None;self.index+=1
        if self.index<2:self.spawn_character()
        else:self.finish()
    def cleanup(self):
        if self.behavior_late is not None:self.behavior_late.close();self.behavior_late=None
        if self.behavior_bot is not None:self.behavior_bot_cleanup=self.behavior_bot.close();self.behavior_bot=None
        self.report['owned_behavior_bot_closed']=self.behavior_bot_cleanup is not None and self.behavior_bot_cleanup['owned_pawn_controller_playerstate_producer_destroyed'] and self.behavior_bot_cleanup['original_bot_producer_list_preserved'];super().cleanup()
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_BEHAVIOR_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_BEHAVIOR_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerBehaviorResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
