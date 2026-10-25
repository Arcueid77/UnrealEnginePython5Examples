"""Native scalar-slider input, Cancel/Apply and isolated local INI reload."""
import atexit,configparser,hashlib,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from . import settings_screens_mixin as screens,settings_editors_mixin as editors
from .settings_local_persistence_contract import FORBIDDEN,near,validate

def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def one(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value

class Validation:
    def __init__(self):
        self.path=Path(arg('UEPSettingsLocalResult'));self.user=Path(arg('UEPSettingsLocalUserRoot')).resolve()
        self.profile=arg('UEPSettingsLocalProfile');self.mode=arg('UEPSettingsLocalMode')
        self.started=time.monotonic();self.phase='ready';self.finished=False;self.widgets=[];self.roots=[];self.selectors={}
        self.report=dict(status='running',error=None,profile=self.profile,mode=self.mode,setting='OverallVolume',owned_user_root=str(self.user),native_pointer_events=[],native_screen_baselines=[])
        self.report.update(dict.fromkeys(FORBIDDEN,False))
    def require(self,value,message):
        if not value:raise AssertionError(message)
    def write(self):atomic_write(self.path,self.report)
    def enter(self,phase):self.phase=phase;self.report['phase']=phase;self.write()
    def value(self):return float(self.local.call_function('GetOverallVolume'))
    def files(self):return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.saved.rglob('*') if p.is_file() and p.suffix in ('.ini','.sav')}
    def ready(self):
        statics=lib('GameplayStatics')
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3):continue
            bridge=lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot')
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
            controller=statics.call_function('GetPlayerController',world,0)
            if not valid(controller):continue
            self.world,self.controller,self.bridge,self.health=world,controller,bridge,float(snap.Health)
            self.saved=Path(ue.convert_relative_path_to_full(one(lib('KismetSystemLibrary').call_function('GetProjectSavedDirectory')))).resolve()
            self.require(self.saved.is_relative_to(self.user),'Native save directory escapes owned UserDir')
            player=controller.get_property('Player');self.local=player.call_function('GetLocalSettings');self.shared=player.call_function('GetSharedSettings')
            self.require(valid(self.local) and valid(self.shared),'Native local/shared settings required')
            self.report.update(saved_path_owned=True,native_saved_directory=str(self.saved),native_mode=str(snap.NetMode),native_store='LyraSettingsLocal/GameUserSettings.ini')
            paths=set(screens.CLASSES.values())|set(editors.CLASSES.values());self.classes={p:ue.load_class(p) for p in paths}
            for cls in self.classes.values():
                if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
                self.selectors[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.profile)
            self.open_screen();return
    def create(self,cls):
        widget=lib('WidgetBlueprintLibrary').call_function('Create',self.world,cls,self.controller)
        widget.add_to_root();self.widgets.append(widget);widget.call_function('AddToPlayerScreen',0);return widget
    def open_screen(self):
        self.screen=self.create(self.classes[screens.CLASSES['screen']]);self.screen.call_function('GetSettingCollection','AudioCollection');self.screen.call_function('ActivateWidget')
        self.require(str(ue.get_mixin_profile(self.screen))==self.profile,'Wrong settings screen profile')
        self.setting=next(s for s in self.screen.get_property('Registry').get_property('RegisteredSettings') if str(s.call_function('GetDevName'))=='OverallVolume')
        self.host=self.create(ue.load_class('/Game/UI/Foundation/LoadingScreen/W_LoadingScreen_Host.W_LoadingScreen_Host_C'))
        self.view=ue.new_object(ue.find_class('GameSettingListView'),self.host.get_property('WidgetTree'))
        self.view.set_property('EntryWidgetClass',self.classes[editors.CLASSES['scalar']]);self.host.get_property('ExperienceSpecificWidgetSlot').call_function('SetContent',self.view)
        self.view.call_function('BP_SetListItems',[self.setting]);self.enter('reopen' if hasattr(self,'initial') else 'assigned')
    def entry(self):
        rows=self.view.call_function('GetDisplayedEntryWidgets')
        if len(rows)!=1:return None
        entry=rows[0];self.require(entry.get_property('Setting')==self.setting and str(ue.get_mixin_profile(entry))==self.profile,'Native scalar entry/profile differs')
        size=entry.get_property('Slider_SettingValue').take_widget().get_cached_geometry().get_local_size()
        return entry if size[0]>0. and size[1]>0. else None
    def pointer_to(self,target):
        before_value=self.value();self.require(not near(before_value,target),'Pointer must change the native setting')
        slider=self.entry_widget.get_property('Slider_SettingValue');slate=slider.take_widget();geometry=slate.get_cached_geometry();width,height=geometry.get_local_size()
        style=slider.get_property('WidgetStyle');sizes=[float(getattr(style,k).ImageSize.X) for k in ('NormalThumbImage','HoveredThumbImage','DisabledThumbImage')]
        self.require(len(set(sizes))==1,'Slider thumb widths differ;native pointer placement needs review')
        indent=sizes[0]*(2. if slider.get_property('IndentHandle') else 1.);x=indent*.5+(width-indent)*target
        absolute=one(lib('SlateBlueprintLibrary').call_function('LocalToAbsolute',slider.call_function('GetCachedGeometry'),ue.find_struct('Vector2D')(X=x,Y=height*.5)))
        pointer=ue.FPointerEvent(0,(float(absolute.x),float(absolute.y)),(float(absolute.x),float(absolute.y)),'LeftMouseButton')
        selected='python_' if self.profile=='Python' else 'fallback_';other='fallback_' if self.profile=='Python' else 'python_';before=dict(editors.evidence(self.entry_widget))
        handled=bool(slate.on_mouse_button_down(geometry,pointer));slate.on_mouse_button_up(geometry,pointer)
        after=editors.evidence(self.entry_widget);material=self.entry_widget.get_property('ProgressBar').call_function('GetDynamicMaterial')
        event=dict(entry='SSlider.OnMouseButtonDown',handled=handled,target=target,before=before_value,after=self.value(),ui_value=float(slider.call_function('GetValue')),
            material_progress=float(one(material.call_function('K2_GetScalarParameterValue','Progress'))),selected_callbacks=after[selected+'scalar_value']-before[selected+'scalar_value'],
            other_callbacks=after[other+'scalar_value']-before[other+'scalar_value'],native_geometry=[float(width),float(height)],synthetic_pointer_up_sent=True)
        self.report['native_pointer_events'].append(event)
        self.require(handled and near(event['after'],target) and near(event['ui_value'],target) and near(event['material_progress'],target),'Native slider/data source/material differs')
        # Native SetValue/Refresh may emit more than one value notification.
        # The final two-profile comparison checks their exact multiplicity.
        self.require(event['selected_callbacks']>0 and event['other_callbacks']==0,'Wrong scalar presentation path')
        self.require(self.screen.call_function('HaveSettingsBeenChanged'),'Native change tracker did not become dirty')
    def cancel(self,expected):
        before=self.files();self.screen.call_function('CancelChanges')
        self.require(near(self.value(),expected) and not self.screen.call_function('HaveSettingsBeenChanged'),'Native CancelChanges failed')
        self.require(self.files()==before,'Native CancelChanges changed a persistent file')
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
            before_value=self.value();before_files=self.files();dirty=bool(self.screen.call_function('HaveSettingsBeenChanged'))
            if dirty:self.screen.call_function('CancelChanges')
            self.report['native_screen_baselines'].append(dict(initially_dirty=dirty,original_cancel_used=dirty,value_before=before_value,value_after=self.value(),
                config_files_unchanged=self.files()==before_files,clean_after_cancel=not self.screen.call_function('HaveSettingsBeenChanged')))
            self.require(near(before_value,self.value()) and self.files()==before_files and not self.screen.call_function('HaveSettingsBeenChanged'),'Initial native cancel changed the loaded value/files or left dirty state')
            if self.phase=='reopen':
                self.require(near(self.value(),self.expected),'Reopen lost saved local value');self.report['same_process_reopen_keeps_saved']=True
                self.pointer_to(self.initial);self.cancel(self.expected);self.report['cancel_after_reopen_keeps_saved']=True;self.finish();return
            self.initial=self.value();self.require(0.<=self.initial<=1.,'Original scalar out of range')
            if self.mode=='read_restore':
                previous=read_json(Path(arg('UEPSettingsLocalWriteReport')))
                self.require(previous and previous['status']=='passed' and previous['profile']==self.profile and near(self.initial,previous['saved']),'Fresh process did not load saved local value')
                self.expected=previous['initial'];self.report['fresh_process_loaded_saved']=True
            else:self.expected=.5 if self.initial>=.75 else 1.
            self.report['initial']=self.initial;self.pointer_to(self.expected);self.cancel(self.initial)
            self.pointer_to(self.expected);self.screen.call_function('ApplyChanges')
            self.require(not self.screen.call_function('HaveSettingsBeenChanged'),'Native ApplyChanges left dirty state')
            self.report['dirty_state_cleared']=True;self.enter('save')
        elif self.phase=='save':
            if self.shared.call_function('IsSaveInProgress'):return
            self.require(self.shared.call_function('WasLastSaveSuccessful'),'Native companion save did not finish')
            self.require(near(self.value(),self.expected),'Native ApplyChanges lost selected local value')
            records=[]
            for path in self.saved.rglob('GameUserSettings.ini'):
                data=path.read_bytes();parser=configparser.RawConfigParser(strict=False);parser.read_string(data.decode('utf-8-sig'))
                section='/Script/LyraGame.LyraSettingsLocal'
                if not parser.has_option(section,'OverallVolume'):continue
                value=parser.getfloat(section,'OverallVolume');self.require(near(value,self.expected),'Native local INI contains the wrong volume')
                snapshot=self.path.parent/'native-local-config-at-apply.txt';snapshot.write_bytes(data)
                records.append(dict(path=str(path.resolve()),value=value,sha256=hashlib.sha256(data).hexdigest().upper(),snapshot=str(snapshot.resolve())))
            self.require(len(records)==1,'One owned native GameUserSettings.ini required')
            self.report.update(saved=self.expected,native_ini_saved=True,native_companion_save_complete=True,ini_files=records)
            if self.mode=='read_restore':self.report['original_owned_value_restored']=True;self.finish()
            else:self.close_screen();self.open_screen()
    def cleanup(self):
        if hasattr(self,'screen'):self.close_screen()
        for widget in self.widgets:
            if valid(widget):
                widget.call_function('RemoveFromParent')
                if widget.is_rooted():widget.remove_from_root()
        for cls,value in self.selectors.items():cls.get_cdo().set_property('PythonMixinProfile',value)
        for cls in self.roots:
            if cls.is_valid() and cls.is_rooted():cls.remove_from_root()
        self.report.update(selectors_roots_widgets_restored=all(not valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets)
            and all(cls.get_cdo().get_property('PythonMixinProfile')==value for cls,value in self.selectors.items()) and all(not c.is_rooted() for c in self.roots),
            health_unchanged=not hasattr(self,'bridge') or float(self.bridge.call_function('CaptureSnapshot').Health)==self.health)
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_SETTINGS_LOCAL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SETTINGS_LOCAL_SHUTDOWN_'+self.report['status'].upper())
    def tick(self,delta):
        try:
            self.require(time.monotonic()-self.started<180.,'Local settings timeout in '+self.phase)
            self.ready() if self.phase=='ready' else self.observe()
        except Exception:self.finish(traceback.format_exc())
        return not self.finished

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSettingsLocalResult=')),None)
if result:
    validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
