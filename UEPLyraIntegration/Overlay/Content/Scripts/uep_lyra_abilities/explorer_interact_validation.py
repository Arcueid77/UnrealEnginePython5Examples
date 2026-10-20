"""Real native collectable trace/nearby grant/GAS input/target event and task end."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_characters.explorer_helpers_validation import Validation as Helpers
from .auto_respawn_helpers_validation import instances
from . import explorer_interact_mixin as policy
from .explorer_interact_contract import FALSE_FIELDS,require,validate

TASKS=dict(scan='AbilityTask_WaitForInteractableTargets_SingleLineTrace',wait='AbilityTask_WaitInputPress',nearby='AbilityTask_GrantNearbyInteraction',release='AbilityTask_WaitInputRelease')
def path(obj):return obj.get_path_name() if valid(obj) else None
def total(a,name):return sum(policy.evidence(a)[p+'_'+name] for p in ('python','fallback'))
class Validation(Ready):
    silence_owned_ui=Helpers.silence_owned_ui
    cancel_owned_abilities=Helpers.cancel_owned_abilities
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.owner=None;self.subject=None;self.ability=None;self.target=None;self.state=None;self.roots=[];self.index=0;self.selector=None
    def task_objects(self):return list(self.ability.get_property('ActiveTasks'))
    def task_counts(self):return {k:sum(valid(t) and t.is_a(ue.find_class(cls)) for t in self.task_objects()) for k,cls in TASKS.items()}
    def options(self):return len(self.ability.get_property('CurrentOptions'))
    def move(self,offset):self.target.call_function('K2_SetActorLocation',NewLocation=ue.FVector(200000.+offset,200000.,2025.),bSweep=False,bTeleport=True)
    def input(self):self.asc.call_function('ServerSetInputPressed',self.handle)
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);self.target_cls=ue.load_class('/Game/UEPValidation/BP_ExplorerInteractTarget.BP_ExplorerInteractTarget_C');self.witness_cls=ue.load_class('/Game/UEPValidation/BP_ExplorerInteractWitnessAbility.BP_ExplorerInteractWitnessAbility_C');self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(self.cls)
        for cls in (self.cls,self.target_cls,self.witness_cls):
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
        self.start_case()
    def start_case(self):
        self.profile=('BlueprintFallback','Python')[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.owner=self.statics.call_function('CreatePlayer',self.world,-1,True);require(valid(self.owner) and self.owner!=self.controller,'owned native local player missing');self.silence_owned_ui();self.subject=self.owner.get_controlled_pawn();self.state=self.owner.get_property('PlayerState');require(valid(self.subject),'owned native player pawn missing');self.subject.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);self.subject.call_function('K2_SetActorLocation',NewLocation=ue.FVector(200000.,200000.,2000.),bSweep=False,bTeleport=True);self.owner.call_function('SetControlRotation',ue.FRotator());self.owner.call_function('SetViewTargetWithBlend',self.subject,0.,0,0.,False);self.case=dict(profile=self.profile,end_cancelled_values=[]);self.report['cases'].append(self.case);self.enter('owned-ready')
    def observe(self):
        self.silence_owned_ui();require(time.monotonic()-self.phase_started<25.,'Explorer Interact phase timeout: '+self.phase)
        if self.phase=='owned-ready':
            asc=ability_system(self.subject)
            if not valid(asc) or asc.get_property('AvatarActor')!=self.subject:return
            if any(spec.ActiveCount and valid(spec.Ability) and spec.Ability.get_class().get_name()=='GA_SpawnEffect_C' for spec in asc.get_property('ActivatableAbilities').Items):self.cancel_owned_abilities(asc,True);return
            self.asc=asc;self.target=self.world.actor_spawn(self.target_cls);box=self.target.add_actor_root_component(ue.find_class('BoxComponent'),'UEPInteractionCollision');box.call_function('SetBoxExtent',ue.FVector(45.,65.,80.),True);box.call_function('SetCollisionProfileName','Interactable_BlockDynamic',True);box.call_function('SetCollisionEnabled',1);self.target.set_property('Option',ue.find_struct('InteractionOption')(InteractionAbilityToGrant=self.witness_cls));self.move(150.);self.handle=self.asc.call_function('K2_GiveAbility',self.cls,1,-1);self.enter('active')
        elif self.phase=='active':
            found=instances(self.asc,self.cls)
            if len(found)!=1 or not found[0].get_property('bIsActive'):return
            self.ability=found[0];ue.set_mixin_profile(self.ability,self.profile)
            if self.options()!=1:return
            counts=self.task_counts();require(counts==dict(scan=1,wait=1,nearby=1,release=0),'native interaction task family missing or duplicated');self.case['active_task_counts']=counts;self.case['native_onspawn_gas_activation']=total(self.ability,'activate')==1 and policy.evidence(self.ability)[self.profile.lower().replace('blueprintfallback','fallback')+'_activate']==1
            scan,=[t for t in self.task_objects() if t.is_a(ue.find_class(TASKS['scan']))];query=scan.get_property('InteractionQuery');location=scan.get_property('StartLocation');self.case['original_scan_query_and_avatar_location_preserved']=query.RequestingAvatar==self.subject and query.RequestingController is None and location.SourceActor==self.subject;self.case['native_parent_nearby_task_granted_target_ability']=any(valid(spec.Ability) and spec.Ability.get_class()==self.witness_cls for spec in self.asc.get_property('ActivatableAbilities').Items);self.case['native_trace_found_real_collectable']=total(self.ability,'options')>=1;self.input();self.enter('first-press')
        elif self.phase=='first-press':
            if int(self.target.get_property('TriggerCount'))!=1:return
            event=self.target.get_property('LastEvent');self.case.update(native_input_press_activated_target_event=total(self.ability,'press')==1,target_event_tag=str(event.EventTag.TagName),target_event_instigator_and_target_match=event.Instigator==self.subject and event.Target==self.target,native_press_rearmed_one_wait_without_duplicate_scan=self.task_counts()==dict(scan=1,wait=1,nearby=1,release=0));self.move(350.);self.enter('out-of-range')
        elif self.phase=='out-of-range':
            if self.options()!=0:return
            self.case['native_target_out_of_range_cleared_options']=total(self.ability,'options')>=2;self.input();self.no_options_count=int(self.target.get_property('TriggerCount'));self.enter('empty-press')
        elif self.phase=='empty-press':
            if time.monotonic()-self.phase_started<.15:return
            self.case['native_press_with_no_options_did_not_trigger_target']=total(self.ability,'press')==2 and int(self.target.get_property('TriggerCount'))==self.no_options_count==1;self.move(150.);self.enter('return-target')
        elif self.phase=='return-target':
            if self.options()!=1:return
            self.switched='Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback';ue.set_mixin_profile(self.ability,self.switched);self.input();self.enter('switched-press')
        elif self.phase=='switched-press':
            if int(self.target.get_property('TriggerCount'))!=2:return
            prefix='python' if self.switched=='Python' else 'fallback';self.case['pending_profile_switch_used_current_callback']=policy.evidence(self.ability)[prefix+'_press']==1 and total(self.ability,'press')==3;self.case['native_target_trigger_count']=int(self.target.get_property('TriggerCount'));self.ability.call_function('K2_CancelAbility');self.case['end_cancelled_values'].append(policy.evidence(self.ability)['last_cancelled']);self.ended=copy.deepcopy(policy.evidence(self.ability));self.move(350.);self.enter('cancelled')
        elif self.phase=='cancelled':
            if time.monotonic()-self.phase_started<.25:return
            self.case['native_cancel_stopped_all_tasks_without_late_callbacks']=not self.ability.get_property('bIsActive') and not self.task_objects() and policy.evidence(self.ability)==self.ended;self.move(150.);require(self.asc.call_function('TryActivateAbilityByClass',self.cls,False),'native reactivation failed');self.enter('reactivated')
        elif self.phase=='reactivated':
            if not self.ability.get_property('bIsActive') or self.task_counts()!=dict(scan=1,wait=1,nearby=1,release=0):return
            self.ability.call_function('K2_EndAbility');self.case['end_cancelled_values'].append(policy.evidence(self.ability)['last_cancelled']);self.ended=copy.deepcopy(policy.evidence(self.ability));self.enter('normal-ended')
        elif self.phase=='normal-ended':
            if time.monotonic()-self.phase_started<.25:return
            self.case['native_reactivation_and_normal_end_stopped_all_tasks']=total(self.ability,'activate')==2 and not self.ability.get_property('bIsActive') and not self.task_objects() and policy.evidence(self.ability)==self.ended;self.close_context();self.case['owned_player_pawn_state_target_destroyed']=all(not valid(v) for v in (self.owner,self.subject,self.state,self.target));self.index+=1
            if self.index<2:self.start_case()
            else:self.finish()
    def close_context(self):
        if valid(self.ability):
            if self.ability.get_property('bIsActive'):self.ability.call_function('K2_CancelAbility')
            ue.clear_mixin_profile(self.ability)
        if valid(self.target):self.target.actor_destroy()
        if valid(self.owner):self.statics.call_function('RemovePlayer',self.owner,True)
        for actor in (self.subject,self.state):
            if valid(actor):actor.actor_destroy()
    def cleanup(self):
        self.close_context()
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        for cls in self.roots:cls.remove_from_root()
        self.report['class_selectors_roots_and_owned_contexts_restored']=all(not cls.is_rooted() for cls in self.roots) and self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector and all(not valid(v) for v in (self.owner,self.subject,self.state,self.target));self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'Explorer Interact readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_INTERACT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_INTERACT_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerInteractResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
