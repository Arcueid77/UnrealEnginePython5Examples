"""Native local-player input injection -> original receiver -> GAS -> equipment."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_abilities.auto_respawn_helpers_validation import instances
from uep_lyra_abilities.quickslot_mixin import CLASS as ABILITY
from .explorer_init_validation import Validation as Initialization
from .enhanced_input_contract import ACTIONS,CASES
from .quickbar_input_contract import DEFINITIONS
from .enhanced_input_validation import fill_slots
from . import enhanced_input_mixin as input_policy,quickbar_input_mixin as helper_policy
from .explorer_input_mixin import bindings
from .team_observer_observation import proxies
from .explorer_input_contract import FALSE_FIELDS,require,validate

def path(obj):return obj.get_path_name() if valid(obj) else None

class Validation(Initialization):
    def __init__(self,result):
        super().__init__(result);self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerInputProfile=')),'Python');self.report=dict(status='running',error=None,profile=self.profile,characters=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.trial_scope=None;self.observer=None;self.input=None;self.action=None;self.original_proxy_objects={}
    def begin(self):
        super().begin()
        if self.original_proxies is not None and not self.original_proxy_objects:
            active=proxies();self.original_proxy_objects={name:active[name] for name in self.original_proxies if name in active}
    def tasks(self):return sum(valid(t) and t.is_a(ue.find_class('AbilityTask_WaitGameplayEvent')) for t in self.quick_ability.get_property('ActiveTasks'))
    def start_matrix(self):
        self.subject.call_function('ClearInventory');self.subject.set_property('InitialInventoryItems',[ue.load_class(d) for d in DEFINITIONS]);self.probe.call_function('Grant',self.subject);self.prepared_slots=list(self.quick.call_function('GetSlots'));self.inventory_ids=sorted(path(v) for v in self.inventory.call_function('GetAllItems'))
        found=instances(self.asc,ue.load_class(ABILITY));require(len(found)==1,'unique original native Quickslot ability required');self.quick_ability=found[0];require(self.quick_ability.get_property('bIsActive') and self.tasks()==3,'natural Quickslot ability/native wait tasks missing')
        self.input=lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubsystem',self.owner,ue.find_class('EnhancedInputLocalPlayerSubsystem'));require(valid(self.input),'native owned EnhancedInput subsystem missing');names=bindings(self.subject.get_class());row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.subject.get_class()];self.row.update(native_receiver_names=names,native_profile_method_counts={p:len(v['functions']) for p,v in row['profiles'].items()},input_cases=[]);self.case_index=0;self.start_input()
    def start_input(self):
        self.spec=CASES[self.case_index];name,action,initial,expected,empty=self.spec;fill_slots(self.quick,self.prepared_slots);self.quick.call_function('SetActiveSlotIndex',initial)
        if empty is not None:self.quick.call_function('RemoveItemFromSlot',empty)
        self.events=[];self.before=dict(input_policy.evidence(self.subject));self.helper_before=dict(helper_policy.evidence(self.subject));self.tasks_before=self.tasks();require(self.tasks_before==3,'native Quickslot wait task count changed before injection')
        tag=ACTIONS[action][3];self.observer=lib('AbilityAsync_WaitGameplayEvent').call_function('WaitGameplayEventToActor',self.subject,GameplayTag(TagName=tag),False,True);self.trial_scope=SubscriptionScope()
        def received(payload):self.events.append(dict(tag=str(payload.EventTag.TagName),magnitude=float(payload.EventMagnitude),instigator_null=payload.Instigator is None,target_null=payload.Target is None,optional_objects_null=payload.OptionalObject is None and payload.OptionalObject2 is None))
        self.trial_scope.bind_event(self.observer,'EventReceived',received);self.observer.call_function('Activate');asset=ACTIONS[action][0];self.action=ue.load_object(ue.find_class('InputAction'),'/ShooterCore/Input/Actions/'+asset+'.'+asset);self.input.call_function('InjectInputVectorForAction',self.action,ue.FVector(1.,0.,0.));self.released=False;self.enter('input')
    def observe(self):
        self.silence_owned_ui()
        if self.phase=='startup':super().observe();return
        if self.phase!='input':return
        if not self.released:self.input.call_function('InjectInputVectorForAction',self.action,ue.FVector(0.,0.,0.));self.released=True
        counts={k:v-self.before[k] for k,v in input_policy.evidence(self.subject).items()};nested={k:v-self.helper_before[k] for k,v in helper_policy.evidence(self.subject).items()};entries=nested['python_calls']+nested['fallback_calls'];require(entries<=1,'native Triggered input repeated unexpectedly');model=capture(self.owner)
        if entries!=1 or model is None or model['active']!=self.spec[3] or time.monotonic()-self.phase_started<.3:
            require(time.monotonic()-self.phase_started<8.,'native Explorer input/equipment timeout: '+repr((self.spec,counts,nested,model)));return
        self.close_trial();name,action,initial,expected,empty=self.spec;self.row['input_cases'].append(dict(name=name,action=action,initial=initial,empty_slot=empty,positive_native_injections=1,native_input_subsystem_used=True,native_bound_receiver=self.row['native_receiver_names'][action],receiver_is_native_router=self.subject.find_function(self.row['native_receiver_names'][action]).get_class().get_name()=='PythonFunction',input_counters=counts,helper_counters=nested,inventory=copy.deepcopy(model),events=copy.deepcopy(self.events),native_tasks_before=self.tasks_before,native_tasks_after=self.tasks(),inventory_items_unchanged=sorted(path(v) for v in self.inventory.call_function('GetAllItems'))==self.inventory_ids,task_scope_closed=self.trial_scope is None,no_repeated_or_release_handler=entries==1));self.case_index+=1
        if self.case_index<len(CASES):self.start_input()
        else:self.finish_character()
    def close_trial(self):
        if valid(self.observer):self.observer.call_function('EndAction')
        if self.trial_scope is not None:self.trial_scope.close();self.trial_scope=None
        self.observer=None
    def finish_character(self):
        self.subject.call_function('ClearInventory');self.statics.call_function('RemovePlayer',self.owner,True);self.owner=None;self.subject=None;self.index+=1
        if self.index<2:self.spawn_character()
        else:self.finish()
    def cleanup(self):
        if valid(self.input) and valid(self.action):self.input.call_function('InjectInputVectorForAction',self.action,ue.FVector(0.,0.,0.))
        self.close_trial();super().cleanup()
        if self.original_proxies is not None:
            missing=self.original_proxies-set(proxies());witnessed={row['observer'] for row in self.report.get('original_pooled_observer_retirement_witnesses',[]) if all(row[n] for n in ('same_native_cue_handle','inactive','unrooted','cue_hidden','owner_cleared'))};recycled=[]
            for cue in ue.tobject_iterator(ue.load_class('/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C')):
                if not valid(cue):continue
                current=cue.get_property('TeamColorWatcherHandle')
                for old,cue_path in self.original_pooled.items():
                    if old not in missing or old in witnessed or cue.get_path_name()!=cue_path or not valid(current) or path(current)==old:continue
                    previous=self.original_proxy_objects.get(old);old_released=not valid(previous) or path(previous)!=old;old_inactive=old_released or (not previous.call_function('IsActive') and not previous.is_rooted())
                    row=dict(observer=old,cue=cue_path,new_observer=path(current),native_cue_identity_preserved=True,native_cue_field_never_written=True,old_observer_released_or_inactive_unrooted=old_inactive,new_observer_inactive=not current.call_function('IsActive'),new_observer_unrooted=not current.is_rooted(),cue_hidden=bool(cue.get_property('bHidden')),owner_cleared=not valid(cue.call_function('GetOwner')));recycled.append(row)
                    if all(row[n] for n in ('native_cue_identity_preserved','native_cue_field_never_written','old_observer_released_or_inactive_unrooted','new_observer_inactive','new_observer_unrooted','cue_hidden','owner_cleared')):witnessed.add(old)
            diagnostic=self.report['proxy_cleanup_diagnostics'];self.report['original_pooled_observer_recycling_witnesses']=recycled;self.report['owned_native_proxies_and_observers_closed']=self.scope.count==0 and not diagnostic['explicit_active'] and not diagnostic['owned_active'] and missing==witnessed
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_INPUT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_INPUT_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerInputResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
