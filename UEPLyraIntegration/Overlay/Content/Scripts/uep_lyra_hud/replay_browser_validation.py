"""Native recordings and real replay rows in a fresh process-owned UserDir."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import replay_browser_mixin as policy,replay_entry_mixin as entry_policy
from .replay_browser_contract import FALSE_FIELDS,require,validate
def arg(name,default):return next((v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'=')),default)
def path(value):return value.get_path_name() if value is not None else None
def count(w,key,entry=False):return sum((entry_policy if entry else policy).evidence(w)[p+'_'+key] for p in ('python','fallback'))
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_local_playing_phase=False;self.profile=arg('UEPReplayBrowserProfile','Python');self.report=dict(status='running',error=None,profile=self.profile,direct_interface_inputs=['null','wrong replay-list object','retarget to older real replay during confirmation']);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.cdos={};self.class_roots=[];self.widgets=[];self.roots=[];self.dialogs=[];self.names=[];self.dialog_results=[];self.arrived=False;self.settings_before=None;self.stop_flag_before=None
    def begin(self):
        saved=Path(ue.convert_relative_path_to_full(policy.lib('KismetSystemLibrary').call_function('GetProjectSavedDirectory'))).resolve();require(saved.is_relative_to((self.path.parent/'User').resolve()),'native Saved/Demos must be isolated inside this run');self.report['isolated_native_saved_directory_verified']=True;self.report['native_saved_directory']=str(saved);self.replay_folder=saved/'Demos';require(not self.replay_folder.exists() or not list(self.replay_folder.glob('*.replay')),'fresh isolated replay folder required');self.health_before=self.healths();self.original_world=self.world;self.original_controller=self.controller;self.original_level=policy.lib('GameplayStatics').call_function('GetCurrentLevelName',self.world,True);self.engine=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('ReplaySubsystem'));self.lyra=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('LyraReplaySubsystem'));require(self.lyra.call_function('DoesPlatformSupportReplays') and not self.engine.call_function('IsRecording') and not self.engine.call_function('IsPlaying'),'native fresh supported replay context required');self.settings=policy.lib('GameUserSettings').call_function('GetGameUserSettings');self.settings_before=bool(self.settings.call_function('ShouldAutoRecordReplays'));self.stop_flag_before=bool(self.engine.get_property('bLoadDefaultMapOnStop'));self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'))
        for name in (policy.CLASS,entry_policy.CLASS,'/Game/UI/Foundation/Buttons/W_LyraButton.W_LyraButton_C','/Game/UI/Foundation/Dialogs/W_ConfirmationDialog.W_ConfirmationDialog_C'):
            cls=ue.load_class(name)
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            ue.register_declared_mixin(cls);self.cdos[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.browser=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,ue.load_class(policy.CLASS),self.controller);self.browser.add_to_root();self.roots.append(self.browser);self.widgets.append(self.browser);ue.set_mixin_profile(self.browser,self.profile);self.browser.call_function('AddToPlayerScreen',0);self.browser.call_function('ActivateWidget');require(count(self.browser,'search')==1 and count(self.browser,'results')==0,'native initial query must be in progress');self.browser.call_function('StartSearch');ue.set_mixin_profile(self.browser,'Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback');self.browser.call_function('StartSearch');require(count(self.browser,'search')==1,'native DoOnce failed across Profile switch');self.report['native_shared_do_once_blocks_duplicate_across_profile_switch']=True;self.enter('empty')
    def console(self,command):policy.lib('KismetSystemLibrary').call_function('ExecuteConsoleCommand',self.world,command,self.controller)
    def start_record(self):
        self.files_before={p.resolve() for p in self.replay_folder.glob('*.replay')};self.settings.call_function('SetShouldAutoRecordReplays',True);require(self.controller.call_function('TryToRecordClientReplay') and self.engine.call_function('IsRecording'),'actual controller record request failed');self.enter('record_start')
    def history(self,obj,key,label):
        file=self.path.parent/(self.profile+'-'+label+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file)),'native replay label export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');rows=[line.strip() for line in text.splitlines() if line.strip().startswith(key+'=')];require(len(rows)==1 and 'NSLOCTEXT' in rows[0],'native replay localized history missing');return rows[0]
    def show_dialog(self,phase):
        self.entry.get_property('LyraButton').call_function('HandleButtonClicked');self.enter(phase)
    def dialog(self):
        dialogs=[w for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen')) if w.call_function('IsActivated')]
        if not dialogs:return None
        require(len(dialogs)==1,'native replay dialog duplicated');dialog=dialogs[0]
        if dialog not in self.dialogs:self.dialogs.append(dialog)
        return dialog
    def observe(self):
        require(time.monotonic()-self.phase_started<(120. if self.phase=='playback' else 35.),'replay browser phase timeout: '+self.phase)
        if self.phase=='empty':
            if count(self.browser,'results')<1:return
            require(count(self.browser,'results')==count(self.browser,'unlock')==1 and not list(self.browser.get_property('ResultList').get_property('Results')) and self.browser.call_function('BP_GetDesiredFocusTarget')==self.browser.get_property('RefreshButton') and int(self.browser.get_property('ProgressSpinner').call_function('GetVisibility'))==1,'native empty query/focus/unlock differs');ue.set_mixin_profile(self.browser,self.profile);self.report['native_initial_empty_query_and_const_focus']=True;self.start_record()
        elif self.phase=='record_start':
            files=[p for p in self.replay_folder.glob('*.replay') if p.resolve() not in self.files_before]
            if not files:return
            require(len(files)==1 and files[0].stem not in self.names,'native generated replay ID missing/duplicated');self.names.append(files[0].stem);self.enter('record')
        elif self.phase=='record':
            if float(self.engine.call_function('GetReplayCurrentTime'))<(3. if len(self.names)==1 else 5.):return
            self.console('demostop');self.enter('flushed')
        elif self.phase=='flushed':
            if self.engine.call_function('IsRecording'):return
            if len(self.names)<2:self.frames=0;self.enter('gap')
            else:
                files=sorted(self.replay_folder.glob('*.replay'));require(len(files)==2 and {p.stem for p in files}==set(self.names) and all(p.stat().st_size>0 for p in files),'two actual isolated replay files missing');self.report.update(native_record_and_stop_two_real_replays=True,recording_count=2,recorded_replay_names=self.names,native_replay_files=[str(p.resolve()) for p in files]);self.browser.get_property('RefreshButton').call_function('HandleButtonClicked');self.browser.call_function('StartSearch');require(count(self.browser,'search')==2,'native refresh DoOnce differs');self.enter('rows')
        elif self.phase=='gap':
            self.frames+=1
            if self.frames>=20:self.start_record()
        elif self.phase=='rows':
            if count(self.browser,'results')<2:return
            self.results=list(self.browser.get_property('ResultList').get_property('Results'));listing=self.browser.get_property('ReplayListWidget');require(count(self.browser,'results')==count(self.browser,'unlock')==2 and len(self.results)==2 and list(listing.call_function('GetListItems'))==self.results,'native result object/order/list replacement differs');require(policy.lib('KismetMathLibrary').call_function('Greater_DateTimeDateTime',self.results[0].call_function('GetTimestamp'),self.results[1].call_function('GetTimestamp')),'native query timestamps are not newest first');entries=list(listing.call_function('GetDisplayedEntryWidgets'));entries=[w for w in entries if w.get_property('As Lyra Replay List Entry')==self.results[0]]
            if not entries:return
            self.entry=entries[0];self.entry.add_to_root();self.roots.append(self.entry);self.widgets.append(self.entry);button=self.entry.get_property('LyraButton');expected=str(self.results[0].call_function('GetFriendlyName'))+' ('+str(policy.lib('KismetTextLibrary').call_function('AsTimespan_Timespan',self.results[0].call_function('GetDuration')))+')';require(str(button.get_property('ButtonText'))==expected,'native friendly name/duration text differs');self.report['native_row_text_history']=self.history(button,'ButtonText','row-text');self.report.update(native_query_identity_and_timestamp_order_preserved=True,native_generated_row_localized_text_and_duration=True,native_result_count=2,actual_query_completions=2)
            for invalid in (None,self.browser.get_property('ResultList')):self.entry.call_function('OnListItemObjectSet',invalid);require(self.entry.get_property('As Lyra Replay List Entry')==self.results[0] and str(button.get_property('ButtonText'))==expected,'invalid replay item changed row')
            self.report['native_invalid_items_preserve_current_row']=True;self.show_dialog('decline')
        elif self.phase in ('decline','confirm'):
            dialog=self.dialog()
            if dialog is None:return
            self.report['native_dialog_title_history']=self.history(dialog.get_property('Text_Title'),'Text','dialog-title');self.report['native_dialog_body_history']=self.history(dialog.get_property('RichText_Description'),'Text','dialog-body');self.report['native_confirmation_prompt_localization']=True;buttons=list(dialog.get_property('EntryBox_Buttons').call_function('GetAllEntries'));require(len(buttons)==2,'native replay Yes/No buttons missing')
            if self.phase=='decline':buttons[1].call_function('HandleButtonClicked');self.frames=0;self.enter('declined')
            else:
                self.entry.call_function('OnListItemObjectSet',self.results[1]);require(self.entry.get_property('As Lyra Replay List Entry')==self.results[1] and self.healths()==self.health_before,'current replay retarget or original gameplay health differs before playback');self.report['initial_gameplay_health_unchanged_before_playback']=True;self.settings.call_function('SetShouldAutoRecordReplays',False);buttons[0].call_function('HandleButtonClicked');self.enter('playback')
        elif self.phase=='declined':
            self.frames+=1
            if self.frames<5:return
            require(count(self.entry,'result',True)==1 and not self.engine.call_function('IsPlaying'),'decline unexpectedly played replay');self.dialog_results.append(1);self.report['native_decline_does_not_play']=True;self.show_dialog('confirm')
        elif self.phase=='playback':
            if not self.engine.call_function('IsPlaying'):return
            for world in ue.all_worlds():
                if world.get_world_type() not in (1,3) or world==self.original_world:continue
                controller=policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)
                if not valid(controller) or not controller.is_a(ue.find_class('LyraReplayPlayerController')):continue
                active=str(self.engine.call_function('GetActiveReplayName'));seconds=float(self.lyra.call_function('GetReplayCurrentTime'));huds=[w for w in ue.tobject_iterator(ue.load_class('/ShooterCore/UserInterface/Replays/W_ShooterReplayHUD.W_ShooterReplayHUD_C')) if w.call_function('IsInViewport') and w.call_function('IsActivated')]
                if seconds<=.25 or not huds:return
                require(active==self.names[0] and count(self.entry,'result',True)==2 and policy.lib('GameplayStatics').call_function('GetCurrentLevelName',world,True)==self.original_level,'native confirmed replay identity/destination differs');self.world=world;self.controller=controller;self.arrived=True;self.dialog_results.append(0);self.report.update(native_confirmed_play_uses_retargeted_current_item=True,native_replay_controller_hud_and_clock_observed=True,played_replay_name=active,native_playback_seconds=seconds,native_dialog_results=self.dialog_results,native_world_controller_replacement_expected=True);self.engine.set_property('bLoadDefaultMapOnStop',False);self.console('demostop');self.enter('stopped');return
        elif self.phase=='stopped':
            if self.engine.call_function('IsPlaying') or self.engine.call_function('IsRecording'):return
            self.report['native_playback_stopped']=True;self.finish()
    def cleanup(self):
        if hasattr(self,'engine') and (self.engine.call_function('IsPlaying') or self.engine.call_function('IsRecording')):self.engine.set_property('bLoadDefaultMapOnStop',False);self.console('demostop')
        for dialog in self.dialogs:
            if valid(dialog) and dialog.call_function('IsActivated'):dialog.call_function('DeactivateWidget')
        for w in self.widgets:
            if not valid(w):continue
            ue.clear_mixin_profile(w);w.call_function('StopAllAnimations')
            if w.is_a(ue.find_class('CommonActivatableWidget')) and w.call_function('IsActivated'):w.call_function('DeactivateWidget')
            w.call_function('RemoveFromParent')
        for w in self.roots:
            if valid(w) and w.is_rooted():w.remove_from_root()
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        for cls in self.class_roots:cls.remove_from_root()
        if self.settings_before is not None:self.settings.call_function('SetShouldAutoRecordReplays',self.settings_before)
        if self.stop_flag_before is not None:self.engine.set_property('bLoadDefaultMapOnStop',self.stop_flag_before)
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before)
        self.report['owned_roots_profiles_settings_and_input_restored']=all(not valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.roots) and all(cls.get_cdo().get_property('PythonMixinProfile')==p for cls,p in self.cdos.items()) and (self.settings_before is None or bool(self.settings.call_function('ShouldAutoRecordReplays'))==self.settings_before) and (self.stop_flag_before is None or bool(self.engine.get_property('bLoadDefaultMapOnStop'))==self.stop_flag_before)
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<280.,'replay browser timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_REPLAY_BROWSER_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_REPLAY_BROWSER_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPReplayBrowserResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
