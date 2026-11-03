"""Opt-in native exception, benchmark and sustained gameplay validation."""
import atexit
import copy
import gc
from pathlib import Path
import statistics
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from . import global_policy,rule_policies,tag_stack_costs

MARKER='UEP_EXPECTED_HARDENING_EXCEPTION'

def arg(name,default=None):return next((a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'=')),default)
def require(value,message):
    if not value:raise AssertionError(message)
def paths(values):return sorted(v.get_path_name() for v in values if valid(v))
def flatten(base):return {k:v for p in reversed(base.__mro__) for k,v in vars(p).items() if not k.startswith('__')}

class Validation:
    def __init__(self):
        self.path=Path(arg('UEPHardeningResult'));self.mode=arg('UEPHardeningMode','Exceptions');self.started=time.monotonic();self.phase='ready';self.finished=False;self.owned=[];self.registrations=[]
        self.statics=ue.find_class('GameplayStatics').get_cdo();self.fixture=ue.find_class('UEPNativeRuleFixture').get_cdo();self.cls=ue.load_class(global_policy.CLASS)
        self.report=dict(status='running',error=None,mode=self.mode,physical_input_tested=False,cpp_compile_executed=False,expected_exception_marker=MARKER,cases=[],samples=[])
        self.last_write=0.
        atomic_write(self.path,self.report)
    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
            bridge=ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot')
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
            self.world=world;self.controller=self.statics.call_function('GetPlayerController',world,0);self.pawn=self.controller.get_controlled_pawn();self.state=self.controller.PlayerState
            isolate_bots(self.statics,world,ue.find_class('AIController'))
            self.host=ue.find_class('UEPNativeGameplayPolicySubsystem').get_cdo().call_function('GetPolicyForContext',world);self.original_profile=str(ue.get_mixin_profile(self.host))
            self.mode_started=time.monotonic()
            getattr(self,'start_'+self.mode.lower())();return
    def add_profile(self,cls,name,methods):
        profile=type(name,(),dict(methods,__module__=__name__));ue.register_mixin_profile(cls,name,profile);self.registrations.append(cls);return name
    def invoke_expected(self,call):
        try:return call()
        except Exception as e:
            require(MARKER in str(e),'unexpected propagated exception: '+str(e));return None
    def start_exceptions(self):
        self.teams=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'))
        base=rule_policies.PawnPython
        def UEPApplyPolicy(owner,context):
            if str(context.Operation)=='Damage.CanCause':
                owner._hardening_calls=getattr(owner,'_hardening_calls',0)+1
                context.set_property('bAllowed',True)
                raise RuntimeError(MARKER+'_DAMAGE')
            return base.UEPApplyPolicy(owner,context)
        name=self.add_profile(self.cls,'HardeningDamageFault',dict(flatten(base),UEPApplyPolicy=UEPApplyPolicy))
        for index in range(3):
            ue.set_mixin_profile(self.host,'Python');require(bool(self.fixture.call_function('DamageAllowed',self.teams,self.pawn,self.pawn,True)),'native self-damage admission baseline missing')
            ue.set_mixin_profile(self.host,name);before=getattr(self.host,'_hardening_calls',0)
            answer=self.invoke_expected(lambda:self.fixture.call_function('DamageAllowed',self.teams,self.pawn,self.pawn,True))
            require(not answer and getattr(self.host,'_hardening_calls',0)==before+1,'exception replayed original damage admission or invoked policy twice')
            ue.set_mixin_profile(self.host,'Python');require(bool(self.fixture.call_function('DamageAllowed',self.teams,self.pawn,self.pawn,True)),'damage policy did not recover')
            self.report['cases'].append(dict(kind='native_damage_policy',index=index,failed_result=False,callbacks=1,recovered=True))
        self.test_cost_exceptions();self.start_reset_exceptions()
    def test_cost_exceptions(self):
        parent=ue.load_class(tag_stack_costs.OWNERS[0][0]);base=tag_stack_costs.WeaponCostPythonProfile
        asc=ability_system(self.pawn)
        specs=[s for s in asc.get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.is_a(parent)]
        candidates=[(s,a) for s in specs for a in list(s.NonReplicatedInstances)+list(s.ReplicatedInstances) if valid(a)]
        require(len(candidates)==1,'one naturally granted active weapon ability required')
        spec,ability=candidates[0];original_profile=str(ue.get_mixin_profile(ability))
        quickbar=self.controller.get_component_by_type(ue.find_class('LyraQuickBarComponent'))
        item=quickbar.call_function('GetActiveSlotItem');require(valid(item),'original equipped item missing')
        tag=GameplayTag(TagName='Lyra.ShooterGame.Weapon.MagazineAmmo');available=int(item.call_function('GetStatTagStackCount',tag));require(available>0,'native equipped magazine must be nonempty')
        for operation in ('check','apply'):
            methods=flatten(base)
            if operation=='check':
                def UEPCheckTagStackCost(owner,context):
                    owner._hardening_cost_calls=getattr(owner,'_hardening_cost_calls',0)+1;raise RuntimeError(MARKER+'_COST_CHECK')
                methods['UEPCheckTagStackCost']=UEPCheckTagStackCost
            else:
                def UEPApplyTagStackCost(owner,context):
                    owner._hardening_cost_calls=getattr(owner,'_hardening_cost_calls',0)+1;raise RuntimeError(MARKER+'_COST_APPLY')
                methods['UEPApplyTagStackCost']=UEPApplyTagStackCost
            name=self.add_profile(parent,'HardeningCost'+operation.title(),methods)
            for index in range(3):
                # Create is deliberately editor-only. Probe can observe the
                # actual game's existing ActorInfo/spec/item without spawning
                # replacement owners or granting any artificial ability.
                case=ue.new_object(ue.find_class('UEPNativeCostCase'));self.owned.append(case);case.add_to_root()
                for field,value in dict(Controller=self.controller,PlayerState=self.state,Pawn=self.pawn,AbilitySystem=asc,Item=item,Ability=ability,Handle=spec.Handle).items():case.set_property(field,value)
                try:
                    ue.set_mixin_profile(ability,name);before_calls=getattr(ability,'_hardening_cost_calls',0)
                    result=self.invoke_expected(lambda:case.call_function('Probe',True,operation=='apply',True,False,False))
                    require(result is not None and int(result.Before)==int(result.After)==available,'faulted native cost mutated the item or replayed native payment')
                    require(getattr(ability,'_hardening_cost_calls',0)==before_calls+1,'cost exception invoked more than once')
                    if operation=='check':require(not result.bCanPay,'faulted check admitted native cost')
                    ue.set_mixin_profile(ability,'Python');recovered=case.call_function('Probe',True,True,True,False,False)
                    require(recovered.bCanPay and int(recovered.Before)==available and int(recovered.After)==available-1,'cost policy recovery did not pay exactly once')
                    self.report['cases'].append(dict(kind='native_item_cost_'+operation,index=index,before=available,after_fault=available,after_recovery=available-1,callbacks=1,recovered=True,original_equipped_ability=True))
                finally:
                    ue.set_mixin_profile(ability,original_profile)
                    current=int(item.call_function('GetStatTagStackCount',tag))
                    if current!=available:item.call_function('AddStatTagStack' if current<available else 'RemoveStatTagStack',tag,abs(available-current))
                    require(int(item.call_function('GetStatTagStackCount',tag))==available,'original native magazine was not restored')
                    case.remove_from_root();self.owned.remove(case)
    def cleanup(self):
        for scope in getattr(self,'hardening_scopes',[]):scope.close()
        self.report['subscriptions_closed']=all(s.closed and s.count==0 for s in getattr(self,'hardening_scopes',[]))
        if hasattr(self,'host') and valid(self.host):ue.set_mixin_profile(self.host,self.original_profile)
        for cls in set(self.registrations):
            ue.unregister_mixin(cls);ue.register_declared_mixin(cls)
        self.report['declarations_restored']=all(not any(str(n).startswith('Hardening') for n in r['profiles']) for r in ue.get_registered_mixins() if r['target_class'] in set(self.registrations))
        self.report['owned_cases_released']=not self.owned
        self.report['selector_restored']=not hasattr(self,'host') or (valid(self.host) and str(ue.get_mixin_profile(self.host))==self.original_profile)
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error,elapsed_seconds=time.monotonic()-self.started);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_HARDENING_'+('FAILED '+error if error else 'READY'));ue.request_exit()
    def tick(self,delta):
        if self.finished:return False
        try:
            limit=float(arg('UEPHardeningDuration','1200'))+300. if self.mode=='Soak' else 300.
            require(time.monotonic()-self.started<limit,'hardening startup/runtime timeout: '+self.phase)
            if self.phase=='ready':self.ready()
            elif self.phase=='soak':self.soak_step()
            elif self.phase=='exceptions-reset':self.exception_reset_step()
            if time.monotonic()-self.last_write>=1.:atomic_write(self.path,self.report);self.last_write=time.monotonic()
            return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            self.report['status']='passed'
            try:
                from .hardening_validation_contract import validate
                validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HARDENING_SHUTDOWN_'+self.report['status'].upper())

from .hardening_activity import install
install(Validation,arg)
from .hardening_exception_cases import install as install_extra
install_extra(Validation)
validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
