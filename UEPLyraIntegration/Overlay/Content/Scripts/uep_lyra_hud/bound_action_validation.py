"""Real CommonInput/UMG lifetime, brush reconstruction and latent-click parity."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import bound_action_mixin as policy
from .bound_action_contract import PROFILES,FALSE_FIELDS,require,validate

def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def count(w,k):return sum(policy.evidence(w)[p+'_'+k] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],owned_selection_fixture_enables_selectable_and_toggleable=True,completion_guard_fixture_sets_only_owned_widget_flag=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.index=0;self.states=[]
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);self.root_class=not self.cls.is_rooted()
        if self.root_class:self.cls.add_to_root()
        self.cdo_profile=self.cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(self.cls);self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));require(policy.valid(self.input),'actual CommonInput subsystem missing');self.input_before=int(self.input.call_function('GetCurrentInputType'));self.start_profile()
    def start_profile(self):
        self.profile=PROFILES[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);self.w.add_to_root();self.widgets.append(self.w);ue.set_mixin_profile(self.w,self.profile);self.w.call_function('AddToPlayerScreen',0);self.row=dict(profile=self.profile,typed_input_style_cases=0,actual_native_input_changes=0);self.frames=0;self.enter('settle')
    def animation(self,n):
        a=self.w.get_property(n);return dict(playing=bool(self.w.call_function('IsAnimationPlaying',a)),forward=bool(self.w.call_function('IsAnimationPlayingForward',a)),position=float(self.w.call_function('GetAnimationCurrentTime',a)))
    def scalars(self):return [[float(one(m.call_function('K2_GetScalarParameterValue',n))) for n in ('Hover_Animate','Pressed_Animate','bIsDisabled')] for m in policy.materials(self.w)]
    def draw(self):return int(self.w.get_property('ButtonBorder').get_property('Background').DrawAs)
    def switch_input(self,bound):
        target=1 if int(self.input.call_function('GetCurrentInputType'))!=1 else 0;before=count(self.w,'style');self.input.call_function('SetCurrentInputType',target);actual=int(self.input.call_function('GetCurrentInputType'));require(actual==target,'native input type switch blocked');delta=count(self.w,'style')-before;require(delta==(1 if bound else 0),'native input delegate count differs: '+str(delta))
        if bound:require(self.draw()==(0 if target==1 else 1),'actual native input brush differs')
        self.row['actual_native_input_changes']+=1;return dict(input=target,callbacks=delta,draw=self.draw() if bound else None)
    def baseline(self):
        w=self.w;w.call_function('PreConstruct',False);self.row['native_construct_preconstruct_and_reset']=count(w,'style')>0 and count(w,'reset')>0;w.call_function('SetIsSelectable',True);w.call_function('SetIsToggleable',True);border=w.get_property('ButtonBorder');rows=[]
        for inputtype in (0,1,2,3):
            old=border.get_property('Background');old.ImageType=1;old.Tiling=1;old.Mirroring=2;old.Margin=ue.find_struct('Margin')(Left=1.,Top=2.,Right=3.,Bottom=4.);border.call_function('SetBrush',old);resource=old.ResourceObject;before=count(w,'style');w.call_function('UpdateSyleOnInputMethod',inputtype);new=border.get_property('Background');row=dict(input=inputtype,draw=int(new.DrawAs),image_type=int(new.ImageType),tiling=int(new.Tiling),mirroring=int(new.Mirroring),margin=[float(getattr(new.Margin,n)) for n in ('Left','Top','Right','Bottom')],resource_identity=new.ResourceObject==resource)
            self.report['brush_observation']=dict(profile=self.profile,**row);require(count(w,'style')==before+1 and row['draw']==(0 if inputtype==1 else 1) and row['image_type']==0 and row['tiling']==1 and row['mirroring']==2 and row['margin']==[1.,2.,3.,4.] and row['resource_identity'],'original brush MakeStruct semantics differ');rows.append(row)
        self.row.update(typed_input_style_cases=len(rows),source_brush_copied_pins_and_omitted_defaults_match=True,only_gamepad_hides_border=True);self.state=dict(brushes=rows);self.state['mounted_input']=self.switch_input(True);self.row['native_input_method_callback_exactly_once']=True
        w.call_function('SetIsEnabled',False);disabled=self.scalars();require(w.get_property('IsDisabled') is True and disabled==[[0.,0.,1.],[0.,0.,1.]],'disable/reset both materials differs');snapshot=(self.animation('OnHovered'),self.animation('OnPressed'));sounds=count(w,'clicksound')
        for f in ('BP_OnHovered','BP_OnUnhovered','BP_OnSelected','BP_OnDeselected','BP_OnClicked'):w.call_function(f)
        require(snapshot==(self.animation('OnHovered'),self.animation('OnPressed')) and count(w,'clicksound')==sounds,'disabled callbacks changed animation/sound');self.row['disabled_callbacks_are_noops']=True;w.call_function('SetIsEnabled',True);enabled=self.scalars();require(w.get_property('IsDisabled') is False and enabled==[[0.,0.,0.],[0.,0.,0.]],'enable both material parameters differs');self.row['both_material_disable_enable_and_reset']=True;self.state.update(disabled=disabled,enabled=enabled)
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'bound-action phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<3:return
            self.baseline();self.w.call_function('BP_OnHovered');self.enter('hover')
        elif self.phase=='hover':
            if self.animation('OnHovered')['position']<.01:return
            require(self.animation('OnHovered')['forward'],'actual hover animation missing');self.w.call_function('SetIsSelected',True,False);require(self.w.call_function('GetSelected'),'owned selectable widget did not select');self.enter('selected')
        elif self.phase=='selected':
            if self.animation('OnPressed')['position']<.01:return
            require(self.animation('OnPressed')['forward'] and count(self.w,'select')>0,'actual selection callback missing');before=count(self.w,'deselect');self.w.call_function('SetIsSelected',False,False);require(count(self.w,'deselect')==before+1,'actual deselection callback missing');self.row['native_hover_selection_and_deselection_callbacks']=True;self.w.call_function('BP_OnUnhovered');self.w.call_function('ResetMaterials');self.click_before=count(self.w,'finished');before=count(self.w,'clicksound');self.w.call_function('BP_OnClicked');require(count(self.w,'clicksound')==before+1,'native immediate click continuation missing');self.enter('click')
        elif self.phase=='click':
            if count(self.w,'finished')<=self.click_before:return
            require(not self.animation('OnPressed')['forward'],'natural click completion did not reverse');self.row['native_click_immediate_and_natural_completion']=True;self.w.call_function('ResetMaterials');self.click_before=count(self.w,'finished');self.w.call_function('BP_OnClicked');self.w.set_property('IsDisabled',True);self.enter('disabled_click')
        elif self.phase=='disabled_click':
            if count(self.w,'finished')<=self.click_before:return
            require(not self.animation('OnPressed')['playing'] or self.animation('OnPressed')['forward'],'disabled natural completion reversed');self.row.update(disabled_flag_at_natural_completion_keeps_reverse_guard=True,native_finished_callbacks=count(self.w,'finished'));self.w.set_property('IsDisabled',False);self.w.call_function('RemoveFromParent');self.frames=0;self.enter('removed')
        elif self.phase=='removed':
            self.frames+=1
            if self.frames<4:return
            self.state['removed_input']=self.switch_input(False);self.row['removed_widget_bp_input_delegate_unbound']=True;self.remount_before=(count(self.w,'style'),count(self.w,'reset'));self.w.call_function('AddToPlayerScreen',0);self.frames=0;self.enter('remounted')
        elif self.phase=='remounted':
            self.frames+=1
            if self.frames<4:return
            require(count(self.w,'style')>self.remount_before[0] and count(self.w,'reset')>self.remount_before[1],'same-widget native Construct did not rerun');self.state['remounted_input']=self.switch_input(True);self.row['same_widget_remount_rebinds_bp_delegate_once']=True;self.w.call_function('RemoveFromParent');self.report['profiles'].append(self.row);self.states.append(self.state);self.report['matrices']=self.states;self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:
                # Initial hardware input can differ between trials; compare each
                # observed callback with its own native input value, plus stable
                # brush/material matrices across Profiles.
                self.report['source_python_state_pairs_match']=all(self.states[0][k]==self.states[1][k] for k in ('brushes','disabled','enabled'));self.finish()
    def cleanup(self):
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('StopAllAnimations');w.call_function('RemoveFromParent');w.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before);self.report['native_input_type_restored']=int(self.input.call_function('GetCurrentInputType'))==self.input_before
        if hasattr(self,'cls'):
            self.cls.get_cdo().set_property('PythonMixinProfile',self.cdo_profile)
            if self.root_class:self.cls.remove_from_root()
            self.report['all_widget_roots_and_profile_selector_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and self.cls.get_cdo().get_property('PythonMixinProfile')==self.cdo_profile
        self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native bound-action timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_BOUND_ACTION_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_BOUND_ACTION_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPBoundActionResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
