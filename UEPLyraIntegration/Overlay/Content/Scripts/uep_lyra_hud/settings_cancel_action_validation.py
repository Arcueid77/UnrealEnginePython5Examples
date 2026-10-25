"""Real bound Cancel Changes action after native scalar-slider interaction."""
import atexit,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from .ui_back_navigation_validation import Validation as BackValidation,menu,bound
from .settings_local_persistence_validation import Validation as ScalarValidation,editors,one
from .settings_cancel_action_contract import FORBIDDEN,near,validate

class Validation(BackValidation):
    pointer_to=ScalarValidation.pointer_to
    files=ScalarValidation.files
    entry=ScalarValidation.entry
    def __init__(self,result):
        super().__init__(result);self.extra=[];self.report['native_pointer_events']=[];self.report.update(dict.fromkeys(FORBIDDEN,False))
        cls=ue.load_class(editors.CLASSES['scalar']);self.classes['scalar']=cls
        if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
        self.selectors.append((cls,cls.get_cdo().get_property('PythonMixinProfile')));cls.get_cdo().set_property('PythonMixinProfile',self.profile)
    def require(self,value,message):
        if not value:raise AssertionError(message)
    def value(self):return float(self.local.call_function('GetOverallVolume'))
    def begin(self):
        self.local=self.controller.get_property('Player').call_function('GetLocalSettings');self.shared=self.controller.get_property('Player').call_function('GetSharedSettings')
        self.saved=Path(ue.convert_relative_path_to_full(one(menu.lib('KismetSystemLibrary').call_function('GetProjectSavedDirectory')))).resolve()
        user=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSettingsCancelUserRoot='))).resolve()
        self.require(self.saved.is_relative_to(user),'Native Cancel file observation escapes owned UserDir');self.report['saved_path_owned']=True
        super().begin()
    def actions(self,word):
        matches=[]
        for bar in ue.tobject_iterator(ue.find_class('CommonBoundActionBar')):
            for button in bar.call_function('GetAllEntries'):
                if not menu.valid(button) or not button.is_a(self.classes['back']) or button.call_function('GetOwningPlayer')!=self.controller:continue
                label=str(button.get_property('Text_ActionName').call_function('GetText'))
                matched=True if word is None else ('cancel' in label.casefold()) if word=='cancel' else label=='Back'
                if matched:matches.append((button,label))
        return matches
    def start_scalar(self):
        self.initial=self.value();self.row['initial']=self.initial;self.screen.call_function('GetSettingCollection','AudioCollection')
        self.setting=next(s for s in self.screen.get_property('Registry').get_property('RegisteredSettings') if str(s.call_function('GetDevName'))=='OverallVolume')
        self.host=menu.lib('WidgetBlueprintLibrary').call_function('Create',self.world,ue.load_class('/Game/UI/Foundation/LoadingScreen/W_LoadingScreen_Host.W_LoadingScreen_Host_C'),self.controller)
        self.host.add_to_root();self.extra.append(self.host);self.host.call_function('AddToPlayerScreen',0)
        self.view=ue.new_object(ue.find_class('GameSettingListView'),self.host.get_property('WidgetTree'));self.view.set_property('EntryWidgetClass',self.classes['scalar'])
        self.host.get_property('ExperienceSpecificWidgetSlot').call_function('SetContent',self.view);self.view.call_function('BP_SetListItems',[self.setting]);self.enter('scalar');self.frames=0
    def click_cancel(self,kind):
        actions=self.actions('cancel')
        if len(actions)!=1:return False
        button,label=actions[0];self.require(str(ue.get_mixin_profile(button))==self.profile,'Native Cancel button uses another profile')
        before=dict(bound.evidence(button));self.cancel_files_before=self.files();self.cancel_value_before=self.value()
        button.call_function('HandleButtonClicked');after=bound.evidence(button)
        self.cancel_receipt=dict(kind=kind,label=label,native_entry='CommonBoundActionButton.HandleButtonClicked',profile_matches=True,
            selected_clicks=after[self.selected+'click']-before[self.selected+'click'],other_clicks=after[self.other+'click']-before[self.other+'click'],value_before=self.cancel_value_before)
        self.enter('baseline_cancel' if kind=='initial' else 'cancelled');self.frames=0;return True
    def start_input(self):
        self.require(near(self.value(),self.initial),'Native baseline did not retain loaded volume')
        self.target=.5 if self.initial>=.75 else 1.;self.row['target']=self.target;self.pointer_to(self.target)
        self.row['pointer']=dict(self.report['native_pointer_events'][-1]);self.enter('cancel_available');self.frames=0
    def observe(self):
        if self.phase=='menu':return super().observe()
        self.require(time.monotonic()-self.phase_started<30.,'Native settings Cancel timeout in '+self.phase+'; '+str(self.report.get('pending')));self.frames+=1
        if self.phase=='settings':
            screens=[w for w in ue.tobject_iterator(self.classes['screen']) if w.call_function('GetOwningPlayer')==self.controller and w.call_function('IsActivated')]
            if len(screens)!=1:return
            self.screen=self.own(screens[0])
            if self.frames<8 or not self.focused(self.screen):return
            self.row['settings_native_focus']=True;self.start_scalar()
        elif self.phase=='scalar':
            entry=self.entry()
            if entry is None or self.shared.call_function('IsSaveInProgress'):return
            self.entry_widget=entry;dirty=bool(self.screen.call_function('HaveSettingsBeenChanged'));self.row['initially_dirty']=dirty
            if dirty:self.click_cancel('initial')
            else:self.start_input()
        elif self.phase=='baseline_cancel':
            if self.frames<12:return
            receipt=dict(self.cancel_receipt,value_after=self.value(),files_unchanged=self.files()==self.cancel_files_before,clean=not self.screen.call_function('HaveSettingsBeenChanged'),screen_active=bool(self.screen.call_function('IsActivated')))
            self.row['baseline_cancel']=receipt
            self.require(receipt['files_unchanged'] and receipt['clean'] and receipt['screen_active'] and near(receipt['value_after'],self.initial),'Initial bound Cancel changed saved state');self.start_input()
        elif self.phase=='cancel_available':
            if self.shared.call_function('IsSaveInProgress'):return
            self.report['pending']=dict(active_actions=[label for _,label in self.actions('cancel')],dirty=bool(self.screen.call_function('HaveSettingsBeenChanged')))
            self.require(self.screen.call_function('HaveSettingsBeenChanged'),'Scalar input did not expose native dirty state');self.click_cancel('edited')
        elif self.phase=='cancelled':
            if self.frames<12:return
            material=self.entry_widget.get_property('ProgressBar').call_function('GetDynamicMaterial');slider=self.entry_widget.get_property('Slider_SettingValue')
            self.row.update(cancel=dict(self.cancel_receipt,value_after=self.value(),ui_after=float(slider.call_function('GetValue')),material_after=float(one(material.call_function('K2_GetScalarParameterValue','Progress'))),
                screen_active=bool(self.screen.call_function('IsActivated')),clean=not self.screen.call_function('HaveSettingsBeenChanged'),files_before=self.cancel_files_before,files_after=self.files(),cancel_action_removed=not self.actions('cancel')))
            result=self.row['cancel'];self.require(near(result['value_after'],self.initial) and near(result['ui_after'],self.initial) and near(result['material_after'],self.initial) and result['screen_active'] and result['clean'] and result['files_before']==result['files_after'] and result['cancel_action_removed'],'Bound Cancel did not roll back without save/pop')
            self.report['pending_case']=self.row;self.clear_extra();self.enter('return_available');self.frames=0
        elif self.phase=='return_available':
            actions=self.actions('back')
            self.report['pending']=dict(active_action_labels=[label for _,label in self.actions(None)],back_actions=len(actions),screen_active=bool(self.screen.call_function('IsActivated')))
            if not actions:return
            # Different native action bars can display the same player's Back
            # action. Observe the actual target close rather than inventing a
            # globally unique visual-button requirement.
            self.row['native_back_candidates']=[button.get_path_name() for button,_ in actions]
            self.row['native_back_clicked']=actions[0][0].get_path_name()
            actions[0][0].call_function('HandleButtonClicked');self.enter('closed');self.frames=0
        elif self.phase=='closed':
            if self.frames<12 or self.screen.call_function('IsActivated') or self.shared.call_function('IsSaveInProgress'):return
            self.row.update(native_back_after_cancel_closed=True,volume_still_original=near(self.value(),self.initial),world_unchanged=self.world.get_path_name()==self.world_path,health_unchanged=self.healths()==self.health_before)
            self.report['cases'].append(self.row);self.clear_extra();self.cycle+=1
            if self.cycle==2:self.finish()
            else:self.start_cycle()
    def clear_extra(self):
        if hasattr(self,'view') and menu.valid(self.view):self.view.call_function('ClearListItems')
        for widget in self.extra:
            if menu.valid(widget):
                widget.call_function('RemoveFromParent')
                if widget.is_rooted():widget.remove_from_root()
    def cleanup(self):
        self.clear_extra();super().cleanup()
        self.report['scalar_fixture_unmounted_and_unrooted']=all(not menu.valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.extra)
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_SETTINGS_CANCEL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SETTINGS_CANCEL_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSettingsCancelResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
