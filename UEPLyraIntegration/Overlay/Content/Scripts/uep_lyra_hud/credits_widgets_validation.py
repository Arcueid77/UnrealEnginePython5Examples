"""Actual activation delay, native looping timer and original removed-widget behavior."""
import atexit
import hashlib
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import credits_widgets_mixin as policy
from .credits_widgets_contract import FALSE_FIELDS,require,validate

PROFILES=('BlueprintFallback','Python')
CLICK='BndEvt__W_TapToggleActionBar_Button_33_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature'
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def count(w,k,m):return sum(policy.evidence(w)[p+'_'+k+'_'+m] for p in ('python','fallback'))
def digest(v):return hashlib.sha256(v.encode('utf-8')).hexdigest()

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,visibility_cases=0,manual_scroll_edge_cases=0,owned_fixture_scroll_speed_overridden=True,owned_fixture_endpoint_overridden_after_capture=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.widgets=[];self.pairs={}
    def now(self):return float(policy.lib('KismetSystemLibrary').call_function('GetGameTimeInSeconds',self.world))
    def active(self,w):return bool(policy.lib('KismetSystemLibrary').call_function('K2_IsTimerActiveHandle',w,w.get_property('ScrollTimerHandle')))
    def exists(self,w):return bool(policy.lib('KismetSystemLibrary').call_function('K2_TimerExistsHandle',w,w.get_property('ScrollTimerHandle')))
    def create(self,k,p):
        self.classes[k].get_cdo().set_property('PythonMixinProfile',p);self.classes['bar'].get_cdo().set_property('PythonMixinProfile',p);w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[k],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,p);w.call_function('AddToPlayerScreen',0);return w
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.pairs={k:{p:self.create(k,p) for p in PROFILES} for k in policy.CLASSES};self.credits=[self.pairs['credits'][p] for p in PROFILES];self.frames=0;self.enter('construct')
    def strings(self):return [w.get_property('StudioPeopleString') for w in self.credits]
    def offsets(self):return [float(w.get_property('CreditsScroller').call_function('GetScrollOffset')) for w in self.credits]
    def visibility_cases(self):
        states=[]
        for value in range(5):
            row=[]
            for w in self.pairs['bar'].values():
                bar=w.get_property('BottomActionBar');bar.call_function('SetVisibility',value);visible=bool(one(w.call_function('GetCurrentVisibility')));require(visible==(value!=1),'source only Collapsed counts invisible');w.call_function(CLICK);after=int(bar.call_function('GetVisibility'));require(after==(0 if value==1 else 1),'tap toggle visibility differs');w.call_function('ResetVisibility');require(int(bar.call_function('GetVisibility'))==1,'bar reset must collapse');row.append([visible,after])
            require(row[0]==row[1],'bar profile state differs');states.append(row[0]);self.report['visibility_cases']+=2
        self.report['visibility_matrix']=states
    def edge_cases(self):
        rows=[]
        for offset,speed,end in ((4.,2.,20.),(19.,1.,20.),(20.,1.,20.)):
            states=[]
            for w in self.credits:
                w.call_function('ToggleScrollTimer',False);scroller=w.get_property('CreditsScroller');scroller.call_function('SetScrollOffset',offset);w.set_property('ScrollSpeed',speed);w.set_property('EndPointOffset',end);w.call_function('ScrollCredits');states.append(dict(current=float(w.get_property('CurrentPosition')),offset=float(scroller.call_function('GetScrollOffset')),bar=int(w.get_property('TapToggleActionBar').get_property('BottomActionBar').call_function('GetVisibility'))))
            require(states[0]==states[1],'source/Python scroll edge state differs');rows.append(states[0]);self.report['manual_scroll_edge_cases']+=1
        self.report['scroll_edge_matrix']=rows
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'credits phase timeout: '+self.phase)
        if self.phase=='construct':
            self.frames+=1
            if self.frames<4:return
            strings=self.strings();expected=''.join(policy.PREFIX+str(i)+policy.SUFFIX for i in range(1,101));require(strings==[expected,expected],'actual Construct rich-text100-loop differs');self.report['original_hundred_line_construct_rich_text_matches']=True;self.report['rich_text_sha256']=digest(expected);require(all(one(w.call_function('BP_GetDesiredFocusTarget')) is None for w in self.credits),'credits const focus must remain null');self.report['native_const_focus_remains_null']=True;self.visibility_cases();self.edge_cases();self.capture_before={w:count(w,'credits','capture') for w in self.credits};self.scroll_before={w:count(w,'credits','scroll') for w in self.credits}
            for w in self.credits:w.set_property('ScrollSpeed',0.);w.call_function('ActivateWidget')
            self.activation_time=self.now();self.enter('delay')
        elif self.phase=='delay':
            elapsed=self.now()-self.activation_time
            if elapsed<.9:require(all(count(w,'credits','capture')==self.capture_before[w] and not self.active(w) for w in self.credits),'native one-second Delay was skipped');return
            if not all(count(w,'credits','capture')>self.capture_before[w] for w in self.credits):return
            require(.99<=elapsed<=1.35,'native Delay completion outside original one-second frame bound');values=[]
            for w in self.credits:
                actual=float(w.get_property('EndPointOffset'));expected=float(w.get_property('CreditsScroller').call_function('GetDesiredSize').y);require(actual==expected and actual>0. and self.active(w),'native desired-size capture/timer start differs');values.append(actual)
            self.report.update(native_one_second_delay_then_desired_size_capture_and_timer=True,native_delay_observed_seconds=elapsed,native_captured_desired_heights=values)
            for w in self.credits:w.set_property('ScrollSpeed',2.)
            self.scroll_before={w:count(w,'credits','scroll') for w in self.credits};self.enter('loop')
        elif self.phase=='loop':
            callbacks=[count(w,'credits','scroll')-self.scroll_before[w] for w in self.credits]
            if min(callbacks)<3:return
            require(all(v>0. for v in self.offsets()),'actual native looping callbacks did not advance scroll')
            self.report.update(native_timer_callbacks_per_profile_min=min(callbacks),native_looping_timer_callbacks_advance_scroll=True)
            for w in self.credits:w.set_property('EndPointOffset',0.);w.get_property('TapToggleActionBar').get_property('BottomActionBar').call_function('SetVisibility',0)
            self.enter('end')
        elif self.phase=='end':
            if any(self.active(w) for w in self.credits):return
            require(not any(self.exists(w) for w in self.credits) and self.offsets()==[0.,0.] and all(int(w.get_property('TapToggleActionBar').get_property('BottomActionBar').call_function('GetVisibility'))==1 for w in self.credits),'native timer handle/scroll/bar end reset differs');self.report['native_endpoint_clears_handle_resets_scroll_and_collapses_bar']=True;self.end_counts=[count(w,'credits','scroll') for w in self.credits];self.end_time=self.now();self.enter('quiet')
        elif self.phase=='quiet':
            if self.now()-self.end_time<.12:return
            require([count(w,'credits','scroll') for w in self.credits]==self.end_counts and not any(self.exists(w) for w in self.credits),'end unexpectedly rearms timer');self.report['native_end_does_not_rearm_timer']=True
            for w in self.credits:w.set_property('EndPointOffset',100000.);w.set_property('ScrollSpeed',0.);w.call_function('ToggleScrollTimer',True);w.call_function('DeactivateWidget');w.call_function('RemoveFromParent')
            self.removed_counts=[count(w,'credits','scroll') for w in self.credits];self.enter('removed')
        elif self.phase=='removed':
            if min(count(w,'credits','scroll')-before for w,before in zip(self.credits,self.removed_counts))<3:return
            require(all(self.active(w) for w in self.credits),'source rooted removed timer was newly canceled');self.report['rooted_deactivated_removed_widget_keeps_original_timer']=True
            for w in self.credits:w.call_function('ToggleScrollTimer',False);w.call_function('AddToPlayerScreen',0)
            self.frames=0;self.enter('remount')
        elif self.phase=='remount':
            self.frames+=1
            if self.frames<4:return
            strings=self.strings();expected=''.join(policy.PREFIX+str(i)+policy.SUFFIX for i in range(1,101))*2;require(strings==[expected,expected],'actual native Construct remount must append100more');self.report.update(actual_native_remount_appends_another_hundred_lines=True,source_python_state_pairs_match=True);self.finish()
    def cleanup(self):
        for w in getattr(self,'credits',[]):
            w.call_function('ToggleScrollTimer',False)
            if w.call_function('IsActivated'):w.call_function('DeactivateWidget')
        self.report['only_owned_timers_explicitly_stopped_by_fixture']=all(not self.exists(w) for w in getattr(self,'credits',[]))
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for c in getattr(self,'class_roots',[]):c.remove_from_root()
        self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native credits timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_CREDITS_WIDGETS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_CREDITS_WIDGETS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPCreditsWidgetsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
