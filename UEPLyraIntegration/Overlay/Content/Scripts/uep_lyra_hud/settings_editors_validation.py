"""Native model assignment/localized options with real UMG animation frames."""
import atexit
import hashlib
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import settings_editors_mixin as policy
from .settings_editors_contract import PROFILES,FALSE_FIELDS,require,validate

HOVER=('background','action','discrete','keyboard','missing','scalar','collection')
CLICK_EVENTS=('BndEvt__SettingsListEntry_Discrete_Button_Decrease_K2Node_ComponentBoundEvent_0_CommonButtonBaseClicked__DelegateSignature','BndEvt__SettingsListEntry_Discrete_Button_Increase_K2Node_ComponentBoundEvent_1_CommonButtonBaseClicked__DelegateSignature')
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def count(w,k,m):return sum(policy.evidence(w)[p+'_'+k+'_'+m] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.profile_widgets=[];self.hosts=[];self.classes={};self.cdos={};self.index=0;self.states=[];self.delegates=[]
    def config_hashes(self):
        saved=Path(ue.convert_relative_path_to_full(ue.get_content_dir())).parent/'Saved/Config';return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in saved.rglob('GameUserSettings.ini')} if saved.exists() else {}
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.config_before=self.config_hashes();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'));self.input.call_function('SetCurrentInputType',0);require(int(self.input.call_function('GetCurrentInputType'))==0,'mouse input mode unavailable');self.geometry=ue.find_struct('Geometry')();self.pointer=ue.find_struct('PointerEvent')();self.probe=self.world.actor_spawn(ue.load_class('/Game/UEPValidation/BP_SettingsEditorProbe.BP_SettingsEditorProbe_C'))
        self.screen=self.create_class(ue.load_class('/Game/UI/Settings/W_LyraSettingScreen.W_LyraSettingScreen_C'),False);self.screen.call_function('GetSettingCollection','AudioCollection');self.registry=self.screen.get_property('Registry');self.registered=self.registry.get_property('RegisteredSettings');actions=[s for s in self.registered if s.is_a(ue.find_class('GameSettingAction'))];pages=[s for s in self.registered if s.is_a(ue.find_class('GameSettingCollectionPage'))];require(actions and pages,'real action/navigation settings unavailable');self.action_setting=next((s for s in actions if str(s.call_function('GetDevName'))=='AutoSetQuality'),actions[0]);self.page_setting=pages[0];choices=[]
        for s in self.registered:
            if s.is_a(ue.find_class('GameSettingValueDiscrete')):
                options=s.call_function('GetDiscreteOptions')
                if 2<=len(options)<=8:choices.append(s)
        require(choices,'real discrete setting options unavailable');self.setting=choices[0];self.setting_before=int(self.setting.call_function('GetDiscreteOptionIndex'));self.option_count=len(self.setting.call_function('GetDiscreteOptions'));self.report['native_model_dev_names']=[str(s.call_function('GetDevName')) for s in (self.action_setting,self.page_setting,self.setting)];self.start_profile()
    def create_class(self,cls,mount=True):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,cls,self.controller);w.add_to_root();self.widgets.append(w)
        if mount:w.call_function('AddToPlayerScreen',0)
        return w
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.current={k:self.create_class(c) for k,c in self.classes.items()}
        for w in self.current.values():ue.set_mixin_profile(w,self.profile);self.profile_widgets.append(w)
        self.row=dict(profile=self.profile);self.state={};self.hover_events=[];callback=lambda value:self.hover_events.append(bool(value));self.current['background'].bind_event('OnMouseEnterChanged',callback);self.delegates.append((self.current['background'],callback));self.assignment_host=self.create_class(ue.load_class('/Game/UI/Foundation/LoadingScreen/W_LoadingScreen_Host.W_LoadingScreen_Host_C'));tree=self.assignment_host.get_property('WidgetTree');box=ue.new_object(ue.find_class('VerticalBox'),tree);self.assignment_host.get_property('ExperienceSpecificWidgetSlot').call_function('SetContent',box);self.lists={}
        for k,setting in (('action',self.action_setting),('collection',self.page_setting)):
            view=ue.new_object(ue.find_class('GameSettingListView'),tree);view.set_property('EntryWidgetClass',self.classes[k]);box.call_function('AddChildToVerticalBox',view);view.call_function('BP_SetListItems',[setting]);self.lists[k]=view
        self.hosts.append(self.assignment_host);self.frames=0;self.enter('assign')
    def history(self,label,tag):
        file=self.path.parent/(self.profile+'-'+tag+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(label,str(file)),'settings native text export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [s.strip() for s in text.splitlines() if s.strip().startswith('Text=')]
    def material_value(self,image,n):return float(one(image.call_function('GetDynamicMaterial').call_function('K2_GetScalarParameterValue',n)))
    def models_assigned(self):
        result={}
        for k in ('action','collection'):
            entries=self.lists[k].call_function('GetDisplayedEntryWidgets')
            if len(entries)!=1:return None
            w=entries[0];require(w.get_class()==self.classes[k],'native ListView chose wrong entry class');require(w.get_property('Setting')==(self.action_setting if k=='action' else self.page_setting),'native ListView did not call SetSetting');button=w.get_property('Button_Action' if k=='action' else 'Button_Navigate');history=self.history(button.get_property('ButtonTextBlock'),k+'-assigned');require(any('NSLOCTEXT' in s for s in history),'native assignment label localization lost');result[k]=history
        return result
    def focus_cases(self):
        rows=[]
        for k,n in policy.FOCUS.items():w=self.current[k];actual=one(w.call_function('GetPrimaryGamepadFocusWidget'));require(actual==w.get_property(n),'typed primary gamepad focus target differs');rows.append(dict(widget=k,target=n))
        self.row.update(focus_cases=5,typed_gamepad_focus_targets_match=True);return rows
    def scalar_cases(self):
        w=self.current['scalar'];image=w.get_property('ProgressBar');values=[];defaults=[]
        for v in (-.25,0.,.5,1.,1.25):w.call_function('OnValueChanged',v);actual=self.material_value(image,'Progress');require(actual==v,'scalar visual progress must remain raw');values.append(actual)
        for v in (-.25,.5,1.25):w.call_function('OnDefaultValueChanged',v);actual=self.material_value(image,'DefaultValue');require(actual==v,'scalar default visual value differs');defaults.append(actual)
        self.row.update(scalar_value_cases=5,scalar_default_cases=3,scalar_raw_values_and_defaults_match=True);return dict(values=values,defaults=defaults)
    def rotator_cases(self):
        w=self.current['rotator'];rows=[]
        for value in (-1,0,3,4,5,6,7,8,12):
            w.call_function('SetPipsStyle',value);expected=3 if value>7 else 2 if value>5 else 1 if value>3 else 0;image=w.get_property('OptionsPips');material=image.call_function('GetDynamicMaterial');row=dict(count=value,width=float(w.get_property('OptionsScalingSizeBox').get_property('WidthOverride')),parent=path(material.get_property('Parent')),options=float(one(material.call_function('K2_GetScalarParameterValue','Options'))));require(row['width']==(192.,256.,320.,384.)[expected] and row['parent']==policy.PIP_MATERIALS[expected] and row['options']==value,'strict rotator threshold/local count differs');rows.append(row)
        w.call_function('PopulateTextLabels',['one','two','three']);require(count(w,'rotator','style')>0,'native options population did not forward style');before=count(w,'rotator','selected');w.call_function('SetSelectedItem',1);require(count(w,'rotator','selected')>before,'native option selection callback missing');indices=[]
        for v in (-2,-1,0,1,99):w.call_function('BP_OnOptionSelected',v);w.call_function('BP_OnDefaultOptionSpecified',v);a=self.material_value(w.get_property('OptionsPips'),'SelectedOption');b=self.material_value(w.get_property('OptionsPips'),'DefaultOption');require(a==b==v,'raw rotator indices were changed');indices.append([a,b])
        self.row.update(rotator_style_cases=9,rotator_index_cases=5,rotator_native_population_selection_and_raw_material_values=True,rotator_strict_width_material_thresholds_and_local_count=True);return dict(styles=rows,indices=indices)
    def detail_cases(self):
        w=self.current['details'];rows=[]
        for selected in (False,True):
            self.probe.call_function('SetupDetails',w,selected);history=self.history(w.get_property('EntryText'),'details-'+str(selected));materials=(w.get_property('EntryText').call_function('GetDynamicFontMaterial'),w.get_property('Diamond').call_function('GetDynamicMaterial'),w.get_property('EntryBorder').call_function('GetDynamicMaterial'));values=[float(one(m.call_function('K2_GetScalarParameterValue','Hover_Animate'))) for m in materials];require(values==[1. if selected else 0.]*3 and any('NSLOCTEXT' in s for s in history),'native details label/material state differs');rows.append(dict(selected=selected,history=history,values=values))
        self.row['details_native_text_precedes_selected_material_update']=True;return rows
    def enum_cases(self):
        w=self.current['extension'];box=w.get_property('EnumOptions');w.call_function('RebuildOptions',self.setting);entries=list(box.call_function('GetAllEntries'));require(len(entries)==self.option_count,'native localized enum entry count differs');rows=[]
        for index,entry in enumerate(entries):
            label=entry.get_property('EntryText');history=self.history(label,'enum-'+str(index));material=entry.get_property('EntryBorder').call_function('GetDynamicMaterial');value=float(one(material.call_function('K2_GetScalarParameterValue','Hover_Animate')));display=policy.lib('KismetTextLibrary').call_function('Conv_TextToString',label.call_function('GetText'));require(display==self.setting.call_function('GetDiscreteOptions')[index] and value==(1. if index==self.setting_before else 0.) and any('NSLOCTEXT' in s for s in history),'enum localized order/selection differs');rows.append(dict(history=history,value=value,display=display))
        w.call_function('RebuildOptions',self.setting);again=list(box.call_function('GetAllEntries'));require(set(entries)==set(again),'Reset(false) must retain/reuse pooled widgets');w.call_function('RebuildOptions',None);require(not box.call_function('GetAllEntries'),'invalid setting must reset entries');self.row.update(enum_option_count=self.option_count,enum_native_localized_options_selection_order_and_pool_reuse=True,enum_invalid_setting_resets_without_deleting_pool=True);return rows
    def mouse(self,enter):
        for k in HOVER:self.current[k].call_function('OnMouseEnter' if enter else 'OnMouseLeave',*([self.geometry,self.pointer] if enter else [self.pointer]))
    def animation(self,k):
        w=self.current[k];a=w.get_property('OnHovered' if k=='background' else 'OnHover');return float(w.call_function('GetAnimationCurrentTime',a)),bool(w.call_function('IsAnimationPlayingForward',a))
    def observe(self):
        require(time.monotonic()-self.phase_started<25.,'settings editor phase timeout: '+self.phase)
        if self.phase=='assign':
            assignments=self.models_assigned()
            if assignments is None:return
            self.row['actual_native_list_assignment_preserves_localized_action_and_navigation_labels']=True;self.state.update(assignments=assignments,focus=self.focus_cases(),scalar=self.scalar_cases(),rotator=self.rotator_cases(),details=self.detail_cases(),enum=self.enum_cases());before=count(self.current['discrete'],'discrete','sound')
            for name in CLICK_EVENTS:self.current['discrete'].call_function(name)
            require(count(self.current['discrete'],'discrete','sound')==before+2,'both discrete component callback sound routes missing');self.row['discrete_both_component_callback_sound_paths']=True;self.mouse(True);self.enter('hover')
        elif self.phase=='hover':
            if not all(self.animation(k)[0]>=.005 for k in HOVER):return
            require(all(self.animation(k)[1] for k in HOVER),'real hover animations not forward');require(self.hover_events==[True],'background native enter multicast order differs');self.mouse(False);require(self.hover_events==[True,False],'background native leave multicast order differs');self.row.update(hover_widget_cases=7,manual_pointer_callbacks_and_actual_hover_animation_frames=True,background_actual_multicast_enter_leave_order=True);self.report['profiles'].append(self.row);self.states.append(self.state);self.report['matrices']=self.states
            for w in self.current.values():w.call_function('RemoveFromParent')
            for view in self.lists.values():view.call_function('ClearListItems')
            self.assignment_host.call_function('RemoveFromParent');self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report['source_python_state_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        for w,fn in self.delegates:
            if policy.valid(w):w.unbind_event('OnMouseEnterChanged',fn)
        if hasattr(self,'lists'):
            for view in self.lists.values():view.call_function('ClearListItems')
        if hasattr(self,'probe') and policy.valid(self.probe):self.probe.actor_destroy()
        for w in self.widgets:
            if w in self.profile_widgets:ue.clear_mixin_profile(w)
            w.call_function('StopAllAnimations');w.call_function('RemoveFromParent');w.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before);self.report['native_input_type_restored']=int(self.input.call_function('GetCurrentInputType'))==self.input_before
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for c in getattr(self,'class_roots',[]):c.remove_from_root()
        self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['native_selected_setting_index_unchanged']=not hasattr(self,'setting') or int(self.setting.call_function('GetDiscreteOptionIndex'))==self.setting_before;self.report['settings_config_files_unchanged']=not hasattr(self,'config_before') or self.config_hashes()==self.config_before;self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<250.,'native settings presentation timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SETTINGS_EDITORS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SETTINGS_EDITORS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSettingsEditorsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
