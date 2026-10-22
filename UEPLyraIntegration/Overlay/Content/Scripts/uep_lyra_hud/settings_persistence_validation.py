"""Opt-in native settings UI save/cancel test inside an isolated user directory."""
import atexit
import hashlib
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from . import settings_screens_mixin as screens,settings_editors_mixin as editors
from .settings_persistence_contract import validate


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def one(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPSettingsPersistenceResult'));self.user=Path(arg('UEPSettingsPersistenceUserRoot')).resolve()
        self.profile=arg('UEPSettingsPersistenceProfile');self.mode=arg('UEPSettingsPersistenceMode')
        self.started=time.monotonic();self.phase='ready';self.finished=False;self.widgets=[];self.class_roots=[];self.selectors={};self.clicks=0;self.policy_calls=0
        self.report=dict(status='running',error=None,profile=self.profile,mode=self.mode,setting='GamepadVibration',owned_user_root=str(self.user),
            full_acceptance=False,direct_settings_setter_called=False,configuration_files_written_by_python=False,physical_keyboard_or_pointer_tested=False)

    def require(self, value, message):
        if not value:raise AssertionError(message)

    def write(self):atomic_write(self.path,self.report)

    def enter(self, phase):self.phase=phase;self.report['phase']=phase;self.write()

    def ready(self):
        statics=lib('GameplayStatics')
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3):continue
            bridge=lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot')
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
            controller=statics.call_function('GetPlayerController',world,0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):continue
            self.world,self.controller,self.bridge=world,controller,bridge;self.health=float(snap.Health)
            saved=Path(ue.convert_relative_path_to_full(one(lib('KismetSystemLibrary').call_function('GetProjectSavedDirectory')))).resolve()
            self.require(saved.is_relative_to(self.user),'native save directory is outside owned UserDir')
            self.saved=saved;self.report.update(saved_path_owned=True,native_saved_directory=str(saved),native_mode=str(snap.NetMode))
            self.shared=controller.get_property('Player').call_function('GetSharedSettings')
            self.require(valid(self.shared),'native shared settings unavailable')
            paths=set(screens.CLASSES.values())|set(editors.CLASSES.values())
            self.classes={p:ue.load_class(p) for p in paths}
            for cls in self.classes.values():
                if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
                self.selectors[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.profile)
            self.open_screen();return

    def create(self, cls):
        widget=lib('WidgetBlueprintLibrary').call_function('Create',self.world,cls,self.controller)
        widget.add_to_root();self.widgets.append(widget);widget.call_function('AddToPlayerScreen',0);return widget

    def open_screen(self):
        self.screen=self.create(self.classes[screens.CLASSES['screen']]);self.screen.call_function('GetSettingCollection','GamepadCollection')
        self.require(str(ue.get_mixin_profile(self.screen))==self.profile,'screen effective profile differs from requested profile')
        self.screen.call_function('ActivateWidget');registry=self.screen.get_property('Registry')
        self.setting=next(s for s in registry.get_property('RegisteredSettings') if str(s.call_function('GetDevName'))=='GamepadVibration')
        self.host=self.create(ue.load_class('/Game/UI/Foundation/LoadingScreen/W_LoadingScreen_Host.W_LoadingScreen_Host_C'))
        tree=self.host.get_property('WidgetTree');self.view=ue.new_object(ue.find_class('GameSettingListView'),tree)
        self.view.set_property('EntryWidgetClass',self.classes[editors.CLASSES['discrete']])
        self.host.get_property('ExperienceSpecificWidgetSlot').call_function('SetContent',self.view)
        self.view.call_function('BP_SetListItems',[self.setting]);self.enter('reopen' if hasattr(self,'initial') else 'assigned')

    def entry(self):
        rows=self.view.call_function('GetDisplayedEntryWidgets')
        if len(rows)!=1:return None
        value=rows[0];self.require(value.get_property('Setting')==self.setting,'native ListView did not assign the real setting')
        self.require(str(ue.get_mixin_profile(value))==self.profile,'entry effective profile differs from requested profile');return value

    def index(self):return int(one(self.setting.call_function('GetDiscreteOptionIndex')))

    def files(self):
        return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.saved.rglob('*') if p.is_file() and p.suffix in ('.sav','.ini')}

    def click_to(self, target):
        current=self.index();self.require(current!=target,'test click requires an actual value change')
        button=self.entry_widget.get_property('Button_Increase' if target>current else 'Button_Decrease')
        self.require(button.call_function('IsInteractionEnabled'),'native setting button is not interactable')
        counter=('python' if self.profile=='Python' else 'fallback')+'_discrete_sound'
        before=editors.evidence(self.entry_widget)[counter]
        button.call_function('HandleButtonClicked');self.clicks+=1
        self.require(editors.evidence(self.entry_widget)[counter]==before+1,'selected profile did not receive the actual button component callback')
        self.policy_calls+=1;self.report['effective_profiles_match']=True
        self.require(self.index()==target,'native button did not update the selected setting')
        self.require(bool(self.shared.call_function('GetForceFeedbackEnabled'))==bool(target),'native setting data source differs from UI')
        self.require(self.screen.call_function('HaveSettingsBeenChanged'),'native change tracker did not become dirty')

    def cancel(self, expected):
        before=self.files();self.screen.call_function('CancelChanges')
        self.require(self.index()==expected and not self.screen.call_function('HaveSettingsBeenChanged'),'native CancelChanges did not restore the initial value')
        self.require(self.files()==before,'CancelChanges wrote persistent files')
        self.report.update(cancel_restores_initial=True,cancel_does_not_write_files=True)

    def close_screen(self):
        if hasattr(self,'view') and valid(self.view):self.view.call_function('ClearListItems')
        for widget in (self.screen,self.host):
            if valid(widget):
                if widget==self.screen and widget.call_function('IsActivated'):widget.call_function('DeactivateWidget')
                widget.call_function('RemoveFromParent')
                if widget.is_rooted():widget.remove_from_root()

    def observe(self):
        if self.phase in ('assigned','reopen'):
            entry=self.entry()
            if entry is None:return
            self.entry_widget=entry
            self.require(not self.screen.call_function('HaveSettingsBeenChanged'),'new screen starts dirty')
            if self.phase=='reopen':
                self.require(self.index()==self.expected,'reopened screen lost the saved setting')
                self.report['same_process_reopen_keeps_saved']=True;self.click_to(self.initial);self.cancel(self.expected)
                self.report['cancel_after_reopen_keeps_saved']=True;self.finish();return
            self.initial=self.index();self.require(self.initial in (0,1),'expected a real bool setting')
            if self.mode=='read_restore':
                previous=read_json(Path(arg('UEPSettingsPersistenceWriteReport')))
                self.require(previous and previous['status']=='passed' and self.initial==previous['saved'] and self.shared.call_function('WasLoaded'),'fresh process did not load the actual saved value')
                self.report['fresh_process_loaded_saved']=True
            self.report['initial']=self.initial;self.click_to(1-self.initial);self.cancel(self.initial)
            self.expected=1-self.initial;self.click_to(self.expected);self.screen.call_function('ApplyChanges')
            self.require(not self.screen.call_function('HaveSettingsBeenChanged'),'ApplyChanges did not clear dirty state')
            self.report['dirty_state_cleared']=True;self.enter('save')
        elif self.phase=='save':
            if self.shared.call_function('IsSaveInProgress'):return
            self.require(self.shared.call_function('WasLastSaveSuccessful'),'native asynchronous save failed')
            self.require(self.index()==self.expected,'native ApplyChanges lost the chosen value')
            files=self.files();saves=[dict(path=p,sha256=h) for p,h in files.items() if p.endswith('.sav')]
            self.require(saves,'native save reported success without an owned save file')
            self.report.update(saved=self.expected,native_async_save_success=True,save_files=saves,native_save_slot=str(self.shared.call_function('GetSaveSlotName')))
            if self.mode=='read_restore':self.report['original_owned_value_restored']=True;self.finish()
            else:self.close_screen();self.open_screen()

    def cleanup(self):
        if hasattr(self,'screen'):self.close_screen()
        for widget in self.widgets:
            if valid(widget):
                widget.call_function('RemoveFromParent')
                if widget.is_rooted():widget.remove_from_root()
        for cls,value in self.selectors.items():cls.get_cdo().set_property('PythonMixinProfile',value)
        for cls in self.class_roots:
            if cls.is_valid() and cls.is_rooted():cls.remove_from_root()
        self.report['selectors_roots_widgets_restored']=(all(not valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets)
            and all(cls.get_cdo().get_property('PythonMixinProfile')==value for cls,value in self.selectors.items())
            and all(not cls.is_valid() or not cls.is_rooted() for cls in self.class_roots))
        self.report['health_unchanged']=not hasattr(self,'bridge') or float(self.bridge.call_function('CaptureSnapshot').Health)==self.health

    def finish(self, error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error,native_button_handler_calls=self.clicks,selected_profile_callback_entries=self.policy_calls);self.write()
        (ue.log_error if error else ue.log)('UEP_SETTINGS_PERSISTENCE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SETTINGS_PERSISTENCE_SHUTDOWN_'+self.report['status'].upper())

    def tick(self, delta):
        try:
            self.require(time.monotonic()-self.started<180,'settings persistence timeout in '+self.phase)
            self.ready() if self.phase=='ready' else self.observe()
        except Exception:self.finish(traceback.format_exc())
        return not self.finished


validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
