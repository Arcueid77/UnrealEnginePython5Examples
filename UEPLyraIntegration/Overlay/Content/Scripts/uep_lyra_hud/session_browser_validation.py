"""Real selection login/push, NULL searches and native shared DoOnce state."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .experience_screen_validation import Validation as Shared,path
from . import session_browser_mixin as policy
from .session_browser_contract import PROFILES,FALSE_FIELDS,require,validate
def count(w,key):
    before=getattr(w,'_uep_session_browser_fixture_before',{});values=policy.evidence(w);return sum(values[p+'_'+key]-before.get(p+'_'+key,0) for p in ('python','fallback'))
class Validation(Shared):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.browser_cls=None;self.browser_cdo=None
    def begin(self):
        self.browser_cls=ue.load_class(policy.CLASS);self.browser_cdo=self.browser_cls.get_cdo().get_property('PythonMixinProfile')
        if not self.browser_cls.is_rooted():self.browser_cls.add_to_root();self.class_roots.append(self.browser_cls)
        ue.register_declared_mixin(self.browser_cls);super().begin();self.classes['browser']=self.browser_cls;self.cdos[self.browser_cls]=self.browser_cdo
    def start_profile(self):
        profile=PROFILES[self.index];self.pooled_before={}
        for widget in self.widgets:
            if valid(widget) and widget.get_class()==self.browser_cls:
                widget._uep_session_browser_fixture_before=dict(policy.evidence(widget));self.pooled_before[path(widget)]=True;ue.set_mixin_profile(widget,profile)
        self.browser_cls.get_cdo().set_property('PythonMixinProfile',profile);super().start_profile()
    def search_logs(self):return self.log().count('LogCommonSession: OnFindSessionsComplete(bWasSuccessful: true)')
    def observe(self):
        require(time.monotonic()-self.phase_started<40.,'browser phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if not self.loaded or self.frames<4:return
            self.list.call_function('SelectFirstExperience');self.search_before=self.search_logs();self.push('BrowseButton','browse')
        elif self.phase=='browse':
            self.bind_push()
            if not self.afterpush:return
            require(len(self.afterpush)==1 and path(self.afterpush[0].get_class())==policy.CLASS,'actual native browser push missing');self.browser=self.afterpush[0]
            if self.browser not in self.widgets:self.widgets.append(self.browser)
            self.row['native_pooled_browser_reused']=path(self.browser) in self.pooled_before
            if not self.browser.is_rooted():self.browser.add_to_root();self.roots.append(self.browser)
            require(str(ue.get_mixin_profile(self.browser))==self.profile,'pushed browser Profile differs');self.row['native_selection_login_then_browser_afterpush']=True;require(count(self.browser,'activate')==1 and self.browser.call_function('BP_GetDesiredFocusTarget')==self.browser.get_property('LyraListView'),'native browser activation/const focus differs');self.row['native_activation_and_const_focus']=True;self.result_counts=[];self.enter('initial')
        elif self.phase in ('initial','refresh','third'):
            expected={'initial':1,'refresh':2,'third':3}[self.phase]
            self.report['native_callback_diagnostics']=dict(phase=self.phase,expected=expected,counters=dict(policy.evidence(self.browser)),native_log_count=self.search_logs(),native_log_baseline=self.search_before)
            if count(self.browser,'results')<expected:return
            # Native log output is flushed after this tick. Keep the callback
            # count strict and wait for its independent log observation.
            if self.search_logs()-self.search_before<expected:return
            require(count(self.browser,'results')==expected and count(self.browser,'unlock')==expected and self.search_logs()-self.search_before==expected,'actual native search callback/unlock count differs');request=self.browser.get_property('SearchRequest');items=list(request.get_property('Results'));require(not items and int(self.browser.get_property('NoGamesBorder').call_function('GetVisibility'))==3 and int(self.browser.get_property('LyraListView').call_function('GetNumItems'))==0,'native empty results/list visibility differs');self.result_counts.append(len(items));self.row['native_empty_results_visibility_list_and_unlock']=True
            if expected==1:
                self.previous=request;self.browser.get_property('RefreshButton').call_function('HandleButtonClicked');self.current=self.browser.get_property('SearchRequest');require(self.current!=self.previous and count(self.browser,'refresh')==1 and count(self.browser,'search')==2,'actual native RefreshButton did not start new request');self.row['native_refresh_button_starts_new_request']=True;self.browser.call_function('StartSearch');other='Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback';ue.set_mixin_profile(self.browser,other);self.browser.call_function('StartSearch');require(self.browser.get_property('SearchRequest')==self.current and count(self.browser,'search')==2,'native shared DoOnce failed to block duplicate across Profiles');self.row['native_do_once_blocks_duplicates_across_profiles']=True;self.switched=other;self.enter('refresh')
            elif expected==2:
                key=('python' if self.switched=='Python' else 'fallback')+'_results';before=getattr(self.browser,'_uep_session_browser_fixture_before',{});require(policy.evidence(self.browser)[key]-before.get(key,0)==1,'actual search completion did not use switched Profile');ue.set_mixin_profile(self.browser,self.profile);self.browser.get_property('RefreshButton').call_function('HandleButtonClicked');require(self.browser.get_property('SearchRequest')!=self.current and count(self.browser,'search')==3,'native completion did not reset shared DoOnce');self.row['native_completion_after_profile_switch_unlocks_next_search']=True;self.enter('third')
            else:self.frames=0;self.enter('quiet')
        elif self.phase=='quiet':
            self.frames+=1
            if self.frames<12 or self.browser.call_function('IsAnimationPlaying',self.browser.get_property('ProgressSpinnerOutro')):return
            require(count(self.browser,'results')==count(self.browser,'unlock')==count(self.browser,'search')==3 and self.search_logs()-self.search_before==3,'native browser repeated callback after completion');self.row.update(native_three_actual_search_completions_and_quiet=True,actual_native_search_completions=3,result_counts=self.result_counts);self.states.append(dict(result_counts=self.result_counts,empty_visibility=int(self.browser.get_property('NoGamesBorder').call_function('GetVisibility')),list_items=int(self.browser.get_property('LyraListView').call_function('GetNumItems'))));self.close(self.browser);self.close(self.w);self.report['profiles'].append(self.row);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report.update(source_python_state_pairs_match=self.states[0]==self.states[1],matrices=self.states);self.finish()
    def cleanup(self):
        super().cleanup()
        for widget in self.widgets:
            if valid(widget) and hasattr(widget,'_uep_session_browser_fixture_before'):delattr(widget,'_uep_session_browser_fixture_before')
        if self.browser_cls is not None:self.browser_cls.get_cdo().set_property('PythonMixinProfile',self.browser_cdo)
        self.report['owned_roots_profiles_input_and_loading_class_restored'] &= self.browser_cls is None or self.browser_cls.get_cdo().get_property('PythonMixinProfile')==self.browser_cdo
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SESSION_BROWSER_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SESSION_BROWSER_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSessionBrowserResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
