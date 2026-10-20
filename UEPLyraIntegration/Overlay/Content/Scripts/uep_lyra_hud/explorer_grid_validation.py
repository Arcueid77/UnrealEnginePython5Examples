"""Natural UMG Construct and original native typed inventory-message callbacks."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,LyraInventoryChangeMessage
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from . import explorer_grid_mixin as policy
from .explorer_grid_contract import FALSE_FIELDS,require,validate

def path(obj):return obj.get_path_name() if valid(obj) else None
def entries(widget):return [path(v) for v in widget.get_property('TileViewWidget').get_property('ListItems')]
def messages(widget):return sum(policy.evidence(widget)[k] for k in ('python_messages','fallback_messages'))
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.grids=[];self.owned_proxies={};self.proxy_groups=[];self.actor=None;self.roots=[];self.original_selector=None;self.gc_ticks=0
    def proxies(self):return {path(p):p for p in ue.tobject_iterator(ue.find_class('AsyncAction_ListenForGameplayMessage')) if valid(p)}
    def gi_refs(self):return {path(p) for p in self.game.get_property('ReferencedObjects') if valid(p) and p.is_a(ue.find_class('AsyncAction_ListenForGameplayMessage'))}
    def broadcast(self,item,new,delta,channel=policy.CHANNEL):self.probe.call_function('BroadcastInventory',self.router,GameplayTag(TagName=channel),LyraInventoryChangeMessage(InventoryOwner=self.inventory,Instance=item,NewCount=new,Delta=delta))
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.game=self.statics.call_function('GetGameInstance',self.world);self.original_gi=self.gi_refs();self.router=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'));self.cls=ue.load_class(policy.CLASS);self.original_selector=self.cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(self.cls);self.probe=ue.load_class('/Game/UEPValidation/BP_ExplorerGridMessageProbe.BP_ExplorerGridMessageProbe_C').get_cdo()
        for obj in (self.cls,self.probe):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        self.actor=self.world.actor_spawn(ue.find_class('Actor'));self.actor.call_function('SetReplicates',False);self.inventory=self.actor.add_actor_component(ue.find_class('LyraInventoryManagerComponent'),'UEPGridOwnedInventory');definition=ue.load_class('/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C');self.items=[self.inventory.call_function('AddItemDefinition',definition,amount) for amount in (3,5)];require(all(valid(v) for v in self.items),'real owned native inventory entries required');self.initial=[path(v) for v in self.controller.get_component_by_type(ue.find_class('LyraInventoryManagerComponent')).call_function('GetAllItems')]
        for profile in ('BlueprintFallback','Python'):
            before=set(self.proxies());self.cls.get_cdo().set_property('PythonMixinProfile',profile);w=lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);w.add_to_root();ue.set_mixin_profile(w,profile);self.grids.append(w);w.call_function('AddToPlayerScreen',0);added={k:v for k,v in self.proxies().items() if k not in before};self.owned_proxies.update(added);self.proxy_groups.append(set(added))
        self.enter('constructed')
    def trial(self,name,item,new,delta,expected,callbacks=1):
        before=[messages(w) for w in self.grids];self.broadcast(item,new,delta);states=[entries(w) for w in self.grids];self.report['cases'].append(dict(name=name,states=states,expected=list(expected),callback_deltas=[messages(w)-b for w,b in zip(self.grids,before)],expected_callbacks=callbacks));require(states==[list(expected)]*2,'actual native grid entries differ: '+name)
    def observe(self):
        require(time.monotonic()-self.phase_started<15.,'Explorer grid phase timeout: '+self.phase)
        if self.phase=='constructed':
            if any(sum(policy.evidence(w)[k] for k in ('python_construct','fallback_construct'))!=1 for w in self.grids):return
            self.report['natural_construct_snapshots_match_native_inventory']=all(entries(w)==self.initial and w.get_property('NewVar_0')==self.controller.get_component_by_type(ue.find_class('LyraInventoryManagerComponent')) for w in self.grids);before=[messages(w) for w in self.grids];self.broadcast(self.items[0],3,3,'Lyra.Inventory.Message');self.report['exact_parent_channel_ignored']=[messages(w) for w in self.grids]==before;self.report['source_unfiltered_foreign_inventory_messages_preserved']=self.inventory!=self.controller.get_component_by_type(ue.find_class('LyraInventoryManagerComponent'))
            a,b=self.items;first=self.initial+[path(a)];both=first+[path(b)];self.trial('add',a,3,3,first);self.trial('repeat-add',a,3,3,first);self.trial('increase',a,7,4,first);self.trial('decrease',a,2,-5,first);self.trial('remove',a,0,-2,self.initial);self.trial('zero-equality-add',a,0,0,first);self.trial('negative-equality-add',b,-1,-1,both)
            for w in self.grids:w.call_function('RemoveFromParent')
            self.trial('removed-widget-still-listens',b,0,-1,first)
            for index,w in enumerate(self.grids):
                before=set(self.proxies());w.call_function('AddToPlayerScreen',0);added={k:v for k,v in self.proxies().items() if k not in before};self.owned_proxies.update(added);self.proxy_groups[index].update(added)
            self.enter('reconstructed')
        elif self.phase=='reconstructed':
            if any(sum(policy.evidence(w)[k] for k in ('python_construct','fallback_construct'))!=2 for w in self.grids):return
            self.report['native_reconstruction_clears_and_resnapshots']=all(entries(w)==self.initial for w in self.grids);self.report['native_proxy_counts']=[len(group) for group in self.proxy_groups];self.report['native_proxy_paths_per_widget']=[sorted(group) for group in self.proxy_groups];self.report['two_original_native_proxies_per_reconstructed_widget']=self.report['native_proxy_counts']==[2,2] and len(self.owned_proxies)==4;self.trial('reconstructed-two-listeners',self.items[0],2,2,self.initial+[path(self.items[0])],2)
            for w,profile in zip(self.grids,('Python','BlueprintFallback')):ue.set_mixin_profile(w,profile)
            before=[copy.deepcopy(policy.evidence(w)) for w in self.grids];self.trial('switch-pending-listeners',self.items[0],0,-2,self.initial,2);self.report['switched_callback_profiles']=[policy.evidence(w)['python_messages']-before[i]['python_messages']==2 if i==0 else policy.evidence(w)['fallback_messages']-before[i]['fallback_messages']==2 for i,w in enumerate(self.grids)];require(all(self.report['switched_callback_profiles']),'native listener callback used stale Profile');self.retire_grids();self.report['owned_proxy_gi_refs_before_gc']=len(set(self.owned_proxies)&self.gi_refs());lib('KismetSystemLibrary').call_function('CollectGarbage');self.enter('gc')
        elif self.phase=='gc':
            self.gc_ticks+=1
            if self.gc_ticks<3:return
            self.broadcast(self.items[0],1,1);self.report['owned_proxy_gi_refs_after_gc']=len(set(self.owned_proxies)&self.gi_refs());self.report['native_gc_releases_owned_listener_gi_references']=self.report['owned_proxy_gi_refs_after_gc']==0;self.report['owned_proxies_inactive_after_gc_and_message']=all(not valid(p) or not p.call_function('IsActive') for p in self.owned_proxies.values());self.report['original_native_listener_gi_references_preserved']=self.original_gi<=self.gi_refs();self.finish()
    def retire_grids(self):
        for w in self.grids:
            if valid(w):w.call_function('RemoveFromParent');ue.clear_mixin_profile(w);w.remove_from_root()
    def cleanup(self):
        self.retire_grids()
        if valid(self.actor):self.actor.actor_destroy()
        if self.original_selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.original_selector)
        for obj in self.roots:obj.remove_from_root()
        self.report['owned_actor_widgets_roots_and_profile_selectors_restored']=not valid(self.actor) and all(not valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.grids) and all(not obj.is_rooted() for obj in self.roots) and self.cls.get_cdo().get_property('PythonMixinProfile')==self.original_selector;self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'Explorer grid readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_GRID_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_GRID_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerGridResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
