"""Actual native list entry callbacks, original TimerManager and delegate expiry."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from . import explorer_toast_mixin as policy
from .explorer_toast_contract import FALSE_FIELDS,SCENARIOS,require,validate

LIST='/ShooterExplorer/UserInterface/W_ItemAcquiredList.W_ItemAcquiredList_C'
def path(v):return v.get_path_name() if valid(v) else None
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.roots=[];self.records=[];self.scopes=[];self.lists=[];self.list_rows=[];self.text_ok=[];self.image_ok=[];self.selector=None
    def now(self):return self.game_time()
    def timer(self,row):return bool(lib('KismetSystemLibrary').call_function('K2_TimerExists',row,'OnTimerElapsed'))
    def text(self,obj,prefix,label):
        file=self.path.parent/(label+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file)),'native FText export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');lines=[line.strip()[len(prefix):] for line in text.splitlines() if line.strip().startswith(prefix)];require(len(lines)==1,'one native localized field required');return lines[0]
    def seed(self,duration,icon=True):
        value=ue.new_object(self.entry_cls,self.game);value.add_to_root();self.roots.append(value);self.probe.call_function('SeedLocalizedEntry',value,self.definition);value.set_property('DisplayDuration',duration);value.set_property('IconToShow',self.texture if icon else None);return value
    def own(self,w,profile):w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,profile);return w
    def listen(self,row,events):
        scope=SubscriptionScope();scope.bind_event(row,'OnToastExpired',lambda value:events.append(dict(item=path(value),time=self.now())));self.scopes.append(scope);return scope
    def bind(self,row,value,label):
        row.call_function('OnListItemObjectSet',value);a=self.text(value,'TextToShow=',label+'-entry');b=self.text(row.get_property('ItemNameAndQtyWidget'),'Text=',label+'-row');self.text_ok.append(a==b and 'NSLOCTEXT' in a)
    def image(self,row):
        image=row.get_property('ItemIconWidget');brush=image.get_property('Brush');texture=lib('WidgetBlueprintLibrary').call_function('GetBrushResourceAsTexture2D',brush);return dict(texture=path(texture),visibility=int(image.call_function('GetVisibility')),size=[float(brush.ImageSize.X),float(brush.ImageSize.Y)])
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.game=self.statics.call_function('GetGameInstance',self.world);self.cls=ue.load_class(policy.CLASS);self.entry_cls=ue.load_class(policy.ENTRY);self.probe=ue.load_class('/Game/UEPValidation/BP_ExplorerToastNativeProbe.BP_ExplorerToastNativeProbe_C').get_cdo();self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(self.cls)
        for obj in (self.cls,self.entry_cls,self.probe):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        self.definition=ue.load_class('/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C').get_cdo();fragment,=[f for f in self.definition.get_property('Fragments') if f.is_a(ue.find_class('InventoryFragment_QuickBarIcon'))];self.texture=lib('WidgetBlueprintLibrary').call_function('GetBrushResourceAsTexture2D',fragment.get_property('Brush'));require(valid(self.texture),'original native pistol icon texture required')
        self.list_class=ue.load_class(LIST);self.list_index=0;self.start_list()
    def start_list(self):
        self.list_profile=('BlueprintFallback','Python')[self.list_index];self.cls.get_cdo().set_property('PythonMixinProfile',self.list_profile);self.feed=lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.list_class,self.controller);self.feed.add_to_root();self.lists.append(self.feed);self.feed.call_function('AddToPlayerScreen',0);self.view=self.feed.get_property('ToastListWidget');self.list_entry=self.seed(1.);self.view.call_function('AddItem',self.list_entry);self.feed.call_function('UpdateDisplayVisibility');self.list_events=[];self.list_row=None;self.enter('list')
    def observe(self):
        require(time.monotonic()-self.phase_started<15.,'Explorer toast phase timeout: '+self.phase)
        if self.phase=='list':
            displayed=list(self.view.call_function('GetDisplayedEntryWidgets'))
            if self.list_row is None:
                if not displayed:return
                require(len(displayed)==1 and displayed[0].get_class()==self.cls,'original native toast row class differs');self.list_row=displayed[0];self.list_rows.append(self.list_row);self.listen(self.list_row,self.list_events);counts=policy.evidence(self.list_row);require(counts['python_item' if self.list_profile=='Python' else 'fallback_item']>=1,'native list did not deliver valid payload');a=self.text(self.list_entry,'TextToShow=',self.list_profile+'-list-entry');b=self.text(self.list_row.get_property('ItemNameAndQtyWidget'),'Text=',self.list_profile+'-list-row');self.text_ok.append(a==b and 'NSLOCTEXT' in a)
            if not self.list_events:return
            require(len(self.list_events)==1 and self.list_events[0]['item']==path(self.list_entry) and self.view.call_function('GetNumItems')==0,'original list expiry did not remove current item');self.feed.call_function('RemoveFromParent');self.list_index+=1
            if self.list_index<2:self.start_list()
            else:self.report['native_list_view_delivered_valid_entries']=True;self.report['native_list_expiry_removed_original_items']=True;self.start_matrix()
        elif self.phase=='matrix':
            elapsed=self.now()-self.matrix_started
            if not self.replaced and elapsed>=.15:
                for rec in self.records:
                    if rec['name']=='replace':rec['item']=self.seed(1.2,False);self.bind(rec['row'],rec['item'],rec['profile']+'-replacement');rec['set_time']=self.now();rec['duration']=1.2
                self.replaced=True
            if elapsed<1.9:return
            for rec in self.records:
                row=rec['row'];events=rec['events'];count=rec['counts'];profile=rec['callback_profile'];expiry=count['python_expired']+count['fallback_expired'];name=rec['name'];expected=0 if name in ('zero','negative','gc') else 1;item_ok=not events or all(e['item']==path(rec['item']) for e in events);native_state=not valid(row) if name=='gc' else not self.timer(row)
                result=dict(name=name,profile=rec['profile'],expiry_count=len(events),expected_item_payload=item_ok,native_timer_state_matches=native_state,current_callback_profile_matches=expiry==expected and count['python_expired' if profile=='Python' else 'fallback_expired']==expected,configured_last_duration=rec['duration'],elapsed_after_last_valid_set=(events[-1]['time']-rec['set_time']) if events else 0.)
                if name=='gc':result.update(row_native_object_collected=not valid(row),no_timer_callback_after_gc=expiry==0)
                self.report['cases'].append(result)
            self.report['localized_text_namespace_keys_preserved']=all(self.text_ok);self.report['icon_texture_visibility_and_unmatched_size_pairs_preserved']=all(self.image_ok);self.finish()
    def start_matrix(self):
        self.matrix_started=self.now();self.replaced=False
        for name in SCENARIOS:
            images=[]
            for profile in ('BlueprintFallback','Python'):
                self.cls.get_cdo().set_property('PythonMixinProfile',profile);row=self.own(lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller),profile);row.call_function('AddToPlayerScreen',0);events=[];scope=self.listen(row,events);duration=0. if name=='zero' else -.2 if name=='negative' else 1.2 if name=='gc' else .8;item=self.seed(duration);self.bind(row,item,name+'-'+profile);rec=dict(name=name,profile=profile,callback_profile=profile,row=row,events=events,counts=policy.evidence(row),item=item,duration=duration,set_time=self.now());self.records.append(rec)
                image=row.get_property('ItemIconWidget');brush=image.get_property('Brush');brush.ImageSize=ue.find_struct('DeprecateSlateVector2D')(X=113.,Y=47.);image.call_function('SetBrush',brush);states=[]
                for texture in (self.texture,None,self.texture):row.call_function('SetIcon',texture);states.append(self.image(row))
                images.append(states)
                if name=='invalid':
                    for invalid in (None,self.game):row.call_function('OnListItemObjectSet',invalid)
                    require(row.get_property('ItemPtr')==item,'failed source cast changed current item')
                if name=='switch':rec['callback_profile']='Python' if profile=='BlueprintFallback' else 'BlueprintFallback';ue.set_mixin_profile(row,rec['callback_profile'])
                if name in ('removed','gc'):row.call_function('RemoveFromParent')
                if name=='gc':scope.close();ue.clear_mixin_profile(row);row.remove_from_root()
            self.image_ok.append(images[0]==images[1] and all(s['size']==[113.,47.] and s['visibility']==(2 if index==1 else 0) and s['texture']==(None if index==1 else path(self.texture)) for index,s in enumerate(images[0])))
        lib('KismetSystemLibrary').call_function('CollectGarbage');self.enter('matrix')
    def cleanup(self):
        for scope in self.scopes:scope.close()
        for row in self.widgets+self.list_rows:
            if valid(row):lib('KismetSystemLibrary').call_function('K2_ClearTimer',row,'OnTimerElapsed')
        timers_closed=all(not valid(row) or not self.timer(row) for row in self.widgets+self.list_rows)
        for row in self.widgets:
            if valid(row):ue.clear_mixin_profile(row);row.call_function('RemoveFromParent');row.remove_from_root()
        for feed in self.lists:
            if valid(feed):feed.call_function('RemoveFromParent');feed.remove_from_root()
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        for obj in self.roots:
            if valid(obj):obj.remove_from_root()
        self.report['owned_timers_widgets_roots_and_selectors_restored']=timers_closed and all(not valid(row) or not row.is_rooted() and not row.call_function('IsInViewport') for row in self.widgets+self.lists) and all(not valid(obj) or not obj.is_rooted() for obj in self.roots) and self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector;self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'Explorer toast readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_TOAST_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_TOAST_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerToastResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
