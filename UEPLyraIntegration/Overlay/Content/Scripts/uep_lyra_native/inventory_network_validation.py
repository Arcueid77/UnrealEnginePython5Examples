"""Native gameplay events -> quickbar policy -> Server RPC -> replicated equip."""
import atexit
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import services,capture
from uep_lyra_network_bots import isolate_bots
from uep_lyra_abilities.jump_network_validation import Server as Playing
from uep_lyra_abilities.quickslot_mixin import CLASS as ABILITY
from .message_validation import arg
from . import inventory as policy
from .inventory_validation_helpers import grant,entries,fingerprint,DEFINITIONS
from .inventory_network_contract import PLAN,require,validate

PEERS=('A','B0')


class Network:
    def __init__(self):
        self.path=Path(arg('UEPNativeInventoryNetworkResult'));self.root=self.path.parent;self.peer=arg('UEPNativeInventoryNetworkPeer');self.run=arg('UEPNativeInventoryNetworkRun');self.profile=arg('UEPNativeInventoryNetworkProfile')
        self.started=time.monotonic();self.finished=False;self.boot=[];self.phase='ready';self.position=0;self.current=None;self.scope=None;self.notifications=[];self.originals={};self.prepared=False;self.restored=False
        self.report=dict(status='running',error=None,peer=self.peer,run_id=self.run,profile=self.profile,cases=[],local_inventory_written=False,native_rpc_bypassed=False,gameplay_state_delivered_by_files=False,original_inventory_restored=False,observer_closed=False)
        for target in (policy.QUICK,policy.INVENTORY):
            cls=ue.load_class(target);ue.register_declared_mixin(cls);self.boot.append((cls,cls.get_cdo().get_property('PythonMixinProfile')));cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.fixture=Playing(str(self.path),self.run) if self.peer=='server' else None
        if self.fixture:self.fixture.ability_class=ABILITY
        atexit.register(self.finalize)

    def token(self,name):
        row=read_json(self.root/name)
        if row is not None:require(row['run_id']==self.run,'foreign inventory rendezvous')
        return row
    def write(self,name,**data):atomic_write(self.root/name,dict(run_id=self.run,**data))

    def client_ready(self):
        if not self.token('playing-ready.json'):return
        statics=ue.find_class('GameplayStatics').get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
            bridge=ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot')
            controller=statics.call_function('GetPlayerController',world,0)
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bAbilitySystemReady and snap.bHealthReady and not snap.bDamageImmune and snap.Health>0) or capture(controller) is None:continue
            require(str(snap.NetMode)=='Client','inventory owner is not a real network client')
            self.world=world;self.controller=controller;self.inventory,self.quickbar=services(controller);self.original=fingerprint(controller)
            require(self.inventory.get_class().get_path_name()==policy.INVENTORY and self.quickbar.get_class().get_path_name()==policy.QUICK,'native replicated component class differs')
            self.helper=ue.new_object(ue.load_class('/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot_C').get_cdo().PythonMessageAdapterClass);self.helper.add_to_root();self.scope=SubscriptionScope()
            def read(proxy):
                payload,ok=self.helper.call_function('ReadQuickBarActiveIndex',proxy);require(ok,'native quickbar notification reader failed');return payload
            def receive(channel,payload):
                if payload.Owner==self.controller:self.notifications.append(int(payload.ActiveIndex))
            self.scope.listen_gameplay_message(world,'Lyra.QuickBar.Message.ActiveIndexChanged',ue.find_struct('LyraQuickBarActiveIndexChangedMessage'),read,receive)
            self.report['native_mode']='Client';self.write(self.peer+'-ready.json',player_id=int(controller.PlayerState.PlayerId));self.phase='permit';return

    def server_prepare(self):
        self.world=self.fixture.world;self.report.update(native_mode='DedicatedServer',natural_playing_phase=self.fixture.playing_gate,production_inventory_classes={},pickup_grant_counts={})
        key='python_grant' if self.profile=='Python' else 'native_grant'
        self.extra_items={};self.extra_slots={}
        for peer,owner in self.fixture.owners.items():
            controller=owner['controller'];inventory,quickbar=services(controller)
            self.originals[peer]=fingerprint(controller);self.report['production_inventory_classes'][peer]=inventory.get_class().get_path_name()==policy.INVENTORY
            before=policy.metrics(inventory)[key];added=grant(controller,[(DEFINITIONS[1],2),(DEFINITIONS[2],1)])
            require(len(added)==2,'native pickup did not create two actual replicated subobjects');self.extra_items[peer]=added
            for item in added:quickbar.call_function('AddItemToSlot',int(quickbar.call_function('GetNextFreeItemSlot')),item)
            self.extra_slots[peer]=quickbar.call_function('GetSlots')[2];self.report['pickup_grant_counts'][peer]=policy.metrics(inventory)[key]-before
        self.prepared=True;self.phase='cases'

    def start_case(self):
        peer=PEERS[self.position//len(PLAN)];index=self.position%len(PLAN);name,initial,expected,empty=PLAN[index]
        controller=self.fixture.owners[peer]['controller'];quickbar=services(controller)[1]
        if quickbar.call_function('GetSlots')[2] is None:quickbar.call_function('AddItemToSlot',2,self.extra_slots[peer])
        quickbar.call_function('SetActiveSlotIndex',initial)
        if empty:quickbar.call_function('RemoveItemFromSlot',2)
        models={p:capture(o['controller']) for p,o in self.fixture.owners.items()}
        if not all(models.values()):return
        self.current=dict(peer=peer,index=index,models=models,started=time.monotonic());self.write(peer+'-permit.json',index=index)

    def client_permit(self):
        if self.position==len(PLAN):self.phase='restore';self.write(self.peer+'-complete.json');return
        token=self.token(self.peer+'-permit.json');model=capture(self.controller);name,initial,expected,empty=PLAN[self.position]
        if token is None or token['index']!=self.position or model is None or model['active']!=initial or len(model['items'])!=3 or (model['slots'][2] is None)!=empty:return
        self.before=copy.deepcopy(policy.metrics(self.quickbar));self.notifications=[]
        kind='backward' if 'backward' in name else 'forward';tag='InputTag.Ability.Quickslot.Cycle'+kind.title()
        self.sent_kind=kind;self.sent_at=time.monotonic();self.phase='observe'
        ue.find_class('AbilitySystemBlueprintLibrary').get_cdo().call_function('SendGameplayEventToActor',self.controller.get_controlled_pawn(),GameplayTag(TagName=tag),GameplayEventData(EventTag=GameplayTag(TagName=tag),Instigator=self.controller.get_controlled_pawn(),Target=self.controller.get_controlled_pawn()))

    def client_observe(self):
        model=capture(self.controller);name,initial,expected,empty=PLAN[self.position]
        require(time.monotonic()-self.sent_at<15.,'owning client native equip/OnRep timed out')
        if model is None or model['active']!=expected or expected not in self.notifications:return
        selected='python_' if self.profile=='Python' else 'native_';other='native_' if selected=='python_' else 'python_';metrics=policy.metrics(self.quickbar)
        row=dict(name=name,model=model,selected_cycle_calls=metrics[selected+self.sent_kind]-self.before[selected+self.sent_kind],other_cycle_calls=metrics[other+self.sent_kind]-self.before[other+self.sent_kind],free=int(self.quickbar.call_function('GetNextFreeItemSlot')),active_notifications=len(self.notifications),replicated_stack_counts=[e['count'] for e in entries(self.inventory)])
        self.report['cases'].append(row);self.write(self.peer+'-'+str(self.position)+'-ack.json',model=model);self.position+=1;self.phase='permit'

    def server_cases(self):
        if self.position==2*len(PLAN):
            if not all(self.token(p+'-complete.json') for p in PEERS):return
            for p,owner in self.fixture.owners.items():
                inventory,quickbar=services(owner['controller']);quickbar.call_function('SetActiveSlotIndex',self.originals[p]['active'])
                for item in self.extra_items[p]:
                    for i,slot in enumerate(quickbar.call_function('GetSlots')):
                        if slot==item:quickbar.call_function('RemoveItemFromSlot',i)
                    inventory.call_function('RemoveItemInstance',item)
                require(fingerprint(owner['controller'])==self.originals[p],'authority inventory restore differs')
            self.report['original_inventory_restored']=True;self.restored=True;self.write('restored.json');self.phase='barrier';return
        if self.current is None:self.start_case();return
        current=self.current;peer=current['peer'];index=current['index'];ack=self.token(peer+'-'+str(index)+'-ack.json')
        require(time.monotonic()-current['started']<20.,'inventory authority RPC acknowledgement timed out')
        other=next(p for p in PEERS if p!=peer)
        require(capture(self.fixture.owners[other]['controller'])==current['models'][other],'native quickbar RPC changed other owner')
        actual=capture(self.fixture.owners[peer]['controller'])
        if ack is None or actual is None or actual['active']!=PLAN[index][2]:return
        require(actual==ack['model'],'native authority/client inventory model differs')
        self.report['cases'].append(dict(peer=peer,index=index,authority=actual,client=ack['model'],other_owner_unchanged=True));self.position+=1;self.current=None

    def cleanup(self):
        if self.scope is not None:self.scope.close();self.helper.remove_from_root()
        self.report['observer_closed']=self.scope is None or self.scope.closed and self.scope.count==0
        for cls,old in self.boot:cls.get_cdo().set_property('PythonMixinProfile',old)
        self.report['selectors_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==old for cls,old in self.boot)

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<420.,'inventory network readiness timed out')
            if self.peer=='server':
                for world in ue.all_worlds():
                    if world.get_world_type() in (1,3,5) and 'L_Expanse' in world.get_name():isolate_bots(self.fixture.statics,world,ue.find_class('AIController'))
                if not self.fixture.playing_gate:self.fixture.wait_playing()
                elif not self.fixture.owners:self.fixture.setup()
                elif not self.prepared:self.server_prepare()
                elif self.phase=='cases':self.server_cases()
                elif self.phase=='barrier' and all(self.token('ready-'+p+'.json') for p in PEERS):self.cleanup();self.write('ready-server.json');self.phase='release'
                elif self.phase=='release':
                    token=self.token('server-release.json')
                    if token:
                        require(token['client_exit_codes']==dict(A=0,B0=0),'real owner exits required');self.report['server_waited_for_client_process_exit']=True;self.finish()
            elif self.phase=='ready':self.client_ready()
            elif self.phase=='permit':self.client_permit()
            elif self.phase=='observe':self.client_observe()
            elif self.phase=='restore':
                if self.token('restored.json') and fingerprint(self.controller)==self.original:self.report['original_inventory_restored']=True;self.cleanup();self.write('ready-'+self.peer+'.json');self.phase='release'
            elif self.phase=='release' and self.token('release.json'):self.finish()
            self.report.update(phase=self.phase,position=self.position);atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_INVENTORY_NETWORK_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_INVENTORY_NETWORK_SHUTDOWN_'+self.report['status'].upper())


network=Network();ticker=ue.add_ticker(network.tick)
