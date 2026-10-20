"""Native five-FText setter, actual UMG selection/click and latent Finished."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import session_button_mixin as policy
from .session_button_contract import PROFILES,FALSE_FIELDS,require,validate

def count(w,key):return sum(policy.evidence(w)[p+'_'+key] for p in ('python','fallback'))
def one(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value
def path(value):return value.get_path_name() if value is not None else None

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],direct_blueprint_event_inputs=['BP_OnHovered','BP_OnUnhovered']);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.holders=[];self.index=0;self.states=[];self.cls=None;self.cdo_before=None;self.class_root=False;self.probe=None
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);self.class_root=not self.cls.is_rooted()
        if self.class_root:self.cls.add_to_root()
        ue.register_declared_mixin(self.cls);self.cdo_before=self.cls.get_cdo().get_property('PythonMixinProfile');self.probe=self.world.actor_spawn(ue.load_class('/Game/UEPValidation/BP_SessionButtonTextProbe.BP_SessionButtonTextProbe_C'));self.texture=ue.load_object(ue.find_class('Texture2D'),'/Game/UI/Menu/Art/T_UI_TileArt_Quickplay.T_UI_TileArt_Quickplay');self.start_profile()
    def start_profile(self):
        self.profile=PROFILES[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);self.w.add_to_root();self.widgets.append(self.w);ue.set_mixin_profile(self.w,self.profile);holder_cls=ue.load_class('/Game/UI/Menu/Experiences/W_NonInteractiveSpinner.W_NonInteractiveSpinner_C');self.holder=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,holder_cls,self.controller);self.holder.add_to_root();self.holders.append(self.holder);root=self.holder.get_property('WidgetTree').get_property('RootWidget');root.call_function('SetContent' if root.is_a(ue.find_class('ContentWidget')) else 'AddChild',self.w);self.holder.call_function('AddToPlayerScreen',0);self.holder.call_function('ActivateWidget');self.row=dict(profile=self.profile);self.state={};self.frames=0;self.enter('settle')
    def materials(self):return [self.w.get_property('ButtonBorder').call_function('GetDynamicMaterial')]+[self.w.get_property(n).call_function('GetDynamicFontMaterial') for n in ('GameModeText','PingText','PlayersText','MapNameText','MaxPlayersText')]
    def scalar(self,materials,parameter):return [float(one(m.call_function('K2_GetScalarParameterValue',parameter))) for m in materials]
    def history(self,name):
        file=self.path.parent/(self.profile+'-'+name+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(self.w.get_property(name),str(file)),'native session text export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');values=[line.strip() for line in text.splitlines() if line.strip().startswith('Text=')];require(len(values)==1 and 'NSLOCTEXT' in values[0],'native five-FText label history missing');return values[0]
    def animation(self,name):
        animation=self.w.get_property(name);return dict(playing=bool(self.w.call_function('IsAnimationPlaying',animation)),forward=bool(self.w.call_function('IsAnimationPlayingForward',animation)),time=float(self.w.call_function('GetAnimationCurrentTime',animation)))
    def checks(self):
        w=self.w;require(count(w,'construct')>0 and count(w,'pre')>0,'actual native session Construct/PreConstruct missing');self.row['native_construct_and_preconstruct']=True;self.probe.call_function('SetLocalized',w);histories=[self.history(n) for n in ('GameModeText','MapNameText','PingText','PlayersText','MaxPlayersText')];self.state['histories']=histories;self.row['native_five_ftext_histories_preserved']=True;materials=self.materials();labels=[w.get_property(n).call_function('GetDynamicFontMaterial') for n in ('MapLabel','PingLabel')]
        for m in materials+labels:m.call_function('SetScalarParameterValue','Hover_Animate',.75);m.call_function('SetScalarParameterValue','Pressed_Animate',.5)
        w.call_function('ResetMaterials');require(self.scalar(materials,'Hover_Animate')==[0.]*6 and self.scalar(materials,'Pressed_Animate')==[0.]*6 and self.scalar(labels,'Hover_Animate')==[.75,.75] and self.scalar(labels,'Pressed_Animate')==[.5,.5],'source six reset targets/unused label materials differ');self.row['native_six_target_reset_preserves_unused_label_scalars']=True;w.call_function('ResetFontMaterials',w.get_property('MapLabel'));require(self.scalar(labels,'Hover_Animate')==[0.,.75] and self.scalar(labels,'Pressed_Animate')==[0.,.5],'native font reset differs');self.row['native_font_reset_function']=True
        textures=[]
        for texture in (self.texture,None,self.texture):w.call_function('SetMapImage',texture);actual=one(materials[0].call_function('K2_GetTextureParameterValue','MapTileArt'));require(actual==self.texture,'native null map texture must retain prior value');textures.append(path(actual))
        self.state['textures']=textures;self.row['native_texture_identity_and_null_retention']=True
        for m,v in zip(materials[1:],(.1,.2,.3,.4,.5)):m.call_function('SetScalarParameterValue','bIsDisabled',v)
        w.call_function('SetIsEnabled',False);disabled=self.scalar(materials,'bIsDisabled');require(w.get_property('IsDisabled') and all(abs(a-b)<1e-5 for a,b in zip(disabled,[1.,.1,.2,.3,.4,.5])),'only border disabled parameter differs');snapshot=[self.animation(n) for n in ('OnHovered','OnPressed')];before=count(w,'finished');w.call_function('BP_OnHovered');w.call_function('BP_OnUnhovered');w.call_function('HandleButtonClicked');require([self.animation(n) for n in ('OnHovered','OnPressed')]==snapshot and count(w,'finished')==before,'disabled handlers started animation');self.row['native_only_border_disabled_and_blocked_handlers']=True;w.call_function('SetIsEnabled',True);w.call_function('BP_OnHovered');require(self.animation('OnHovered')['forward'],'native hover animation direction differs');w.call_function('BP_OnUnhovered');w.call_function('SetIsSelectable',True);w.call_function('SetIsToggleable',True);w.call_function('SetIsSelected',True);require(self.animation('OnPressed')['forward'],'native selection animation direction differs');self.row['native_enabled_selection_and_hover_directions']=True;self.enter('selected')
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'session button phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<4:return
            self.checks()
        elif self.phase=='selected':
            position=self.animation('OnPressed')['time']
            if position<.01:return
            self.finished_before=count(self.w,'finished');self.w.call_function('HandleButtonClicked');after=self.animation('OnPressed')['time'];require(abs(after-position)<.08 and count(self.w,'click')>0,'native click did not retain current animation time');self.row['native_mid_animation_click_continuity']=True;self.enter('finished')
        elif self.phase=='finished':
            delta=count(self.w,'finished')-self.finished_before
            if delta<1:return
            require(delta==1,'native Finished fired more than once');require(not self.animation('OnPressed')['forward'],'native Finished did not reverse OnPressed');self.frames=0;self.enter('quiet')
        elif self.phase=='quiet':
            self.frames+=1
            if self.frames<12 or self.animation('OnPressed')['playing']:return
            require(abs(self.animation('OnPressed')['time'])<.001,'native Finished reverse did not settle at start')
            require(count(self.w,'finished')-self.finished_before==1,'native Finished repeated after completion');self.row.update(native_finished_callbacks=1,native_actual_finished_then_reverse_and_quiet=True);self.state['reset_scalars']=self.scalar(self.materials(),'Hover_Animate');self.w.call_function('StopAllAnimations');self.holder.call_function('DeactivateWidget');self.holder.call_function('RemoveFromParent');self.report['profiles'].append(self.row);self.states.append(self.state);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report.update(source_python_state_pairs_match=self.states[0]==self.states[1],matrices=self.states);self.finish()
    def cleanup(self):
        for w in self.widgets:
            ue.clear_mixin_profile(w);w.call_function('StopAllAnimations');w.call_function('RemoveFromParent');w.remove_from_root()
        for holder in self.holders:
            if holder.call_function('IsActivated'):holder.call_function('DeactivateWidget')
            holder.call_function('RemoveFromParent');holder.remove_from_root()
        if self.cls is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.cdo_before)
        if self.class_root:self.cls.remove_from_root()
        if valid(self.probe):self.probe.actor_destroy()
        self.report['owned_roots_profiles_and_gameplay_health_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets+self.holders) and (self.cls is None or self.cls.get_cdo().get_property('PythonMixinProfile')==self.cdo_before) and (not hasattr(self,'health_before') or self.healths()==self.health_before)
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<250.,'native session button timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SESSION_BUTTON_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SESSION_BUTTON_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSessionButtonResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
