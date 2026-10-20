"""Mount experience tiles; compare native callbacks, localized text and sound."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import experience_tile_mixin as policy
from .experience_tile_contract import PROFILES,FALSE_FIELDS,require,validate

def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def count(w,k):return sum(policy.evidence(w)[p+'_'+k] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],owned_selection_fixture_enables_selectable_and_toggleable=True,completion_guard_fixture_sets_only_owned_widget_flag=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.owned_audio=[];self.index=0;self.states=[]
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);self.root_class=not self.cls.is_rooted()
        if self.root_class:self.cls.add_to_root()
        self.cdo_profile=self.cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(self.cls);self.gi=policy.lib('GameplayStatics').call_function('GetGameInstance',self.world);require(self.gi.is_a(ue.load_class(policy.GAME_INSTANCE)),'actual Lyra GameInstance missing');self.original_sound=self.gi.get_property('Audio_LobbySelect');self.sentinel=ue.new_object(ue.find_class('AudioComponent'));self.sentinel.add_to_root();self.probe=self.world.actor_spawn(ue.load_class('/Game/UEPValidation/BP_ExperienceTileProbe.BP_ExperienceTileProbe_C'));self.select_sound=ue.load_object(ue.find_class('SoundBase'),policy.SOUNDS['select']);self.texture=ue.load_object(ue.find_class('Texture2D'),'/Game/UI/Menu/Art/T_UI_TileArt_Quickplay.T_UI_TileArt_Quickplay');self.start_profile()
    def start_profile(self):
        self.profile=PROFILES[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);self.w.add_to_root();self.widgets.append(self.w);ue.set_mixin_profile(self.w,self.profile);self.w.call_function('AddToPlayerScreen',0);self.row=dict(profile=self.profile,raw_progress_cases=0,texture_cases=0,spawned_click_audio=[]);self.frames=0;self.enter('settle')
    def history(self,label,tag):
        file=self.path.parent/(self.profile+'-'+tag+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(label,str(file)),'native text export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [s.strip() for s in text.splitlines() if s.strip().startswith('Text=')]
    def animation(self,n):
        a=self.w.get_property(n);return dict(playing=bool(self.w.call_function('IsAnimationPlaying',a)),forward=bool(self.w.call_function('IsAnimationPlayingForward',a)),position=float(self.w.call_function('GetAnimationCurrentTime',a)))
    def scalars(self):return [[float(one(m.call_function('K2_GetScalarParameterValue',n))) for n in ('Hover_Animate','Pressed_Animate','bIsDisabled')] for m in policy.materials(self.w)]
    def audio_objects(self):return [o for o in ue.tobject_iterator(ue.find_class('AudioComponent')) if policy.valid(o) and o.get_property('Sound')==self.select_sound]
    def start_click(self):
        before={path(c) for c in self.audio_objects()};self.gi.set_property('Audio_LobbySelect',self.sentinel);self.click_before=count(self.w,'finished');sound_before=count(self.w,'clicksound');self.w.call_function('BP_OnClicked');require(count(self.w,'clicksound')==sound_before+1,'native immediate click continuation missing');require(self.gi.get_property('Audio_LobbySelect') is None,'source unwired return must clear GameInstance sound field');components=[c for c in self.audio_objects() if path(c) not in before];require(len(components)==1,'native SpawnSound2D component missing or duplicate');c,=components;self.owned_audio.append(c);self.row['spawned_click_audio'].append(dict(sound=path(c.get_property('Sound')),playing=bool(c.call_function('IsPlaying')),auto_destroy=bool(c.get_property('bAutoDestroy')),existing_before_click=False,ui_sound=bool(c.get_property('bIsUISound')),spatialized=bool(c.get_property('bAllowSpatialization')),stop_with_owner=bool(c.get_property('bStopWhenOwnerDestroyed'))))
    def baseline(self):
        w=self.w;w.call_function('PreConstruct',False);self.row['native_construct_and_preconstruct']=count(w,'pre')>0 and count(w,'construct')>0;w.call_function('SetIsSelectable',True);w.call_function('SetIsToggleable',True);self.probe.call_function('SetLocalized',w);histories=[self.history(w.get_property(n),n) for n in ('ExperienceTitle','MapTitle','ExperienceDescription')];self.row['localized_three_text_histories_preserved']=all(any('NSLOCTEXT' in s for s in h) for h in histories)
        values=[]
        for value in (-.25,0.,.5,1.,1.25):w.set_property('PressProgress',value);actual=float(one(w.call_function('GetPressProgress')));require(actual==value,'unclamped progress differs');values.append(actual)
        self.row['raw_progress_cases']=len(values);textures=[]
        for value in (self.texture,None,self.texture):
            w.call_function('UpdateTileArt',value);actual=one(w.get_property('KeyArt').call_function('GetDynamicMaterial').call_function('K2_GetTextureParameterValue','TileArt'));textures.append(path(actual));self.report['texture_observations']=dict(profile=self.profile,input=path(value),actual=path(actual))
            # Native SetTextureParameterValueInternal ignores null assignments.
            require(actual==self.texture,'native null texture must retain previous parameter')
        self.row.update(texture_cases=len(textures),tile_art_parameter_identity=True,null_texture_input_retains_previous_native_parameter=True)
        for material,value in zip(policy.materials(w)[1:],(.25,.5,.75)):material.call_function('SetScalarParameterValue','bIsDisabled',value)
        w.call_function('SetIsEnabled',False);disabled=self.scalars();require(w.get_property('IsDisabled') is True and disabled==[[0.,0.,1.],[0.,0.,.25],[0.,0.,.5],[0.,0.,.75]],'only-border disable/all-four reset differs');snapshot=(self.animation('OnHovered'),self.animation('OnPressed'));sounds=count(w,'clicksound')
        for f in ('BP_OnHovered','BP_OnUnhovered','BP_OnSelected','BP_OnDeselected','BP_OnClicked'):w.call_function(f)
        require(snapshot==(self.animation('OnHovered'),self.animation('OnPressed')) and count(w,'clicksound')==sounds,'disabled callback changed animation/sound');self.row['disabled_callbacks_are_noops']=True;w.call_function('SetIsEnabled',True);enabled=self.scalars();require(w.get_property('IsDisabled') is False and enabled==[[0.,0.,0.],[0.,0.,.25],[0.,0.,.5],[0.,0.,.75]],'enable changed font disabled parameters');self.row['only_border_disable_parameter_and_all_four_material_resets']=True;self.states.append(dict(history=histories,progress=values,textures=textures,disabled=disabled,enabled=enabled));self.report['matrices']=self.states
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'experience phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<3:return
            self.baseline();self.w.call_function('BP_OnHovered');self.enter('hover')
        elif self.phase=='hover':
            if self.animation('OnHovered')['position']<.01:return
            require(self.animation('OnHovered')['forward'],'native hover animation missing');self.w.call_function('SetIsSelected',True,False);require(self.w.call_function('GetSelected'),'owned selectable tile did not select');self.enter('selected')
        elif self.phase=='selected':
            if self.animation('OnPressed')['position']<.01:return
            require(self.animation('OnPressed')['forward'] and count(self.w,'select')>0,'actual selected callback missing');before=count(self.w,'deselect');self.w.call_function('SetIsSelected',False,False);require(count(self.w,'deselect')==before+1 and not self.w.call_function('GetSelected'),'actual deselection callback missing');self.row['native_hover_selection_and_deselection_callbacks']=True;self.w.call_function('BP_OnUnhovered');self.w.call_function('ResetMaterials');self.start_click();self.enter('click')
        elif self.phase=='click':
            if count(self.w,'finished')<=self.click_before:return
            require(not self.animation('OnPressed')['forward'],'natural click completion did not reverse');self.row['native_click_immediate_and_natural_completion']=True;self.w.call_function('ResetMaterials');self.start_click();self.w.set_property('IsDisabled',True);self.enter('disabled_click')
        elif self.phase=='disabled_click':
            if count(self.w,'finished')<=self.click_before:return
            require(not self.animation('OnPressed')['playing'] or self.animation('OnPressed')['forward'],'disabled completion reversed');self.row.update(disabled_flag_at_natural_completion_keeps_reverse_guard=True,unwired_audio_return_clears_game_instance_reference=True,native_finished_callbacks=count(self.w,'finished'));self.w.set_property('IsDisabled',False);self.w.call_function('RemoveFromParent');self.report['profiles'].append(self.row);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report['source_python_state_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        if hasattr(self,'probe') and policy.valid(self.probe):self.probe.actor_destroy()
        for c in self.owned_audio:
            if policy.valid(c):c.call_function('Stop')
            if policy.valid(c):c.call_function('K2_DestroyComponent',c)
        self.report['only_new_owned_click_audio_stopped_or_destroyed']=all(not policy.valid(c) or not c.call_function('IsPlaying') for c in self.owned_audio)
        if hasattr(self,'gi'):self.gi.set_property('Audio_LobbySelect',self.original_sound);self.report['original_game_instance_sound_reference_restored']=self.gi.get_property('Audio_LobbySelect')==self.original_sound
        if hasattr(self,'sentinel') and self.sentinel.is_rooted():self.sentinel.remove_from_root()
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('StopAllAnimations');w.call_function('RemoveFromParent');w.remove_from_root()
        if hasattr(self,'cls'):
            self.cls.get_cdo().set_property('PythonMixinProfile',self.cdo_profile)
            if self.root_class:self.cls.remove_from_root()
            self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and self.cls.get_cdo().get_property('PythonMixinProfile')==self.cdo_profile
        self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native experience timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPERIENCE_TILE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPERIENCE_TILE_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExperienceTileResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
