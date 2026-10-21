"""Observe actual Arena registrations plus native owned component Begin/EndPlay."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from . import arena_player_ui_mixin as policy
from .arena_player_ui_contract import validate

PROBE='/Game/UEPValidation/BP_ArenaPlayerUIProbe.BP_ArenaPlayerUIProbe_C'
def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def path(obj):return obj.get_path_name() if valid(obj) else None
def handle_valid(handle):
    value=ue.find_class('UIExtensionHandleFunctions').get_cdo().call_function('IsValid',handle)
    if not isinstance(value,tuple) or len(value)!=2 or type(value[0]) is not bool:raise RuntimeError('native handle IsValid ABI differs')
    return value[0]

class Validation:
    def __init__(self,result):
        self.path=Path(result);self.started=time.monotonic();self.mode=arg('UEPArenaPlayerUIMode');self.finished=False;self.world=None;self.roots=[];self.observers=[];self.points=[];self.owned=[];self.selector=None
        self.report=dict(status='running',error=None,mode=self.mode,natural_components=[],owned_components=[],initial_registry=[],final_registry=[],owned_events=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,lifecycle_callbacks_replayed=False,registry_replaced=False,observer_callback_native=True,native_component_destruction=True)
        self.cls=ue.load_class(policy.CLASS);self.probe_cls=ue.load_class(PROBE)
        for obj in (self.cls,self.probe_cls):self.root(obj)
        class Observe:
            def Observe(witness,Action,ExtensionRequest):
                # Serialize the borrowed native request during the callback.
                witness._events.append(dict(action=int(Action),tag=str(ExtensionRequest.ExtensionPointTag.TagName),priority=int(ExtensionRequest.Priority),data=path(ExtensionRequest.Data),context=path(ExtensionRequest.ContextObject),handle_valid=handle_valid(ExtensionRequest.ExtensionHandle)))
        ue.register_mixin_profile(self.probe_cls,'Observe',Observe,make_default=True)
        if self.mode!='Baseline':
            self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');self.cls.get_cdo().set_property('PythonMixinProfile',self.mode);ue.register_declared_mixin(self.cls)
    def root(self,obj):
        if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
    def write(self):atomic_write(self.path,self.report)
    def observer(self):
        witness=ue.new_object(self.probe_cls);self.root(witness);self.observers.append(witness);witness._events=[]
        result=witness.call_function('Install',self.subsystem,[ue.find_class('LyraPlayerState')])
        parameters=ue.describe_function(self.probe_cls,'Install')['parameters']
        names=[p['name'] for p in parameters if int(p['flags'])&0x400]+[p['name'] for p in parameters if int(p['flags'])&0x100 and not int(p['flags'])&0x400 and (p['type']=='TArray' or p['type'].startswith('TArray<') or not int(p['flags'])&0x2)]
        if not isinstance(result,tuple) or len(result)!=len(names):raise RuntimeError('observer Install output ABI differs: '+str(names))
        handle=dict(zip(names,result))['Handle']
        self.points.append(handle);return witness
    def snapshot_registry(self):
        witness=self.observer();events=copy.deepcopy(witness._events);self.subsystem.call_function('UnregisterExtensionPoint',self.points[-1]);self.points.pop();self.observers.remove(witness);witness.remove_from_root();self.roots.remove(witness)
        if any(v['action']!=0 for v in events):raise RuntimeError('fresh point must enumerate Added registrations')
        return events
    def exercise(self):
        components=[c for c in ue.tobject_iterator(self.cls) if valid(c) and c.get_world()==self.world and not c.is_rooted()]
        if not components:return False
        self.subsystem=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',self.world,ue.find_class('UIExtensionSubsystem'))
        if not valid(self.subsystem):return False
        for component in components:
            owner=component.call_function('GetOwner')
            if not handle_valid(component.get_property('ExtensionHandle')):return False
            self.report['natural_components'].append(dict(component=path(component),owner=path(owner),owner_is_playerstate=owner.is_a(ue.find_class('LyraPlayerState')),handle_valid=True,counts=copy.deepcopy(policy.evidence(component))))
        self.owner=components[0].call_function('GetOwner');self.report['owned_owner']=path(self.owner);self.witness=self.observer();self.report['initial_registry']=copy.deepcopy(self.witness._events);self.witness._events=[]
        for index in range(2):
            component=self.owner.add_actor_component(self.cls,'UEPArenaPlayerUIOwned'+str(index));self.owned.append(component);handle=component.get_property('ExtensionHandle').clone();counts=policy.evidence(component)
            self.report['owned_components'].append(dict(component=path(component),owner=path(component.call_function('GetOwner')),handle_valid_before=handle_valid(handle)))
            self.owned[-1]=(component,handle,counts)
        for index,(component,handle,counts) in enumerate(self.owned):
            component.destroy_component();row=self.report['owned_components'][index];row.update(handle_valid_after_unregister=handle_valid(handle),counts_after=copy.deepcopy(counts));self.report['remaining_after_'+('first' if index==0 else 'second')+'_destroy']=len(self.snapshot_registry())
        self.owned=[];self.report['owned_events']=copy.deepcopy(self.witness._events);self.report['final_registry']=self.snapshot_registry();return True
    def cleanup(self):
        for value in self.owned:
            component=value[0] if isinstance(value,tuple) else value
            if valid(component):component.destroy_component()
        self.owned=[]
        if hasattr(self,'subsystem'):
            for handle in self.points:self.subsystem.call_function('UnregisterExtensionPoint',handle)
        self.points=[]
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        ue.unregister_mixin(self.probe_cls)
        for obj in reversed(self.roots):obj.remove_from_root()
        self.report['cleanup_complete']=not self.points and not self.owned and all(not obj.is_rooted() for obj in self.roots) and (self.selector is None or self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector)
    def tick(self,delta):
        if self.finished:return False
        try:
            if time.monotonic()-self.started>150.:raise RuntimeError('Arena player UI native timeout')
            for world in ue.all_worlds():
                if world.get_world_type() in (1,3) and 'TopDown' in world.get_name():self.world=world;break
            if self.world is not None and self.exercise():self.finish()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ARENA_PLAYER_UI_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_PLAYER_UI_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaPlayerUIResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
