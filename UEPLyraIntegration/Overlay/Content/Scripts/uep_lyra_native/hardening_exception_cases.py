"""Native reward settlement and GAS Reset failure/continuation witnesses."""
import time
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData,LyraVerbMessage
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from . import message_processors,rule_policies

MARKER='UEP_EXPECTED_HARDENING_EXCEPTION'

def flatten(base):return {k:v for p in reversed(base.__mro__) for k,v in vars(p).items() if not k.startswith('__')}

def test_settlement_exception(self):
    cls=ue.load_class(message_processors.CLASSES['streak']);components=[]
    for obj in ue.tobject_iterator(cls):
        if not valid(obj) or obj.get_name().startswith('Default__'):continue
        try:same=obj.get_world()==self.world
        except Exception:continue
        if same:components.append(obj)
    self.require(len(components)==1,'one actual original streak processor required');component=components[0]
    tags={int(k):GameplayTag(TagName=str(v.TagName)) for k,v in component.get_property('ElimStreakTags').items()};self.require(bool(tags),'original reward tag table missing')
    tag=next(iter(tags.values()));scope=SubscriptionScope();self.hardening_scopes=[scope];events=[]
    scope.listen_gameplay_signal(self.world,str(tag.TagName),lambda channel:events.append(str(channel.TagName)))
    old_profile=str(ue.get_mixin_profile(component));history=dict(message_processors.state(component))
    targets=[p for p in ue.tobject_iterator(ue.find_class('LyraPlayerState')) if valid(p) and p!=self.state and not p.get_name().startswith('Default__')]
    self.require(bool(targets),'native reward target PlayerState missing')
    payload=LyraVerbMessage(Verb=GameplayTag(TagName='Lyra.Elimination.Message'),Instigator=self.state,Target=targets[0])
    base=message_processors.StreakPythonProfile
    def UEPHandleElimination(owner,Channel,Payload):
        owner._hardening_settlements=getattr(owner,'_hardening_settlements',0)+1
        base.UEPHandleElimination(owner,Channel,Payload)
        raise RuntimeError(MARKER+'_SETTLEMENT')
    name=self.add_profile(cls,'HardeningSettlementFault',dict(flatten(base),UEPHandleElimination=UEPHandleElimination))
    try:
        component.set_property('ElimStreakTags',{1:tag});ue.set_mixin_profile(component,'Python');message_processors.state(component).clear()
        component.call_function('UEPHandleElimination',payload.Verb,payload)
        self.report['settlement_diagnostics']=dict(baseline_events=list(events),baseline_broadcasts=message_processors.metrics(component)['broadcasts'],threshold_keys=list(component.get_property('ElimStreakTags')),channel=str(tag.TagName),written_channels=[str(v.TagName) for v in component.get_property('ElimStreakTags').values()],instigator=self.state.get_path_name(),target=targets[0].get_path_name())
        self.require(len(events)==1,'native reward observation baseline differs: '+str(self.report['settlement_diagnostics']))
        events.clear();ue.set_mixin_profile(component,name);message_processors.state(component).clear()
        before=getattr(component,'_hardening_settlements',0)
        self.invoke_expected(lambda:component.call_function('UEPHandleElimination',payload.Verb,payload))
        self.report['settlement_diagnostics'].update(fault_events=list(events),fault_callbacks=getattr(component,'_hardening_settlements',0)-before)
        self.require(len(events)==1 and getattr(component,'_hardening_settlements',0)==before+1,'faulted reward settlement differs: '+str(self.report['settlement_diagnostics']))
        ue.set_mixin_profile(component,'Python');message_processors.state(component).clear();component.call_function('UEPHandleElimination',payload.Verb,payload)
        self.require(len(events)==2,'reward callback did not recover exactly once')
        scope.close();self.require(scope.closed and scope.count==0,'native reward observer did not close')
        message_processors.state(component).clear();component.call_function('UEPHandleElimination',payload.Verb,payload)
        self.require(len(events)==2,'closed native reward listener received a later settlement')
        self.report['cases'].append(dict(kind='native_reward_settlement',callbacks=1,after_fault=1,after_recovery=2,closed_scope_ignores_later_native_broadcast=True,recovered=True,callback_payload_supplied_by_fixture=True))
    finally:
        scope.close();component.set_property('ElimStreakTags',tags);ue.set_mixin_profile(component,old_profile);message_processors.state(component).clear();message_processors.state(component).update(history)

def start_reset_exceptions(self):
    base=rule_policies.PawnPython
    def UEPApplyPolicy(owner,context):
        if str(context.Operation)=='Reset.Activate':
            owner._hardening_resets=getattr(owner,'_hardening_resets',0)+1
            context.set_property('Actions',['ResetCharacter','BroadcastReset'])
            raise RuntimeError(MARKER+'_RESET')
        return base.UEPApplyPolicy(owner,context)
    self.reset_fault_profile=self.add_profile(self.cls,'HardeningResetFault',dict(flatten(base),UEPApplyPolicy=UEPApplyPolicy))
    self.reset_case_index=0;self.phase='exceptions-reset';self.begin_reset_exception()

def reset_instance(self):
    asc=ability_system(self.controller.get_controlled_pawn());cls=ue.find_class('LyraGameplayAbility_Reset')
    instances=[a for s in asc.get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.is_a(cls) for a in list(s.NonReplicatedInstances)+list(s.ReplicatedInstances) if valid(a)]
    self.require(len(instances)==1,'one original native Reset instance required');return instances[0]

def send_reset(self):
    tag=GameplayTag(TagName='GameplayEvent.RequestReset')
    ue.find_class('AbilitySystemBlueprintLibrary').get_cdo().call_function('SendGameplayEventToActor',self.state,tag,GameplayEventData(EventTag=tag,Instigator=self.state,Target=self.state))

def begin_reset_exception(self):
    old=self.controller.get_controlled_pawn();ability=reset_instance(self);self.require(not ability.get_property('bIsActive'),'native Reset was already active')
    ue.set_mixin_profile(self.host,self.reset_fault_profile);before=getattr(self.host,'_hardening_resets',0)
    self.invoke_expected(lambda:send_reset(self))
    self.require(not ability.get_property('bIsActive') and self.controller.get_controlled_pawn()==old,'faulted Reset left an active ability or reset its Pawn')
    self.require(getattr(self.host,'_hardening_resets',0)==before+1,'native Reset fault invoked twice')
    self.reset_old=old.get_path_name();ue.set_mixin_profile(self.host,'Python');send_reset(self);self.reset_since=time.monotonic()

def exception_reset_step(self):
    self.require(time.monotonic()-self.reset_since<15.,'Reset recovery did not spawn a new Pawn')
    pawn=self.controller.get_controlled_pawn()
    if not valid(pawn) or pawn.get_path_name()==self.reset_old or not valid(ability_system(pawn)):return
    self.require(self.controller.PlayerState==self.state and not reset_instance(self).get_property('bIsActive'),'Reset recovery changed owner or left native ability active')
    self.report['cases'].append(dict(kind='native_reset_abort',index=self.reset_case_index,callbacks=1,failed_plan_did_not_reset_pawn=True,native_ability_ended_on_fault=True,recovered=True,old_pawn=self.reset_old,new_pawn=pawn.get_path_name()))
    self.reset_case_index+=1;self.pawn=pawn
    if self.reset_case_index==3:self.test_settlement_exception();self.finish()
    else:begin_reset_exception(self)

def install(cls):
    cls.test_settlement_exception=test_settlement_exception;cls.start_reset_exceptions=start_reset_exceptions;cls.exception_reset_step=exception_reset_step;cls.begin_reset_exception=begin_reset_exception
