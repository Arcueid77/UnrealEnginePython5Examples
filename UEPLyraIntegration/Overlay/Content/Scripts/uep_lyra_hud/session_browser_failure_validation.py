"""Native search rejection, hidden completion and GC of a pending UI receiver."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from .experience_screen_validation import Validation as Shared,path
from . import session_browser_mixin as policy
from .session_browser_failure_contract import require,validate
from uep_lyra_world.effect_pad_mixin import valid


def count(widget,key):
    values=policy.evidence(widget)
    return sum(values[p+'_'+key] for p in ('python','fallback'))


class Validation(Shared):
    def __init__(self,result):
        super().__init__(result);self.mode='life';self.dialogs=[];self.notifications=[];self.states=[]
        self.report=dict(status='running',error=None,profiles=[])
        for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested',
                    'online_provider_failure_tested','backend_search_cancelled','callbacks_replayed','health_properties_written'):
            self.report[key]=False

    def begin(self):
        require('oss: tryloadsubsystemandsetdefault: loaded subsystem for type [null]' in self.log().casefold(),'Actual NULL backend required')
        self.health_before=self.healths();self.original_world=path(self.world)
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode)
        self.cls=ue.load_class(policy.CLASS);self.classes={'browser':self.cls}
        if not self.cls.is_rooted():self.cls.add_to_root();self.class_roots.append(self.cls)
        self.cdos[self.cls]=self.cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(self.cls)
        self.sub=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('CommonSessionSubsystem'))
        self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'))
        self.start_profile()

    def watch(self,request):
        def complete(success,error):self.notifications.append(dict(success=bool(success),error=str(error)))
        self.bind(request,'K2_OnSearchFinished',complete,True)
        return request

    def start_profile(self):
        self.profile=('BlueprintFallback','Python')[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.browser=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller)
        self.browser.add_to_root();self.roots.append(self.browser);self.widgets.append(self.browser);ue.set_mixin_profile(self.browser,self.profile)
        self.notification_before=len(self.notifications);self.row=dict(profile=self.profile)
        self.browser.call_function('AddToPlayerScreen',0);self.browser.call_function('ActivateWidget')
        self.request=self.watch(self.browser.get_property('SearchRequest'));require(count(self.browser,'search')==1 and count(self.browser,'results')==0,'Initial search must be genuinely pending')
        self.enter('initial')

    def dialogs_active(self):
        return [w for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen')) if w.call_function('IsActivated') and w.call_function('GetOwningPlayer')==self.controller]

    def history(self,widget,label):
        file=self.path.parent/(self.profile+'-'+label+'.t3d')
        require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(widget,str(file)),'Native browser error history export failed')
        raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        return [s.strip() for s in text.splitlines() if s.strip().startswith('Text=')]

    def observe(self):
        require(time.monotonic()-self.phase_started<40.,'Browser failure phase timeout: '+self.phase)
        if self.phase=='initial':
            if len(self.notifications)<self.notification_before+1:return
            require(self.notifications[-1]['success'] and count(self.browser,'results')==count(self.browser,'unlock')==1,'Native initial search differs')
            self.row['native_initial_search_completed']=True;self.item_counts=[int(self.browser.get_property('LyraListView').call_function('GetNumItems'))]
            # Reuse the actual completed native request and its original UI
            # delegate. The public API produces the failure;no delegate replay.
            self.sub.call_function('FindSessions',None,self.request);self.enter('failure')
        elif self.phase=='failure':
            if not self.dialogs_active():return
            require(len(self.dialogs_active())==1,'Native search error dialog duplicated');self.dialog=self.dialogs_active()[0];self.dialogs.append(self.dialog)
            title=self.history(self.dialog.get_property('Text_Title'),'search-error-title');body=self.history(self.dialog.get_property('RichText_Description'),'search-error-body')
            require(any('CommonUser' in line and 'Error_FindSessionBadPlayer' in line for line in body),'Original native search error FText history differs')
            require(len(self.notifications)==self.notification_before+2 and not self.notifications[-1]['success'] and self.notifications[-1]['error']=='Session search was not provided a local player','Native bad-player completion missing')
            self.row.update(native_bad_player_failure_dialog=True,native_error_ftext_history_preserved=True)
            self.state=dict(title=title,body=body,error=copy.deepcopy(self.notifications[-1]));self.item_counts.append(int(self.browser.get_property('LyraListView').call_function('GetNumItems')))
            require(count(self.browser,'results')==count(self.browser,'unlock')==2,'Native failure must update results/unlock exactly once')
            buttons=list(self.dialog.get_property('EntryBox_Buttons').call_function('GetAllEntries'));require(len(buttons)==1,'Expected native error acknowledgement button')
            buttons[0].call_function('HandleButtonClicked');self.frames=0;self.enter('acknowledged')
        elif self.phase=='acknowledged':
            self.frames+=1
            if self.frames<4:return
            require(not self.dialog.call_function('IsActivated') and not self.dialogs_active(),'Native error acknowledgement failed')
            old=self.request;self.browser.get_property('RefreshButton').call_function('HandleButtonClicked');self.request=self.watch(self.browser.get_property('SearchRequest'))
            require(self.request!=old and count(self.browser,'search')==2 and len(self.notifications)==self.notification_before+2,'Native retry did not start a distinct pending request')
            self.row['native_acknowledgement_and_refresh_recovery']=True;self.close(self.browser);self.enter('closed-pending')
        elif self.phase=='closed-pending':
            if len(self.notifications)<self.notification_before+3:return
            require(self.notifications[-1]['success'] and count(self.browser,'results')==count(self.browser,'unlock')==3 and not self.browser.call_function('IsInViewport') and not self.browser.call_function('IsActivated'),'Original retained hidden-widget completion differs')
            self.row['native_pending_screen_close_matches_original']=True;self.item_counts.append(int(self.browser.get_property('LyraListView').call_function('GetNumItems')))
            old=self.request;self.browser.call_function('AddToPlayerScreen',0);self.browser.call_function('ActivateWidget');self.request=self.watch(self.browser.get_property('SearchRequest'))
            require(self.request!=old and count(self.browser,'search')==3 and len(self.notifications)==self.notification_before+3,'Native reactivation must start a new pending request')
            self.row['native_reactivation_started_distinct_request']=True
            self.counters=policy.evidence(self.browser);self.counters_before=copy.deepcopy(self.counters)
            self.close(self.browser);self.browser.call_function('StopAllAnimations');self.browser.remove_from_root()
            policy.lib('KismetSystemLibrary').call_function('CollectGarbage');self.gc_frames=0;self.enter('gc-pending')
        elif self.phase=='gc-pending':
            self.gc_frames+=1
            if self.gc_frames<3:return
            require(not valid(self.browser),'Retired browser must be collected while request is still pending')
            if len(self.notifications)<self.notification_before+4:
                self.row['native_pending_widget_collected_before_completion']=True;return
            require(self.row.get('native_pending_widget_collected_before_completion') is True and self.notifications[-1]['success'] and self.counters==self.counters_before,'Destroyed browser received a late native completion')
            self.row['native_request_completed_without_destroyed_widget_callback']=True;self.enter('quiet')
        elif self.phase=='quiet':
            if time.monotonic()-self.phase_started<.3:return
            require(self.counters==self.counters_before and not self.dialogs_active() and path(self.world)==self.original_world,'Late callback/dialog/travel after retired receiver')
            prefix='fallback' if self.profile=='BlueprintFallback' else 'python';foreign='python' if prefix=='fallback' else 'fallback'
            self.row.update(native_notification_sequence=[n['success'] for n in self.notifications[self.notification_before:]],
                search_calls=sum(self.counters[p+'_search'] for p in ('python','fallback')),results_calls=sum(self.counters[p+'_results'] for p in ('python','fallback')),
                unlock_calls=sum(self.counters[p+'_unlock'] for p in ('python','fallback')),
                exclusive_selected_profile_calls=all(self.counters[prefix+'_'+key]==3 and self.counters[foreign+'_'+key]==0 for key in ('search','results','unlock')))
            self.state.update(native_notification_sequence=self.row['native_notification_sequence'],item_counts=self.item_counts,retired_receiver_collected=True)
            self.report['profiles'].append(self.row);self.states.append(self.state);self.index+=1
            if self.index<2:self.start_profile()
            else:self.report.update(source_python_states_match=self.states[0]==self.states[1],matrices=self.states);self.finish()

    def cleanup(self):
        for dialog in self.dialogs:
            if valid(dialog):self.close(dialog)
        super().cleanup()

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_BROWSER_FAILURE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_BROWSER_FAILURE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSessionBrowserFailureResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
