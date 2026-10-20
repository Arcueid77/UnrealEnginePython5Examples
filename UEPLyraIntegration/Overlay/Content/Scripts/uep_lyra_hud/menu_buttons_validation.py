"""Native widget/material/layout/latent-click comparison on real UMG frames."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import menu_buttons_mixin as policy
from .menu_buttons_contract import PROFILES,WIDGETS,FALSE_FIELDS,require,validate

def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def count(w,k):return sum(policy.evidence(w)[p+'_'+k] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None
def margin(v):return [float(getattr(v,k)) for k in ('Left','Top','Right','Bottom')]

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],completion_guard_fixture_sets_only_owned_widget_flag=True,owned_selection_fixture_enables_selectable_and_toggleable=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.classes={};self.cdos={};self.profile_index=0;self.widget_index=0;self.states=[]
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in dict(policy.CLASSES,**policy.CHILDREN).items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for k in policy.CLASSES:ue.register_declared_mixin(self.classes[k])
        self.probe=self.world.actor_spawn(ue.load_class('/Game/UEPValidation/BP_FoundationButtonsProbe.BP_FoundationButtonsProbe_C'));self.start_profile()
    def start_profile(self):
        self.profile=PROFILES[self.profile_index];self.profile_row=dict(profile=self.profile,widgets=[]);self.profile_states=[];self.widget_index=0
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.start_widget()
    def start_widget(self):
        self.key=WIDGETS[self.widget_index];self.w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[self.key],self.controller);self.w.add_to_root();self.widgets.append(self.w);ue.set_mixin_profile(self.w,self.profile);self.w.call_function('AddToPlayerScreen',0);self.row=dict(widget=self.key,raw_progress_cases=0,layout_cases=0);self.frames=0;self.enter('settle')
    def history(self,label,tag):
        file=self.path.parent/(self.profile+'-'+self.key+'-'+tag+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(label,str(file)),'native text export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [s.strip() for s in text.splitlines() if s.strip().startswith('Text=')]
    def animation(self,n):
        a=self.w.get_property(n);return dict(playing=bool(self.w.call_function('IsAnimationPlaying',a)),forward=bool(self.w.call_function('IsAnimationPlayingForward',a)),position=float(self.w.call_function('GetAnimationCurrentTime',a)))
    def scalars(self):return [[float(one(m.call_function('K2_GetScalarParameterValue',n))) for n in ('Hover_Animate','Pressed_Animate','bIsDisabled')] for m in policy.materials(self.w)]
    def baseline(self):
        w=self.w;w.call_function('PreConstruct',False);self.row['native_construct_and_preconstruct']=count(w,'pre')>0 and (self.key!='tile' or count(w,'construct')>0);w.call_function('SetIsSelectable',True);w.call_function('SetIsToggleable',True)
        values=[]
        for v in (-.25,0.,.5,1.,1.25):w.set_property('PressProgress',v);actual=float(one(w.call_function('GetPressProgress')));require(actual==v,'raw press progress differs');values.append(actual)
        self.row.update(raw_press_progress=True,raw_progress_cases=len(values));states=dict(progress=values)
        if self.key=='tile':
            states['history']=[self.history(w.get_property(n),n) for n in ('ButtonTextBlock','ButtonDescriptionTextBlock')];material=w.get_property('KeyArt').call_function('GetDynamicMaterial');texture=one(material.call_function('K2_GetTextureParameterValue','TileArt'));require(texture==w.get_property('KeyArtTexture'),'native tile art parameter differs');states['art']=path(texture);self.row['native_tile_art_parameter_matches']=True
        else:
            self.probe.call_function('SetLocalized',w);states['history']=[self.history(w.get_property('ButtonTextBlock'),'label')];states['layout']=self.layouts()
        self.row['localized_text_history_preserved']=all(any('NSLOCTEXT' in line for line in history) for history in states['history']);require(self.row['localized_text_history_preserved'],'localized text identity lost')
        w.call_function('SetIsEnabled',False);require(w.get_property('IsDisabled') is True,'native disabled callback missing');disabled=self.scalars();require(all(v==[0.,0.,1.] for v in disabled),'disabled scalar/reset differs')
        snapshot=(self.animation('OnHovered'),self.animation('OnPressed'));sounds=count(w,'clicksound');finished=count(w,'finished')
        for f in ('BP_OnHovered','BP_OnUnhovered','BP_OnSelected','BP_OnDeselected','BP_OnClicked'):w.call_function(f)
        require(snapshot==(self.animation('OnHovered'),self.animation('OnPressed')) and count(w,'clicksound')==sounds and count(w,'finished')==finished,'disabled callback changed animation/click');self.row['disabled_callbacks_are_noops']=True;w.call_function('SetIsEnabled',True);require(w.get_property('IsDisabled') is False and all(v==[0.,0.,0.] for v in self.scalars()),'enable scalar differs');self.row['material_disable_enable_and_reset']=True;states['disabled_scalars']=disabled;states['enabled_scalars']=self.scalars();self.profile_states.append(states)
    def layouts(self):
        w=self.w;rows=[];m=ue.find_struct('Margin');w.set_property('HitTestPadding_X',7.);w.set_property('HitTestPadding_Y',9.);w.set_property('TextLeftRightPadding',13.);w.set_property('InputPadding',m(Left=2.,Top=3.,Right=4.,Bottom=5.));w.set_property('InputHorzAlignment',2);w.set_property('InputVertAlignment',1)
        for bits in range(8):
            overlay=bool(bits&1);spacers=bool(bits&2);icon=bool(bits&4)
            for n,v in dict(UseImageOverlays=overlay,UseScaleChangeSpacers=spacers,UseIconOverride=icon,FlipIconXDimension=overlay).items():w.set_property(n,v)
            w.call_function('UpdateButtonStyles');row=dict(overlays=[int(w.get_property(n).call_function('GetVisibility')) for n in ('Ring','Glow','TextShadow')],spacers=[int(w.get_property(n).call_function('GetVisibility')) for n in ('AnimBoundSpacer_Left','AnimBoundSpacer_Right')],active=w.get_property('TextIconSwitch').call_function('GetActiveWidget')==w.get_property('IconOvr' if icon else 'TextOvr'),hit_padding=margin(w.get_property('ButtonBorder').get_property('Slot').get_property('Padding')),input_padding=margin(w.get_property('InputActionWidget').get_property('Slot').get_property('Padding')))
            require(row['overlays']==[3 if overlay else 1]*3 and row['spacers']==[3 if spacers else 1]*2 and row['active'] and row['hit_padding']==[7.,9.,7.,9.] and row['input_padding']==[2.,3.,4.,5.],'menu layout native values differ')
            slot=w.get_property('InputActionWidget').get_property('Slot');require(int(slot.get_property('HorizontalAlignment'))==2 and int(slot.get_property('VerticalAlignment'))==1,'input alignment differs')
            if icon:row['scale']=float(w.get_property('Icon').get_property('RenderTransform').Scale.x);require(row['scale']==(-1. if overlay else 1.),'icon flip differs')
            else:row['text_padding']=margin(w.get_property('TextOvr').get_property('Slot').get_property('Padding'));require(row['text_padding']==[13.,0.,13.,0.],'text padding differs')
            rows.append(row)
        self.row['layout_cases']=len(rows);return rows
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'menu phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<3:return
            self.baseline();self.w.call_function('BP_OnHovered');self.enter('hover')
        elif self.phase=='hover':
            if self.animation('OnHovered')['position']<.01:return
            require(self.animation('OnHovered')['forward'],'native hover not forward');self.w.call_function('SetIsSelected',True,False);require(self.w.call_function('GetSelected'),'owned selectable widget did not select');self.enter('selected')
        elif self.phase=='selected':
            if self.animation('OnPressed')['position']<.01:return
            require(self.animation('OnPressed')['forward'] and count(self.w,'select')>0,'native selected callback missing');self.row['native_hover_and_selection_animation_frames']=True;self.w.call_function('SetIsSelected',False,False);self.w.call_function('BP_OnUnhovered');self.w.call_function('ResetMaterials');self.click_before=count(self.w,'finished');sound_before=count(self.w,'clicksound');self.w.call_function('BP_OnClicked');require(count(self.w,'clicksound')==sound_before+1,'click immediate native continuation missing');self.enter('click')
        elif self.phase=='click':
            if count(self.w,'finished')<=self.click_before:return
            require(not self.animation('OnPressed')['forward'],'natural click completion did not reverse');self.row['native_click_immediate_and_natural_completion']=True;self.w.call_function('ResetMaterials');self.click_before=count(self.w,'finished');self.w.call_function('BP_OnClicked');self.w.set_property('IsDisabled',True);self.enter('disabled_click')
        elif self.phase=='disabled_click':
            # Only this owned fixture flag changes: actual SetIsEnabled(False)
            # also stops OnPressed through ResetMaterials, cancelling the player.
            if count(self.w,'finished')<=self.click_before:return
            require(not self.animation('OnPressed')['playing'] or self.animation('OnPressed')['forward'],'disabled finish unexpectedly reversed');self.row['disabled_flag_at_natural_completion_keeps_reverse_guard']=True;self.row['native_finished_callbacks']=count(self.w,'finished');self.w.set_property('IsDisabled',False);self.w.call_function('RemoveFromParent');self.profile_row['widgets'].append(self.row);self.widget_index+=1
            if self.widget_index<len(WIDGETS):self.start_widget()
            else:
                self.report['profiles'].append(self.profile_row);self.states.append(self.profile_states);self.report['matrices']=self.states;self.profile_index+=1
                if self.profile_index<len(PROFILES):self.start_profile()
                else:self.report['source_python_state_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        if hasattr(self,'probe') and policy.valid(self.probe):self.probe.actor_destroy()
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('StopAllAnimations');w.call_function('RemoveFromParent');w.remove_from_root()
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for c in getattr(self,'class_roots',[]):c.remove_from_root()
        self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native menu UI timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_MENU_BUTTONS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_MENU_BUTTONS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPMenuButtonsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
