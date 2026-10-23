"""Owned LAN success -> actual duplicate provider rejection -> native UI retry."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from .session_entry_validation import Host as OriginalHost,Client as OriginalClient,fresh_world,count,arg,path,policy
from .session_join_failure_contract import require,validate_peer
from uep_lyra_world.effect_pad_mixin import valid


class Finish:
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_SESSION_JOIN_FAILURE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate_peer(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SESSION_JOIN_FAILURE_SHUTDOWN_'+self.report['status'].upper())


class Host(Finish,OriginalHost):
    pass


class Client(Finish,OriginalClient):
    def __init__(self,result):
        super().__init__(result);self.join_notifications=[];self.dialogs=[];self.duplicate_started=False

    def begin(self):
        super().begin()
        def joined(result):self.join_notifications.append(dict(success=bool(result.bWasSuccessful),error_id=str(result.ErrorId),error=str(result.ErrorText)))
        self.bind(self.sub,'K2_OnJoinSessionCompleteEvent',joined)

    def check_row(self):
        self.saved_result=self.entry.get_property('SessionEntry')
        if not self.saved_result.is_rooted():self.saved_result.add_to_root();self.proxy_roots.append(self.saved_result)
        super().check_row()

    def destroy_session(self,phase):
        if self.phase=='arrival' and not self.duplicate_started:
            self.duplicate_started=True;self.initial_entry=self.entry;self.initial_counters=copy.deepcopy(policy.evidence(self.initial_entry))
            require([r['success'] for r in self.join_notifications]==[True],'Initial join must come from actual native completion')
            self.before_duplicate_health=self.healths();self.duplicate_world=path(self.world);self.duplicate_controller=path(self.controller)
            self.destroy_log_before=self.log().count('OnDestroySessionComplete(SessionName: GameSession, bWasSuccessful: true)')
            cls=ue.load_class(policy.CLASS);self.duplicate=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,cls,self.controller)
            self.duplicate.add_to_root();self.roots.append(self.duplicate);self.widgets.append(self.duplicate);ue.set_mixin_profile(self.duplicate,self.only_profile)
            self.duplicate.call_function('AddToPlayerScreen',0);self.duplicate.call_function('OnListItemObjectSet',self.saved_result)
            self.report['duplicate_row_uses_actual_advertised_result']=True;self.enter('duplicate-row')
        else:super().destroy_session(phase)

    def active_dialogs(self):
        return [w for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen')) if w.call_function('IsActivated') and w.call_function('GetOwningPlayer')==self.controller]

    def observe(self):
        if self.phase not in ('duplicate-row','duplicate-error','acknowledged','retry-arrival','destroy'):
            return super().observe()
        require(time.monotonic()-self.phase_started<110.,'Duplicate join phase timeout: '+self.phase)
        if self.phase=='duplicate-row':
            if count(self.duplicate,'image')<1:return
            require(self.duplicate.get_property('SessionEntry')==self.saved_result,'Duplicate row lost actual search result')
            self.duplicate.get_property('SessionButton').call_function('HandleButtonClicked');self.enter('duplicate-error')
        elif self.phase=='duplicate-error':
            if len(self.join_notifications)<2 or not self.active_dialogs():return
            require([r['success'] for r in self.join_notifications]==[True,False] and self.join_notifications[-1]['error_id']=='UnknownError' and self.join_notifications[-1]['error']=='Join failed.','Expected actual NULL-provider duplicate join result')
            require(len(self.active_dialogs())==1,'Duplicate join error dialog duplicated');self.dialog=self.active_dialogs()[0];self.dialogs.append(self.dialog)
            title=self.history(self.dialog.get_property('Text_Title'),'duplicate-title');body=self.history(self.dialog.get_property('RichText_Description'),'duplicate-body')
            require('NSLOCTEXT("NetworkErrors", "JoinSessionFailed", "Join failed.")' in body,'Native duplicate join error history lost')
            require(count(self.duplicate,'prepared')==count(self.duplicate,'completed')==1 and not self.duplicate.get_property('JoiningProgressWidget').call_function('IsActivated'),'Native join failure spinner/unbind continuation differs')
            require(path(self.world)==self.duplicate_world and path(self.controller)==self.duplicate_controller and self.healths()==self.before_duplicate_health,'Failed duplicate join travelled or changed gameplay health')
            self.report.update(failed_join_error_ui_natively_tested=True,native_duplicate_join_rejected=True,native_failure_ftext_history_preserved=True,native_spinner_popped_after_failure=True,
                native_failure_error_id=self.join_notifications[-1]['error_id'],failure_state=dict(title=title,body=body,native_result=copy.deepcopy(self.join_notifications[-1])))
            buttons=list(self.dialog.get_property('EntryBox_Buttons').call_function('GetAllEntries'));require(len(buttons)==1,'Expected actual native error acknowledgement')
            buttons[0].call_function('HandleButtonClicked');self.frames=0;self.enter('acknowledged')
        elif self.phase=='acknowledged':
            self.frames+=1
            if self.frames<4 or self.log().count('OnDestroySessionComplete(SessionName: GameSession, bWasSuccessful: true)')<=self.destroy_log_before:return
            require(not self.dialog.call_function('IsActivated') and not self.active_dialogs(),'Native duplicate join acknowledgement failed')
            require(policy.evidence(self.initial_entry)==self.initial_counters,'Initial completed row remained bound to unrelated joins')
            self.report.update(native_acknowledgement_closed_error_dialog=True,failure_cleanup_destroyed_owned_named_session=True)
            self.retry_world=self.world;self.duplicate.get_property('SessionButton').call_function('HandleButtonClicked');self.enter('retry-arrival')
        elif self.phase=='retry-arrival':
            arrival=fresh_world(self.retry_world)
            if not arrival:return
            world,controller,snap=arrival
            require([r['success'] for r in self.join_notifications]==[True,False,True] and count(self.duplicate,'prepared')==count(self.duplicate,'completed')==2,'Native retry continuation duplicated or missing')
            level=policy.lib('GameplayStatics').call_function('GetCurrentLevelName',world,True)
            require(str(snap.NetMode)=='Client' and level==self.host['level'] and self.host['experience'] in path(snap.CurrentExperience),'Native retry joined wrong host/Experience')
            require(policy.evidence(self.initial_entry)==self.initial_counters,'Initial completed row reentered during retry')
            values=policy.evidence(self.duplicate);selected='fallback' if self.only_profile=='BlueprintFallback' else 'python';foreign='python' if selected=='fallback' else 'fallback'
            self.report.update(native_retry_rejoined_same_host=True,initial_row_not_reentered_by_other_join_notifications=True,
                native_join_notification_sequence=[r['success'] for r in self.join_notifications],duplicate_prepared_calls=count(self.duplicate,'prepared'),duplicate_completion_calls=count(self.duplicate,'completed'),
                exclusive_selected_profile_calls=all(values[selected+'_'+key]==2 and values[foreign+'_'+key]==0 for key in ('prepared','completed')))
            self.world=world;self.controller=controller;self.destroy_session('destroy')
        elif self.phase=='destroy':
            if not self.destroyed:return
            require(self.destroyed==[True],'Native retried client session cleanup failed');self.report['owned_native_client_session_destroyed']=True;self.finish()

    def cleanup(self):
        for dialog in self.dialogs:
            if valid(dialog):self.close(dialog)
        super().cleanup()


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSessionJoinFailureResult=')),None)
if result:
    validation=(Host if arg('UEPSessionEntryRole','client')=='host' else Client)(result)
    atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
