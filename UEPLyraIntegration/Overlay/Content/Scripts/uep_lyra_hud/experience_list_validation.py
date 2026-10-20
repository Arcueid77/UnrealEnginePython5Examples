"""Actual selection-screen caller, native async catalog, remount/cache and focus."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import experience_list_mixin as policy
from . import experience_entry_mixin as entry
from .experience_list_contract import PROFILES,FALSE_FIELDS,require,validate

def path(obj):return obj.get_path_name() if obj is not None else None
def paths(values):return [path(value) for value in values]
def count(widget,method):return sum(policy.evidence(widget)[p+'_'+method] for p in ('python','fallback'))

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,trials=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.class_roots=[];self.parents=[];self.bindings=[];self.visibility_scopes=[];self.index=0;self.states=[]
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in dict(list=policy.CLASS,tile=entry.CLASS).items()};self.selection_cls=ue.load_class('/Game/UI/Menu/Experiences/W_ExperienceSelectionScreen.W_ExperienceSelectionScreen_C');self.async_cls=ue.find_class('AsyncActionLoadPrimaryAssetList')
        for cls in list(self.classes.values())+[self.selection_cls]:
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
        self.cdos={cls:cls.get_cdo().get_property('PythonMixinProfile') for cls in self.classes.values()};self.show_before=self.classes['list'].get_cdo().get_property('ShowAllExperiences')
        for cls in self.cdos:ue.register_declared_mixin(cls)
        self.start_trial()
    def bind(self,obj,name,fn):obj.bind_event(name,fn);self.bindings.append((obj,name,fn))
    def owned_widget(self,parent,name):
        pending=[parent.get_property('WidgetTree').get_property('RootWidget')]
        while pending:
            widget=pending.pop()
            if widget.get_name()==name:return widget
            if widget.is_a(ue.find_class('PanelWidget')):pending.extend(widget.call_function('GetChildAt',i) for i in range(int(widget.call_function('GetChildrenCount'))))
        raise RuntimeError('owned caller widget missing: '+name)
    def start_trial(self):
        self.profile=PROFILES[self.index//2];self.show_all=bool(self.index%2)
        for cls in self.cdos:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.parent=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.selection_cls,self.controller);self.parent.add_to_root();self.parents.append(self.parent);self.w=self.parent.get_property('W_ExperienceList');ue.set_mixin_profile(self.w,self.profile);self.w.set_property('ShowAllExperiences',self.show_all);self.completed=0;self.selections=[];self.catalogs=[];self.row=dict(profile=self.profile,show_all=self.show_all);self.matrix={}
        def loaded():self.completed+=1;self.catalogs.append(self.native_catalog())
        def selected(exp):self.selections.append(exp)
        self.bind(self.w,'OnExperiencesLoaded',loaded);self.bind(self.w,'OnExperienceSelected',selected);self.mount(False)
    def mount(self,remount):
        baseline={path(p) for p in ue.tobject_iterator(self.async_cls)};self.parent.call_function('AddToPlayerScreen',0);self.parent.call_function('ActivateWidget');new=[p for p in ue.tobject_iterator(self.async_cls) if path(p) not in baseline];require(len(new)==1,'native list Construct must create one primary-asset async action')
        self.row['native_async_actions_observed']=self.row.get('native_async_actions_observed',0)+1;self.enter('remounted' if remount else 'loaded')
    def native_catalog(self):
        # Cached loads can complete inside Activate before a later observer can
        # bind the async proxy. The native list's real completion dispatcher is
        # bound before Construct; read the same ordered primary IDs/loaded
        # objects there without issuing or replaying a load/completion.
        ids,=policy.lib('KismetSystemLibrary').call_function('GetPrimaryAssetIdList',ue.find_struct('PrimaryAssetType')(Name='LyraUserFacingExperienceDefinition'));objects=[policy.lib('KismetSystemLibrary').call_function('GetObjectFromPrimaryAssetId',asset_id) for asset_id in ids];return [obj for obj in objects if valid(obj)]
    def native_text(self,obj,field,label):
        file=self.path.parent/(self.profile+str(int(self.show_all))+'-'+label+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file)),'native experience text export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');values=[line.strip().split('=',1)[1] for line in text.splitlines() if line.strip().startswith(field+'=')];require(len(values)==1,'native text field missing: '+field);return values[0]
    def check_rows(self,remount):
        catalog=self.catalogs[-1];cls=ue.find_class('LyraUserFacingExperienceDefinition');visible=[exp for exp in catalog if valid(exp) and exp.is_a(cls) and exp.get_property('bShowInFrontEnd')];expected=list(reversed([exp for exp in visible if exp.get_property('bIsDefaultExperience')]))+([exp for exp in visible if not exp.get_property('bIsDefaultExperience')] if self.show_all else []);actual=list(self.w.get_property('UserFacingExperienceList'));require(paths(actual)==paths(expected) and actual,'native asset filter/default-prepend ordering differs');self.expected=expected;self.n=len(expected);row=self.w.get_property('ExperienceRowBox');cache=list(self.w.get_property('ExperienceWidgets'));require(int(row.call_function('GetChildrenCount'))==self.n and len(cache)==self.n*(2 if remount else 1),'native rows/cache accumulation differs');children=[row.call_function('GetChildAt',i) for i in range(self.n)];require(children==cache[-self.n:] and all(tile.get_property('MyUserFacingExperience')==exp for tile,exp in zip(children,expected)),'native entry row/definition identity differs');self.children=children;self.cache=cache
        histories=[]
        for i,(tile,exp) in enumerate(zip(children,expected)):
            require(ue.get_mixin_profile(tile)==self.profile,'entry Profile differs');button=tile.get_property('ExperienceTileButton');values=[]
            for source,target in (('TileTitle','ExperienceTitle'),('TileSubTitle','MapTitle'),('TileDescription','ExperienceDescription')):
                native=self.native_text(exp,source,'definition'+str(i)+source+str(int(remount)));label=self.native_text(button.get_property(target),'Text','label'+str(i)+target+str(int(remount)));require(native==label,'native experience localized text/history differs');values.append(native)
            histories.append(values);icon=exp.get_property('TileIcon')
            if valid(icon):require(button.get_property('KeyArt').call_function('GetDynamicMaterial').call_function('K2_GetTextureParameterValue','TileArt')==icon,'native experience art identity differs')
        self.row.update(visible_entries=self.n,actual_native_async_catalog_order_and_filter=True,actual_native_text_histories_and_art_preserved=True);self.matrix['catalog']=paths(catalog);self.matrix['filtered']=paths(expected);self.matrix['histories']=histories
        if remount:self.row.update(remount_cache_size=len(cache),actual_native_remount_rebuild_and_accumulating_cache=True)
        else:self.row['initial_cache_size']=len(cache)
    def click(self,tile,expected,phase):
        self.event_before=len(self.selections);self.event_expected=expected;tile.get_property('ExperienceTileButton').call_function('HandleButtonClicked');self.enter(phase)
    def delivered(self):
        events=self.selections[self.event_before:]
        if not events:return False
        require(events==[self.event_expected] and self.parent.get_property('SelectedExperience')==self.event_expected,'native entry/list/selection-parent event payload differs');return True
    def observe(self):
        require(time.monotonic()-self.phase_started<35.,'experience list phase timeout: '+self.phase)
        if self.phase in ('loaded','remounted'):
            remount=self.phase=='remounted';required=2 if remount else 1
            if self.completed<required or len(self.catalogs)<required:return
            require(self.completed==len(self.catalogs)==required,'native load completion duplicated');self.check_rows(remount)
            if not remount:self.old_first=self.cache[0];self.click(self.children[0],self.expected[0],'clicked')
            else:
                require(self.cache[0]==self.old_first and self.children[0]!=self.old_first and self.old_first.call_function('GetParent') is None,'original cached removed entry not retained');candidates=[exp for exp in self.catalogs[-1] if valid(exp) and exp.is_a(ue.find_class('LyraUserFacingExperienceDefinition')) and exp!=self.expected[0]];require(candidates,'fixture needs another original definition to distinguish stale cache');self.retarget=candidates[0];self.old_first.call_function('Set User Facing Experience',self.retarget);self.event_before=len(self.selections);self.event_expected=self.retarget;self.w.call_function('SelectFirstExperience');self.enter('first')
        elif self.phase=='clicked':
            if not self.delivered():return
            require(count(self.w,'click')>0,'actual entry-to-list native binding missing');self.row['actual_entry_click_native_delegate_and_parent_assignment']=True;self.parent.call_function('DeactivateWidget');self.parent.call_function('RemoveFromParent');self.frames=0;self.enter('unmounted')
        elif self.phase=='unmounted':
            self.frames+=1
            if self.frames<4:return
            self.mount(True)
        elif self.phase=='first':
            if not self.delivered():return
            self.row['actual_native_first_selection_uses_cached_old_entry']=True;self.click(self.old_first,self.retarget,'removed_click')
        elif self.phase=='removed_click':
            if not self.delivered():return
            self.row['actual_native_removed_entry_keeps_original_click_binding']=True;self.event_before=len(self.selections);self.w.call_function('SelectRandomExperience');self.enter('random')
        elif self.phase=='random':
            events=self.selections[self.event_before:]
            if not events:return
            require(len(events)==1 and events[0] in [tile.get_property('MyUserFacingExperience') for tile in self.cache] and self.parent.get_property('SelectedExperience')==events[0],'native random cache selection differs');self.row['actual_native_random_selection_from_accumulated_cache']=True;container=self.owned_widget(self.parent,'CollapsedContent');self.focus_container=container;self.hidden_before=int(container.call_function('GetVisibility'));require(self.hidden_before==1,'source selection caller hidden-list layout changed');self.visibility_scopes.append((container,self.hidden_before));container.call_function('SetVisibility',0);self.parent.call_function('ForceLayoutPrepass');self.row.update(fixture_collapsed_content_original_visibility=self.hidden_before,fixture_temporarily_expanded_for_focus=True);self.frames=0;self.enter('focus_visible')
        elif self.phase=='focus_visible':
            self.frames+=1
            if self.frames<3:return
            self.w.call_function('SetUserFocus',self.controller);self.frames=0;self.enter('list_focus')
        elif self.phase=='list_focus':
            self.frames+=1
            if self.frames<3:return
            scroller=self.w.get_property('ExperienceScroller');focus=dict(scroller_focusable=bool(scroller.call_function('GetIsFocusable')),list=bool(self.w.call_function('HasUserFocus',self.controller)),scroller=bool(scroller.call_function('HasUserFocus',self.controller)),descendant=bool(scroller.call_function('HasUserFocusedDescendants',self.controller)),buttons=[bool(tile.get_property('ExperienceTileButton').call_function('HasUserFocus',self.controller)) for tile in self.children],selection_buttons=[bool(self.parent.get_property(name).call_function('HasUserFocus',self.controller)) for name in ('QuickplayButton','BrowseButton','HostButton')]);self.report['latest_list_focus_outcome']=focus;require(count(self.w,'focus')>0 and (focus['list'] or focus['scroller'] or focus['descendant'] or any(focus['selection_buttons'])),'actual native list focus callback/outcome missing');self.matrix['list_focus_outcome']=focus;self.children[0].call_function('SetUserFocus',self.controller);self.frames=0;self.enter('tile_focus')
        elif self.phase=='tile_focus':
            self.frames+=1
            if self.frames<3:return
            tile=self.children[0];button=tile.get_property('ExperienceTileButton');focus=dict(entry=bool(tile.call_function('HasUserFocus',self.controller)),button=bool(button.call_function('HasUserFocus',self.controller)),button_descendant=bool(button.call_function('HasUserFocusedDescendants',self.controller)),button_focusable=bool(button.call_function('GetIsFocusable')));self.report['latest_tile_focus_outcome']=focus;require((focus['button'] or focus['button_descendant']) and sum(entry.evidence(tile)[p+'_focus'] for p in ('python','fallback'))>0,'native entry focus reply did not target its button or native internal focus child');self.matrix['tile_focus_outcome']=focus;self.row.update(actual_native_focus_replies_preserve_original_request_and_outcome=True,native_selection_events=len(self.selections),native_completed_loads=self.completed);self.focus_container.call_function('SetVisibility',self.hidden_before);self.parent.call_function('DeactivateWidget');self.parent.call_function('RemoveFromParent');self.report['trials'].append(self.row);self.states.append(self.matrix);self.index+=1
            if self.index<4:self.start_trial()
            else:self.report.update(source_python_state_pairs_match=self.states[:2]==self.states[2:],matrices=self.states);self.finish()
    def cleanup(self):
        for obj,name,fn in self.bindings:
            if valid(obj):obj.unbind_event(name,fn)
        for container,visibility in self.visibility_scopes:container.call_function('SetVisibility',visibility)
        self.report['fixture_collapsed_content_visibility_restored']=all(int(container.call_function('GetVisibility'))==visibility for container,visibility in self.visibility_scopes)
        for parent in self.parents:
            widget=parent.get_property('W_ExperienceList');ue.clear_mixin_profile(widget)
            if parent.call_function('IsActivated'):parent.call_function('DeactivateWidget')
            parent.call_function('StopAllAnimations');parent.call_function('RemoveFromParent');parent.remove_from_root()
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        if 'list' in self.classes:self.classes['list'].get_cdo().set_property('ShowAllExperiences',self.show_before)
        for cls in self.class_roots:cls.remove_from_root()
        self.report['owned_roots_profiles_and_show_all_restored']=all(not p.is_rooted() and not p.call_function('IsInViewport') for p in self.parents) and all(c.get_cdo().get_property('PythonMixinProfile')==v for c,v in self.cdos.items()) and (not self.classes or self.classes['list'].get_cdo().get_property('ShowAllExperiences')==self.show_before);self.report['original_gameplay_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,'native experience list timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPERIENCE_LIST_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPERIENCE_LIST_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExperienceListResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
