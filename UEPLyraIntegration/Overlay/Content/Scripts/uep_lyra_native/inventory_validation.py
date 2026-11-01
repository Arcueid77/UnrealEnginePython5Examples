"""Actual native inventory/pickup and quickbar boundary differential."""
import atexit
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import services,capture
from .message_validation import arg
from . import inventory as policy
from .inventory_validation_helpers import grant,entries,fingerprint,DEFINITIONS
from .inventory_validation_contract import require,validate


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeInventoryResult'));self.profile=arg('UEPNativeInventoryProfile');self.started=time.monotonic();self.finished=False;self.controller=None;self.original=None;self.boot=[]
        self.report=dict(status='running',error=None,profile=self.profile,cases=[],fixture_only_slot_array_writes=True,native_rpc_bypassed=False,native_inventory_replication_replaced=False,existing_instance_grant_runtime_tested=False)
        for target in (policy.QUICK,policy.INVENTORY):
            cls=ue.load_class(target);ue.register_declared_mixin(cls);self.boot.append((cls,cls.get_cdo().get_property('PythonMixinProfile')));cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        atexit.register(self.finalize)

    def setup(self):
        lib=ue.find_class('GameplayStatics').get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
            controller=lib.call_function('GetPlayerController',world,0)
            if capture(controller) is None:continue
            self.world=world;self.controller=controller;self.inventory,self.quickbar=services(controller)
            require(self.inventory.get_class().get_path_name()==policy.INVENTORY and self.quickbar.get_class().get_path_name()==policy.QUICK,'natural production inventory/quickbar classes differ')
            require(str(ue.get_mixin_profile(self.inventory))==str(ue.get_mixin_profile(self.quickbar))==self.profile,'natural policy selectors differ')
            isolate_bots(lib,world,ue.find_class('AIController'));self.original=fingerprint(controller);self.original_slots=list(self.quickbar.call_function('GetSlots'));self.original_items=list(self.inventory.call_function('GetAllItems'))
            self.report.update(natural_components=True,natural_free_slot_metrics=copy.deepcopy(policy.metrics(self.quickbar)));return True
        return False

    def configure(self,slots,active=-1):
        for index in range(len(self.quickbar.call_function('GetSlots'))):self.quickbar.call_function('RemoveItemFromSlot',index)
        self.quickbar.set_property('Slots',[None]*len(slots))
        for index,item in enumerate(slots):
            if item is not None:self.quickbar.call_function('AddItemToSlot',index,item)
        if active>=0:self.quickbar.call_function('SetActiveSlotIndex',active)

    def case(self,name,slots,active,direction,expected,free):
        self.configure(slots,active);self.quickbar.call_function('CycleActiveSlotForward' if direction==1 else 'CycleActiveSlotBackward')
        result=dict(name=name,active=int(self.quickbar.call_function('GetActiveSlotIndex')),free=int(self.quickbar.call_function('GetNextFreeItemSlot')))
        require(result['active']==expected and result['free']==free,'native quickbar boundary differs: '+name)
        if expected>=0:require(capture(self.controller) is not None,'native equip/instigator missing after quickbar selection')
        self.report['cases'].append(result)

    def execute(self):
        before=len(entries(self.inventory));require(grant(self.controller,[],True)==[],'native null inventory guard failed')
        require(grant(self.controller,[])==[],'empty native pickup added items')
        added=grant(self.controller,[(DEFINITIONS[1],2),(DEFINITIONS[2],1),(DEFINITIONS[1],3)])
        require(len(added)==3 and len(entries(self.inventory))==before+3,'native template pickup count differs')
        self.report['pickup_entries']=entries(self.inventory)[before:];self.report['static_pickup_interface_entry_executed']=True
        a,b,c=added
        specs=[('zero',[],-1,1,-1,-1),('one',[a],-1,1,-1,-1),('one_backward',[a],-1,-1,-1,-1),('all_empty',[None]*3,-1,1,-1,0),('empty_backward',[None]*3,-1,-1,-1,0),('sparse',[None,a,None],-1,1,1,0),('sparse_backward',[None,a,None],-1,-1,1,0),('unset_forward',[a,b,c],-1,1,0,-1),('unset_backward',[a,b,c],-1,-1,1,-1),('skip_forward',[a,None,b],0,1,2,1),('forward_wrap',[a,None,b],2,1,0,1),('backward_wrap',[a,None,b],0,-1,2,1),('skip_backward',[a,None,b],2,-1,0,1),('same_only',[None,a,None],1,1,1,0)]
        for spec in specs:self.case(*spec)
        self.report['quickbar_metrics']=copy.deepcopy(policy.metrics(self.quickbar));self.report['inventory_metrics']=copy.deepcopy(policy.metrics(self.inventory));self.finish()

    def cleanup(self):
        if self.original is not None:
            self.configure(self.original_slots,self.original['active'])
            for item in list(self.inventory.call_function('GetAllItems')):
                if item not in self.original_items:self.inventory.call_function('RemoveItemInstance',item)
            self.report['original_inventory_restored']=fingerprint(self.controller)==self.original
        for cls,previous in self.boot:cls.get_cdo().set_property('PythonMixinProfile',previous)
        self.report['selectors_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==p for cls,p in self.boot)

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<200.,'inventory readiness timed out')
            if self.setup():self.execute()
            return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_INVENTORY_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_INVENTORY_SHUTDOWN_'+self.report['status'].upper())


if any(v.startswith('-UEPNativeInventoryResult=') for v in __import__('sys').argv):
    validation=Validation();ticker=ue.add_ticker(validation.tick)
