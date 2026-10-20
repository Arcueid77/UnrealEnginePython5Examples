"""Native original macro completion and real loading-class setter observations."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import experience_preparation_policy as policy
from .ui_preparation_probe_contract import CASES,FALSE_FIELDS,require,validate
def path(value):return value.get_path_name() if value is not None else None
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_local_playing_phase=False;self.report=dict(status='running',error=None,cases=[],direct_python_helper_inputs=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widget=None;self.definition=None;self.cls=None;self.class_root=False;self.bound=False;self.index=0
    def begin(self):
        self.health_before=self.healths();self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.sub=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('LyraLoadingScreenSubsystem'));self.before=self.sub.call_function('GetLoadingScreenContentWidget');self.cls=ue.load_class('/Game/UEPValidation/W_UIExperiencePreparationProbe.W_UIExperiencePreparationProbe_C');self.class_root=not self.cls.is_rooted()
        if self.class_root:self.cls.add_to_root()
        self.widget=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);self.widget.add_to_root();self.definition=ue.new_object(ue.find_class('LyraUserFacingExperienceDefinition'));self.definition.add_to_root();self.spinner=ue.load_class('/Game/UI/Menu/Experiences/W_NonInteractiveSpinner.W_NonInteractiveSpinner_C');self.host=ue.load_class('/Game/UI/Foundation/LoadingScreen/W_LoadingScreen_Host.W_LoadingScreen_Host_C');self.inputs=(None,self.spinner,self.host,ue.find_class('Actor'));self.notifications=[];self.callback=lambda cls:self.notifications.append(path(cls));self.sub.bind_event('OnLoadingScreenWidgetChanged',self.callback);self.bound=True;self.start_case()
    def start_case(self):
        self.input=self.inputs[self.index];self.expected=self.input if self.input is not None and self.input.is_child_of(ue.find_class('UserWidget')) else None;self.sentinel=self.host if self.expected==self.spinner else self.spinner;self.sub.call_function('SetLoadingScreenContentWidget',self.sentinel);self.definition.set_property('LoadingScreenWidget',self.input);self.original_before=int(self.widget.get_property('OriginalCount'));self.notifications_before=len(self.notifications);self.widget.call_function('RunOriginal',self.definition);self.enter('original')
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'UI preparation probe phase timeout')
        if self.phase=='original':
            delta=int(self.widget.get_property('OriginalCount'))-self.original_before
            if delta<1:return
            actual=self.sub.call_function('GetLoadingScreenContentWidget');require(delta==1 and actual==self.expected and len(self.notifications)-self.notifications_before==1,'original native macro cast/setter/completion differs');self.row=dict(case=CASES[self.index],expected_class=path(self.expected),original_class=path(actual),actual_original_native_completions=delta,original_setter_notifications=1);self.sub.call_function('SetLoadingScreenContentWidget',self.sentinel);before=len(self.notifications);helper_before=int(self.widget.get_property('HelperCount'));policy.finish(self.widget,self.input,'HelperCompleted');actual=self.sub.call_function('GetLoadingScreenContentWidget');require(actual==self.expected and int(self.widget.get_property('HelperCount'))-helper_before==1 and len(self.notifications)-before==1,'Python/native setter/continuation differs');self.row.update(python_class=path(actual),actual_helper_native_continuations=1,python_setter_notifications=1);self.frames=0;self.enter('quiet')
        elif self.phase=='quiet':
            self.frames+=1
            if self.frames<6:return
            require(int(self.widget.get_property('OriginalCount'))-self.original_before==1,'original native completion repeated');self.report['cases'].append(self.row);self.index+=1
            if self.index<len(CASES):self.start_case()
            else:self.finish()
    def cleanup(self):
        if self.bound:self.sub.unbind_event('OnLoadingScreenWidgetChanged',self.callback)
        if hasattr(self,'before'):self.sub.call_function('SetLoadingScreenContentWidget',self.before)
        if self.widget is not None:self.widget.call_function('StopAllAnimations');self.widget.call_function('RemoveFromParent');self.widget.remove_from_root()
        if self.definition is not None:self.definition.remove_from_root()
        if self.class_root:self.cls.remove_from_root()
        self.report['owned_objects_roots_loading_class_and_health_restored']=(self.widget is None or not self.widget.is_rooted()) and (self.definition is None or not self.definition.is_rooted()) and (not hasattr(self,'before') or self.sub.call_function('GetLoadingScreenContentWidget')==self.before) and (not hasattr(self,'health_before') or self.healths()==self.health_before)
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<180.,'UI preparation probe timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_UI_PREPARATION_PROBE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_UI_PREPARATION_PROBE_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPUIPreparationProbeResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
