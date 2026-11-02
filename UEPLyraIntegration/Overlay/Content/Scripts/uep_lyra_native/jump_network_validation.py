"""Reused real native Jump input harness; only new C++ rule profiles change."""
import atexit
import copy
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities import jump_network_validation as original
from uep_lyra_abilities import jump_mixin as previous
from . import ability_lifecycle as policy
from .jump_network_contract import client as client_gate,require

ORDER=('NativeLifecycleFallback','Python')


class Client(original.Client):
    def __init__(self,*args):
        super().__init__(*args);self.profile_order=ORDER;self.report.update(previous_blueprint_policy_fixed='Python',admission_boundaries=[])
    def begin(self):
        if self.index==0 and not self.report['admission_boundaries']:
            fixture=ue.find_class('UEPNativeLifecycleFixture').get_cdo()
            for profile in ORDER:
                ue.set_mixin_profile(self.ability,profile)
                for name,info,avatar in (('null_info',False,True),('null_avatar',True,False),('valid',True,True)):
                    value=bool(fixture.call_function('ProbeJumpAdmission',self.ability,info,avatar));self.report['admission_boundaries'].append(dict(profile=profile,case=name,result=value));require(value==(name=='valid'),'native Jump admission failed: '+name)
        self.native_before=copy.deepcopy(policy.metrics(self.ability));super().begin()
    def record_trial(self,row,counts):
        m=policy.metrics(self.ability);row['native_lifecycle_counts']={k:m[k]-self.native_before[k] for k in m if k!='trace'};super().record_trial(row,counts)
    def finalize(self):
        self.report['policy_shutdown']=previous.snapshot()
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';client_gate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_JUMP_NETWORK_SHUTDOWN_'+self.report['status'].upper())


class Server(original.Server):
    def __init__(self,*args):super().__init__(*args);self.profile_order=ORDER;self.report['previous_blueprint_policy_fixed']='Python'
    def finalize(self):
        self.report['policy_shutdown']=previous.snapshot()
        if self.report['status']=='awaiting_shutdown':
            try:
                m=self.report['policy_shutdown'];require(len(self.report['cases'])==28 and self.report['server_waited_for_client_process_exit'] and m['activations']==m['scopes_created']==m['scopes_closed']==28 and not m['active_count'] and not m['errors'],'native authority Jump completion failed');self.report['status']='passed'
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_JUMP_NETWORK_SHUTDOWN_'+self.report['status'].upper())


path,peer,run=original.arg('-UEPJumpNetworkResult='),original.arg('-UEPJumpPeer='),original.arg('-UEPJumpRun=')
validation=Server(path,run) if peer=='server' else Client(path,peer,run);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
