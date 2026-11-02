"""Original native Reset GAS event, owner messages and cancellation witnesses."""
import atexit
import copy
import sys
import unreal_engine as ue
from uep_lyra_abilities import auto_respawn_reset_network_validation as original
from . import global_policy

PLAN=('native-reset-live','native-reset-repeat','native-reset-pending-long')
ORDER=('NativeGameplayFallback','Python')
original.PLAN=PLAN;original.TRIALS=len(PLAN)*2;original.TOTAL=len(PLAN)*4


def host(value, index):
    if not hasattr(value,'policy_host'):
        value.policy_host=ue.find_class('UEPNativeGameplayPolicySubsystem').get_cdo().call_function('GetPolicyForContext',value.world)
        original.require(original.valid(value.policy_host),'world-owned Blueprint policy carrier missing')
        value.original_host_profile=str(ue.get_mixin_profile(value.policy_host))
    ue.set_mixin_profile(value.policy_host,ORDER[index%2])


def restore_host(value):
    if hasattr(value,'policy_host'):
        ue.set_mixin_profile(value.policy_host,value.original_host_profile)
        value.report['host_profile_restored']=str(ue.get_mixin_profile(value.policy_host))==value.original_host_profile


def counts(value):
    after=global_policy.metrics(value.policy_host)
    return {key:after[key]-value.host_before[key] for key in after if key!='trace'}


class Client(original.Client):
    def __init__(self,*args):
        super().__init__(*args);self.report['previous_blueprint_policy_fixed']='Python'

    def arm(self,command):
        host(self,command['index']);self.host_before=copy.deepcopy(global_policy.metrics(self.policy_host))
        super().arm(command)

    def complete_reset(self):
        self.row.update(native_policy=ORDER[self.index%2],native_policy_counts=counts(self))
        super().complete_reset()

    def finish(self,error=None):
        restore_host(self);super().finish(error)

    def finalize(self):
        super().finalize()
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_RESET_NETWORK_SHUTDOWN_'+self.report['status'].upper())


class Server(original.Server):
    def __init__(self,*args):
        super().__init__(*args);self.profile_order=('Python','Python');self.report.update(previous_blueprint_policy_fixed='Python',fixture_witness_abilities_granted=True)

    def prepare(self):
        super().prepare()
        if self.phase=='armed':host(self,self.index)

    def trigger_reset(self):
        self.host_before=copy.deepcopy(global_policy.metrics(self.policy_host))
        self.protection=ue.find_class('UEPNativeProtectionFixture').get_cdo();self.witness_asc=self.asc
        self.witnesses=[self.protection.call_function('GrantActive',self.asc,protected) for protected in (False,True)]
        original.require(all(self.protection.call_function('WitnessActive',self.asc,h) for h in self.witnesses),'Reset cancellation witnesses did not activate')
        reset_spec=next(s for s in self.asc.get_property('ActivatableAbilities').Items if original.valid(s.Ability) and s.Ability.get_class().get_path_name()=='/Script/LyraGame.LyraGameplayAbility_Reset')
        native_instances=[a for a in list(reset_spec.NonReplicatedInstances)+list(reset_spec.ReplicatedInstances) if original.valid(a)]
        original.require(len(native_instances)==1,'one original native Reset instance required')
        super().trigger_reset()
        self.row.update(native_policy=ORDER[self.index%2],native_policy_counts=counts(self),ordinary_cancelled=not bool(self.protection.call_function('WitnessActive',self.asc,self.witnesses[0])),protected_survived_reset=bool(self.protection.call_function('WitnessActive',self.asc,self.witnesses[1])),native_reset_inactive_after=not bool(native_instances[0].get_property('bIsActive')))

    def remove_witnesses(self):
        handles,self.witnesses=getattr(self,'witnesses',[]),[]
        return all([self.protection.call_function('RemoveWitness',self.witness_asc,h) for h in handles])

    def observe_reset(self):
        pawn=self.controller.get_controlled_pawn()
        if getattr(self,'witnesses',None) and original.valid(pawn) and pawn.get_path_name()!=self.old_pawn:
            self.row['protected_survived_respawn']=bool(self.protection.call_function('WitnessActive',self.witness_asc,self.witnesses[1]))
            self.row['witnesses_removed']=self.remove_witnesses()
        super().observe_reset()

    def finish(self,error=None):
        if getattr(self,'witnesses',None):self.remove_witnesses()
        restore_host(self);super().finish(error)

    def finalize(self):
        super().finalize()
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_RESET_NETWORK_SHUTDOWN_'+self.report['status'].upper())


if '-UEPNativePartsNetwork' not in sys.argv:
    result,peer,run=(original.arg(flag) for flag in ('-UEPAutoRespawnResetNetworkResult=','-UEPJumpPeer=','-UEPJumpRun='))
    validation=Server(result,run) if peer=='server' else Client(result,peer,run)
    atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
