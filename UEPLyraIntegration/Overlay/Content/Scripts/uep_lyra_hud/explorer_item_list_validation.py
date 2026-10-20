"""Exact native messages, source factories/bindings, real ListView rows and GC."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,LyraInventoryChangeMessage
from uep_runtime import SubscriptionScope
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from . import explorer_item_list_mixin as policy,explorer_toast_mixin as toast
from .explorer_item_list_contract import FALSE_FIELDS,require,validate

def path(v):return v.get_path_name() if valid(v) else None
def messages(w):return sum(policy.evidence(w)[p+'_message'] for p in ('python','fallback'))
def entries(w):return list(w.get_property('ToastListWidget').get_property('ListItems'))
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,groups=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.roots=[];self.selectors={};self.owned_proxies={};self.scopes=[];self.actor=None;self.index=0
    def proxies(self):return {path(p):p for p in ue.tobject_iterator(ue.find_class('AsyncAction_ListenForGameplayMessage')) if valid(p)}
    def gi_refs(self):return {path(p) for p in self.game.get_property('ReferencedObjects') if valid(p) and p.is_a(ue.find_class('AsyncAction_ListenForGameplayMessage'))}
    def broadcast(self,item,delta,new=-777,channel=policy.CHANNEL):self.probe.call_function('BroadcastInventory',self.router,GameplayTag(TagName=channel),LyraInventoryChangeMessage(InventoryOwner=self.inventory,Instance=item,Delta=delta,NewCount=new))
    def state(self,w,label):
        result=[]
        for index,item in enumerate(entries(w)):
            file=self.path.parent/(label+'-'+str(index)+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(item,str(file)),'native formatted toast export failed');raw=file.read_text(encoding='utf-8-sig');result.append(dict(text=str(item.get_property('TextToShow')),icon=path(item.get_property('IconToShow')),duration=float(item.get_property('DisplayDuration')),native_format_identity_preserved='E40DBDA84BB0A625640CE890772DF399' in raw))
        return result
    def clear(self,w):
        for item in entries(w):w.call_function('RemoveToast',item)
    def trial(self,name,item,delta,expected,callbacks=1,channel=policy.CHANNEL,text=None,icon=None):
        before=[messages(w) for w in self.current];self.broadcast(item,delta,channel=channel);states=[self.state(w,self.row_profile+'-'+name+'-'+str(i)) for i,w in enumerate(self.current)];outers=all(item.get_outer()==w for w in self.current for item in entries(w));self.group['cases'].append(dict(name=name,states=states,callback_deltas=[messages(w)-n for w,n in zip(self.current,before)],expected_callbacks=callbacks,expected_items=expected,expected_text=text,expected_icon=icon,all_item_outers_match_own_list=outers));require(states[0]==states[1] and all(len(state)==expected for state in states),'native item list state/count mismatch: '+name)
        for w in self.current:self.clear(w)
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.game=self.statics.call_function('GetGameInstance',self.world);self.original_refs=self.gi_refs();self.router=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'));self.cls=ue.load_class(policy.CLASS);self.row_cls=ue.load_class(toast.CLASS);self.probe=ue.load_class('/Game/UEPValidation/BP_ExplorerItemListProbe.BP_ExplorerItemListProbe_C').get_cdo()
        for cls in (self.cls,self.row_cls):self.selectors[cls]=cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(cls)
        for obj in (self.cls,self.row_cls,self.probe):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        self.actor=self.world.actor_spawn(ue.find_class('Actor'));self.actor.call_function('SetReplicates',False);self.inventory=self.actor.add_actor_component(ue.find_class('LyraInventoryManagerComponent'),'UEPItemListOwnedInventory');definition=ue.load_class('/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C');self.item=self.inventory.call_function('AddItemDefinition',definition,3);self.noicon=self.inventory.call_function('AddItemDefinition',ue.load_class('/Game/UEPValidation/BP_ExplorerItemListNoIconDefinition.BP_ExplorerItemListNoIconDefinition_C'),1);fragment=self.item.call_function('FindFragmentByClass',ue.find_class('InventoryFragment_QuickBarIcon'));self.item_name=str(fragment.get_property('DisplayNameWhenEquipped'));self.icon=path(lib('WidgetBlueprintLibrary').call_function('GetBrushResourceAsTexture2D',fragment.get_property('Brush')));self.start_group()
    def start_group(self):
        self.row_profile=('BlueprintFallback','Python')[self.index];self.row_cls.get_cdo().set_property('PythonMixinProfile',self.row_profile);self.current=[];self.proxy_groups=[];self.group=dict(row_profile=self.row_profile,cases=[])
        for profile in ('BlueprintFallback','Python'):
            before=set(self.proxies());self.cls.get_cdo().set_property('PythonMixinProfile',profile);w=lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);w.add_to_root();self.widgets.append(w);self.current.append(w);ue.set_mixin_profile(w,profile);w.call_function('AddToPlayerScreen',0);added={k:v for k,v in self.proxies().items() if k not in before};self.owned_proxies.update(added);self.proxy_groups.append(set(added));require(int(w.get_property('DisplayVBox').call_function('GetVisibility'))==1,'initial source empty list must collapse')
        self.trial('parent-ignored',self.item,1,0,0,'Lyra.Inventory.Message');self.trial('zero-ignored',self.item,0,0);self.trial('negative-ignored',self.item,-3,0);self.trial('positive-one',self.item,1,1,text='1x '+self.item_name,icon=self.icon);self.trial('positive-large',self.item,1000,1,text='1,000x '+self.item_name,icon=self.icon);self.trial('missing-fragment',self.noicon,2,1,text='2x ');self.trial('repeat-positive',self.item,1,1,text='1x '+self.item_name,icon=self.icon)
        for w in self.current:w.call_function('RemoveFromParent')
        self.trial('removed-still-listens',self.item,2,1,text='2x '+self.item_name,icon=self.icon)
        for index,w in enumerate(self.current):
            before=set(self.proxies());w.call_function('AddToPlayerScreen',0);added={k:v for k,v in self.proxies().items() if k not in before};self.owned_proxies.update(added);self.proxy_groups[index].update(added)
        self.group['native_proxy_counts']=[len(v) for v in self.proxy_groups];self.group['proxy_paths']=[sorted(v) for v in self.proxy_groups];self.trial('reconstructed-two-listeners',self.item,2,2,2,text='2x '+self.item_name,icon=self.icon)
        for w,p in zip(self.current,('Python','BlueprintFallback')):ue.set_mixin_profile(w,p)
        self.trial('switch-current-profile',self.item,3,2,2,text='3x '+self.item_name,icon=self.icon);self.broadcast(self.item,4);self.expiries=[[],[]];self.live_rows=[[],[]];self.observed_time=None;self.enter('rows')
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'Explorer item list phase timeout: '+self.phase)
        if self.phase=='rows':
            rows=[list(w.get_property('ToastListWidget').call_function('GetDisplayedEntryWidgets')) for w in self.current]
            if any(len(v)!=2 for v in rows):return
            self.observed_time=self.game_time();self.live_rows=rows;self.remove_before=[copy.deepcopy(policy.evidence(w)) for w in self.current];self.expiry_before=[]
            for index,group in enumerate(rows):
                for row in group:
                    require(row.get_class()==self.row_cls and row.get_property('ItemPtr') in entries(self.current[index]),'real native row/current item differs');require(toast.evidence(row)['python_item' if self.row_profile=='Python' else 'fallback_item']>=1,'native row creation used wrong initial Profile');scope=SubscriptionScope();scope.bind_event(row,'OnToastExpired',lambda item,index=index:self.expiries[index].append(dict(item=path(item),time=self.game_time())));self.scopes.append(scope);ue.set_mixin_profile(row,'Python' if self.row_profile=='BlueprintFallback' else 'BlueprintFallback');self.expiry_before.append(copy.deepcopy(toast.evidence(row)))
            self.group['native_entry_assignment_and_binding_observed']=all(sum(policy.evidence(w)[p+'_bind'] for p in ('python','fallback'))>=2 for w in self.current)
            for w,p in zip(self.current,('BlueprintFallback','Python')):ue.set_mixin_profile(w,p)
            self.enter('expiry')
        elif self.phase=='expiry':
            if any(entries(w) for w in self.current) or any(len(v)!=2 for v in self.expiries):return
            flat=[row for group in self.live_rows for row in group];callback='python_expired' if self.row_profile=='BlueprintFallback' else 'fallback_expired';row_profiles=all(toast.evidence(row)[callback]-old[callback]==1 for row,old in zip(flat,self.expiry_before));list_profiles=all(policy.evidence(w)[p+'_remove']-old[p+'_remove']==2 for w,p,old in zip(self.current,('fallback','python'),self.remove_before));self.group.update(pending_row_and_list_profiles_used=row_profiles and list_profiles,native_two_second_expiry_removes_all_items=True,expired_items=[len(v) for v in self.expiries],expiry_elapsed=[event['time']-self.observed_time for events in self.expiries for event in events],final_empty_list_collapsed=all(int(w.get_property('DisplayVBox').call_function('GetVisibility'))==1 for w in self.current))
            for scope in self.scopes:scope.close()
            for row in flat:ue.clear_mixin_profile(row)
            self.last_counts=[policy.evidence(w) for w in self.current];self.last_snapshots=[copy.deepcopy(v) for v in self.last_counts];self.retire_current();lib('KismetSystemLibrary').call_function('CollectGarbage');self.gc_ticks=0;self.enter('gc')
        elif self.phase=='gc':
            self.gc_ticks+=1
            if self.gc_ticks<3:return
            self.broadcast(self.item,0);self.group['original_listener_refs_preserved']=self.original_refs<=self.gi_refs();require(self.last_counts==self.last_snapshots,'collected original list listener invoked late');self.report['groups'].append(self.group);self.index+=1
            if self.index<2:self.start_group()
            else:self.report['original_native_listener_released_after_owned_gc']=not set(self.owned_proxies)&self.gi_refs();self.report['owned_proxies_inactive_after_gc_and_message']=all(not valid(p) or not p.call_function('IsActive') for p in self.owned_proxies.values());self.finish()
    def retire_current(self):
        for w in self.current:
            if valid(w):w.call_function('RemoveFromParent');ue.clear_mixin_profile(w);w.remove_from_root()
    def cleanup(self):
        if hasattr(self,'current'):self.retire_current()
        for scope in self.scopes:scope.close()
        for group in getattr(self,'live_rows',[]):
            for row in group:
                if valid(row):lib('KismetSystemLibrary').call_function('K2_ClearTimer',row,'OnTimerElapsed');ue.clear_mixin_profile(row)
        if valid(self.actor):self.actor.actor_destroy()
        for cls,p in self.selectors.items():cls.get_cdo().set_property('PythonMixinProfile',p)
        for obj in self.roots:obj.remove_from_root()
        self.report['owned_widgets_actors_roots_and_selectors_restored']=not valid(self.actor) and all(not valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(not obj.is_rooted() for obj in self.roots) and all(cls.get_cdo().get_property('PythonMixinProfile')==p for cls,p in self.selectors.items());self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'Explorer item list readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_ITEM_LIST_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_ITEM_LIST_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerItemListResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
