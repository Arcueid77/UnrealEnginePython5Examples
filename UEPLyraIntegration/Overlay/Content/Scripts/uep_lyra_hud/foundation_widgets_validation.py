"""Real activation/ticks/layout plus source loading delegate lifetime comparison."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import foundation_widgets_mixin as policy
from .foundation_widgets_contract import PROFILES,FALSE_FIELDS,require,validate

def count(w,k):return sum(policy.evidence(w)[p+'_'+k] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None
def xy(v):return [float(v.x),float(v.y)]
def margin(v):return [float(getattr(v,n)) for n in ('Left','Top','Right','Bottom')]

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.classes={};self.cdos={};self.index=0;self.states=[]
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.backend=policy.subsystem(self.world,'LyraLoadingScreenSubsystem');self.original_content=self.backend.call_function('GetLoadingScreenContentWidget');self.manager=policy.subsystem(self.world,'LoadingScreenManager');self.texture=ue.load_object(ue.find_class('Texture2D'),'/Game/UI/Menu/Art/T_UI_TileArt_Quickplay.T_UI_TileArt_Quickplay');self.start_profile()
    def create(self,k):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[k],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile);w.call_function('AddToPlayerScreen',0);return w
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.backend.call_function('SetLoadingScreenContentWidget',None);self.current={k:self.create(k) for k in policy.CLASSES};self.row=dict(profile=self.profile,aspect_brush_cases=0,spinner_size_cases=0,native_loading_changes=0);self.state={};self.reason_at_start=count(self.current['reason'],'reason');self.current['dialog'].call_function('ActivateWidget');self.frames=0;self.enter('settle')
    def history(self):
        label=self.current['reason'].get_property('ReasonTextWidget');file=self.path.parent/(self.profile+'-reason.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(label,str(file)),'native reason export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [s.strip() for s in text.splitlines() if s.strip().startswith('Text=')]
    def brush(self,v):return dict(draw=int(v.DrawAs),image_type=int(v.ImageType),tiling=int(v.Tiling),mirroring=int(v.Mirroring),margin=margin(v.Margin),resource=path(v.ResourceObject))
    def aspect_cases(self):
        w=self.current['aspect'];rows=[]
        for i,resource in enumerate((self.texture,None,self.texture)):
            brush=ue.find_struct('SlateBrush')(ResourceObject=resource,DrawAs=i,ImageType=i,Tiling=i,Mirroring=i,Margin=ue.find_struct('Margin')(Left=i,Top=i+1,Right=i+2,Bottom=i+3));w.set_property('DisplayBrush',brush);w.call_function('PreConstruct',bool(i%2));expected=self.brush(brush);values=[self.brush(w.get_property(n).get_property('Brush')) for n in ('Background','BlurredBackground')];require(values==[expected,expected],'aspect must copy the whole brush to both images');rows.append(values)
        self.row.update(aspect_brush_cases=3,actual_native_aspect_construct_and_brush_copy=count(w,'aspect')>=4);return rows
    def spinner_cases(self):
        w=self.current['spinner'];rows=[]
        for i,value in enumerate(((16.,32.),(0.,0.),(99.5,41.25))):
            w.set_property('Size',ue.FVector2D(*value));w.call_function('PreConstruct',bool(i%2));w.call_function('ForceLayoutPrepass');actual=xy(w.get_property('Spinner').call_function('GetDesiredSize'));require(actual==list(value),'actual native Image desired-size override differs');rows.append(actual)
        self.row.update(spinner_size_cases=3,actual_native_spinner_preconstruct_and_desired_size=count(w,'spinner')>=4);return rows
    def child(self):return self.current['loading'].get_property('ExperienceSpecificWidgetSlot').call_function('GetContent')
    def load_cases(self):
        w=self.current['loading'];default=ue.load_class(policy.DEFAULT_CONTENT);require(count(w,'loading')>0 and w.get_property('ContentWidgetClass')==default and self.child().get_class()==default,'actual loading Construct fallback differs');self.row['loading_host_actual_construct_and_fallback']=True;w.call_function('OnLoadingScreenWidgetChanged',self.classes['spinner']);first=self.child();w.call_function('OnLoadingScreenWidgetChanged',self.classes['spinner']);second=self.child();require(first!=second and first.get_class()==second.get_class()==self.classes['spinner'],'same-class callback must still create a new child');self.row['same_class_direct_callback_creates_new_child']=True;before=count(w,'loading');self.backend.call_function('SetLoadingScreenContentWidget',self.classes['aspect']);require(count(w,'loading')==before+1 and self.child().get_class()==self.classes['aspect'],'actual subsystem delegate must deliver exactly once');self.row.update(native_loading_class_change_delegate_once=True,native_loading_changes=1);return dict(fallback=path(default),same_class_new_child=True,native_child=path(self.child().get_class()))
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'foundation widgets phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<5:return
            dialog=self.current['dialog'];animation=dialog.get_property('OnActivated')
            if float(dialog.call_function('GetAnimationCurrentTime',animation))<.01:return
            require(count(dialog,'dialog')>0 and dialog.call_function('IsAnimationPlayingForward',animation),'actual native dialog activation animation missing');self.row['actual_native_dialog_activation_animation']=True;reason=self.current['reason'];ticks=count(reason,'reason')-self.reason_at_start;require(ticks>=3,'actual native reason Tick did not poll');self.row.update(actual_native_reason_construct_and_ticks=True,native_reason_ticks=ticks);history=self.history();require(any('NSLOCTEXT' in s and 'D1EF437A4F9FF5DE58443886BD514521' in s for s in history),'localized reason format identity lost');label=reason.get_property('ReasonTextWidget');display=policy.lib('KismetTextLibrary').call_function('Conv_TextToString',label.call_function('GetText'));current=self.manager.call_function('GetDebugReasonForShowingOrHidingLoadingScreen');require(display==current+'...','reason format display differs');self.row['localized_reason_format_history_preserved']=True;self.state.update(aspect=self.aspect_cases(),spinner=self.spinner_cases(),loading=self.load_cases());self.current['loading'].call_function('RemoveFromParent');self.frames=0;self.enter('removed')
        elif self.phase=='removed':
            self.frames+=1
            if self.frames<4:return
            w=self.current['loading'];before=count(w,'loading');self.backend.call_function('SetLoadingScreenContentWidget',None);require(count(w,'loading')==before+1 and self.child().get_class()==ue.load_class(policy.DEFAULT_CONTENT),'original rooted removed host must retain its delegate');self.row.update(rooted_removed_loading_host_keeps_original_delegate=True,native_loading_changes=2);self.current['dialog'].call_function('DeactivateWidget')
            for widget in self.current.values():widget.call_function('RemoveFromParent')
            self.report['profiles'].append(self.row);self.states.append(self.state);self.report['matrices']=self.states;self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report['source_python_state_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        if hasattr(self,'backend'):self.backend.call_function('SetLoadingScreenContentWidget',self.original_content);self.report['original_loading_content_class_restored']=self.backend.call_function('GetLoadingScreenContentWidget')==self.original_content
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('StopAllAnimations');w.call_function('RemoveFromParent');w.remove_from_root()
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for c in getattr(self,'class_roots',[]):c.remove_from_root()
        self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native foundation widgets timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_FOUNDATION_WIDGETS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_FOUNDATION_WIDGETS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPFoundationWidgetsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
