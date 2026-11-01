"""Live native scan/indicator/interface customization/GAS input comparison."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.explorer_interact_validation import Validation as Legacy,TASKS
from uep_lyra_abilities.auto_respawn_helpers_validation import instances
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture
from . import interactions as policy
from .interaction_validation_contract import require,validate

INPUT=7128
ICON='/Game/UEPValidation/W_NativeInteractionIndicator.W_NativeInteractionIndicator_C'


class Validation(Legacy):
    def __init__(self,result):
        super().__init__(result);self.second=None
        self.report=dict(status='running',error=None,cases=[],synthetic_target_events=False,native_interface_replaced=False,native_scan_task_replaced=False,network_acceptance=False,visible_rendering_acceptance=False)

    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls)
        self.target_cls=ue.find_class('UEPNativeInteractionFixture');self.witness_cls=ue.find_class('UEPNativeInteractionWitness');self.selector=self.cls.get_cdo().get_property('PythonMixinProfile')
        for cls in (self.cls,self.target_cls,self.witness_cls):
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
        self.start_case()

    def start_case(self):
        self.ability=None
        self.profile=('NativeFallback','Python')[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.owner=self.statics.call_function('CreatePlayer',self.world,-1,True);require(valid(self.owner) and self.owner!=self.controller,'owned native local player missing');self.silence_owned_ui()
        self.subject=self.owner.get_controlled_pawn();self.state=self.owner.PlayerState;require(valid(self.subject),'owned native Pawn missing')
        self.subject.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0)
        self.subject.call_function('K2_SetActorLocation',NewLocation=ue.FVector(200000.,200000.,2000.),bSweep=False,bTeleport=True)
        self.owner.call_function('SetControlRotation',ue.FRotator());self.owner.call_function('SetViewTargetWithBlend',self.subject,0.,0,0.,False)
        self.case=dict(profile=self.profile);self.report['cases'].append(self.case);self.enter('owned-ready')

    def press(self):
        for pressed in (True,False):self.target_cls.get_cdo().call_function('UEPRouteInteractionInput',self.asc,self.handle,pressed)

    def check_payload(self):
        event=self.target.LastEvent
        return str(event.EventTag.TagName)=='Ability.Interaction.Activate' and event.Instigator==self.subject and event.Target==self.second and float(event.EventMagnitude)==37. and event.OptionalObject==self.target and self.target.SeenOwner==self.state and self.target.SeenAvatar==self.subject

    def matrix(self):
        original=self.ability.get_property('CurrentOptions')[0].clone();manager=self.ability.call_function('UEPGetInteractionIndicatorManager');require(valid(manager),'owned native indicator manager missing')
        previous=list(self.ability.get_property('Indicators'));external=set(manager.get_property('Indicators'))-set(previous)
        update=lambda values:self.ability.call_function('UpdateInteractions',values)
        update([]);self.ability.call_function('TriggerInteraction')
        result=dict(empty_options=len(self.ability.get_property('CurrentOptions'))==0 and not self.ability.get_property('Indicators') and set(manager.get_property('Indicators'))==external and int(self.target.TriggerCount)==0)
        default=original.clone();default.InteractionWidgetClass=None;update([default]);indicators=list(self.ability.get_property('Indicators'))
        result['default_widget']=len(indicators)==1 and self.ability.call_function('UEPInteractionIndicatorPath',indicators[0])==self.ability.call_function('UEPDefaultInteractionWidgetPath')
        result['native_indicator_target_and_root']=indicators[0].call_function('GetDataObject')==self.target and indicators[0].call_function('GetSceneComponent')==self.target.get_property('RootComponent')
        try:ue.find_object(ICON);unloaded=False
        except Exception as exc:
            if not str(exc).startswith('unable to find object '):raise
            unloaded=True
        specified=original.clone();specified.InteractionWidgetClass=ICON
        result['specified_unloaded_soft_class']=unloaded and self.ability.call_function('UEPHasInteractionWidget',specified)
        update([specified]);result['specified_widget']=self.ability.call_function('UEPInteractionIndicatorPath',self.ability.get_property('Indicators')[0])==ICON
        second=specified.clone();second.InteractableTarget=self.second;update([default,second]);indicators=list(self.ability.get_property('Indicators'))
        result['multiple_indicator_order']=[i.call_function('GetDataObject') for i in indicators]==[self.target,self.second] and set(manager.get_property('Indicators'))==external|set(indicators)
        self.ability.call_function('TriggerInteraction')
        self.case['native_event_diagnostics']=dict(trigger_count=int(self.target.TriggerCount),customize_count=int(self.target.CustomizeCount),other_count=int(self.second.TriggerCount),owner=str(self.target.SeenOwner),avatar=str(self.target.SeenAvatar),event_tag=str(self.target.LastEvent.EventTag.TagName),event_target=str(self.target.LastEvent.Target),event_magnitude=float(self.target.LastEvent.EventMagnitude))
        result['first_option_and_native_customized_payload']=int(self.target.TriggerCount)==int(self.target.CustomizeCount)==1 and int(self.second.TriggerCount)==0 and self.check_payload()
        require(all(result.values()),'native interaction matrix differs: '+str(result));self.case['matrix']=result;update([default]);self.press();self.enter('first-press')

    def observe(self):
        if valid(self.target):self.report['live_target_counts']=dict(trigger=int(self.target.TriggerCount),customize=int(self.target.CustomizeCount),options=self.options() if valid(self.ability) else None)
        self.silence_owned_ui();require(time.monotonic()-self.phase_started<25.,'native interaction phase timed out: '+self.phase)
        if self.phase=='owned-ready':
            asc=ability_system(self.subject)
            if not valid(asc) or asc.get_property('AvatarActor')!=self.subject:return
            if any(s.ActiveCount and valid(s.Ability) and s.Ability.get_class().get_name()=='GA_SpawnEffect_C' for s in asc.get_property('ActivatableAbilities').Items):self.cancel_owned_abilities(asc,True);return
            self.asc=asc;self.target=self.world.actor_spawn(self.target_cls);self.second=self.world.actor_spawn(self.target_cls);self.move(150.)
            self.second.call_function('K2_SetActorLocation',NewLocation=ue.FVector(200150.,200300.,2025.),bSweep=False,bTeleport=True)
            self.target.set_property('Retarget',self.second);self.target.set_property('bCustomizePayload',True)
            self.handle=asc.call_function('K2_GiveAbility',self.cls,1,INPUT);self.enter('active')
        elif self.phase=='active':
            found=instances(self.asc,self.cls)
            if len(found)!=1 or not found[0].get_property('bIsActive'):return
            self.ability=found[0];ue.set_mixin_profile(self.ability,self.profile)
            if self.options()!=1:return
            self.case['native_task_counts']=self.task_counts();require(self.task_counts()==dict(scan=1,wait=1,nearby=1,release=0),'native task family missing')
            self.matrix()
        elif self.phase=='first-press':
            if int(self.target.TriggerCount)!=2:return
            self.case['native_input_triggered']=self.check_payload();self.move(350.);self.enter('out-of-range')
        elif self.phase=='out-of-range':
            if self.options()!=0:return
            self.case['out_of_range_cleared']=not self.ability.get_property('Indicators');self.press();self.enter('empty-press')
        elif self.phase=='empty-press':
            if time.monotonic()-self.phase_started<.15:return
            self.case['empty_input_ignored']=int(self.target.TriggerCount)==2;self.move(150.);self.enter('return-target')
        elif self.phase=='return-target':
            if self.options()!=1:return
            self.switched='Python' if self.profile=='NativeFallback' else 'NativeFallback';ue.set_mixin_profile(self.ability,self.switched);self.press();self.enter('switched-press')
        elif self.phase=='switched-press':
            if int(self.target.TriggerCount)!=3:return
            other='python_' if self.switched=='Python' else 'native_';self.case['profile_switch_dispatched']=policy.metrics(self.ability)[other+'trigger']==1 and self.check_payload();ue.set_mixin_profile(self.ability,self.profile);self.move(350.);self.enter('clear-before-cancel')
        elif self.phase=='clear-before-cancel':
            if self.options()!=0:return
            self.ability.call_function('K2_CancelAbility');self.ended=copy.deepcopy(policy.metrics(self.ability));self.enter('cancelled')
        elif self.phase=='cancelled':
            if time.monotonic()-self.phase_started<.25:return
            self.case.update(cancel_stopped_tasks=not self.ability.get_property('bIsActive') and not self.task_objects() and policy.metrics(self.ability)==self.ended,metrics=copy.deepcopy(policy.metrics(self.ability)),trigger_count=int(self.target.TriggerCount),customize_count=int(self.target.CustomizeCount))
            self.close_context();self.case['owned_context_destroyed']=all(not valid(v) for v in (self.owner,self.subject,self.state,self.target,self.second));self.index+=1
            if self.index<2:self.start_case()
            else:self.finish()

    def close_context(self):
        super().close_context()
        if valid(self.second):self.second.actor_destroy()

    def cleanup(self):
        self.close_context()
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        for cls in self.roots:cls.remove_from_root()
        self.report['selectors_and_owned_roots_restored']=all(not cls.is_rooted() for cls in self.roots) and (self.selector is None or self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector)
        if hasattr(self,'player_before'):self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_NATIVE_INTERACTION_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_INTERACTION_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPNativeInteractionResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
