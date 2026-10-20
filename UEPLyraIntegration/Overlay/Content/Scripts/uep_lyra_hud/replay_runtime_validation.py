"""Natural component/HUD/tick lifecycle and native SBorder pointer/reply route."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .replay_browser_validation import Validation as Browser,arg,path,one
from . import replay_browser_mixin as browser_policy,replay_runtime_mixin as policy
from .replay_runtime_contract import FALSE_FIELDS,require,validate
def count(obj,kind,key):return sum(policy.evidence(obj,kind)[p+'_'+key] for p in ('python','fallback'))
def components(controller,cls):return list(one(controller.call_function('K2_GetComponentsByClass',cls)))
class Validation(Browser):
    def __init__(self,result):
        super().__init__(result);self.profile=arg('UEPReplayRuntimeProfile','Python');self.report=dict(status='running',error=None,profile=self.profile,synthetic_slate_pointer_inputs=[.75,.2],native_handled_replies=[],native_seek_samples=[],native_tick_samples=0,direct_zero_width_slate_pointer_input=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.runtime_classes={};self.fixture_actors=[];self.runtime_checks_done=False;self.seek_index=0;self.template_profiles={}
        for kind,name in policy.CLASSES.items():
            cls=ue.load_class(name);self.runtime_classes[kind]=cls
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            ue.register_declared_mixin(cls);self.cdos[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        prefix=policy.CLASSES['hud'].split('.')[0]+'.'
        for widget in ue.tobject_iterator(self.runtime_classes['scrub']):
            if widget.get_path_name().startswith(prefix) and ':WidgetTree.' in widget.get_path_name():self.template_profiles[widget]=widget.get_property('PythonMixinProfile');widget.set_property('PythonMixinProfile',self.profile)
        self.report['early_runtime_profiles_selected_before_natural_beginplay']=True
    def begin(self):
        super().begin();handlers=components(self.controller,self.runtime_classes['handler']);require(len(handlers)==1 and count(handlers[0],'handler','begin')==1 and str(ue.get_mixin_profile(handlers[0]))==self.profile,'natural regular controller component/profile missing');self.report['natural_regular_controller_component_beginplay']=True;self.wrong_controller=self.world.actor_spawn(ue.find_class('PlayerController'));self.fixture_actors.append(self.wrong_controller);self.wrong_component=self.wrong_controller.add_actor_component(self.runtime_classes['handler'],'UEPWrongReplayOwner');self.idle=browser_policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.runtime_classes['scrub'],self.controller);self.idle.add_to_root();self.roots.append(self.idle);self.widgets.append(self.idle);self.idle.call_function('AddToPlayerScreen',0);self.frames=0;self.enter('runtime_idle')
    def zero_pointer(self):
        widget=browser_policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.runtime_classes['scrub'],self.controller);widget.add_to_root();self.roots.append(widget);self.widgets.append(widget);border=widget.get_property('Border_0').take_widget();geometry=border.get_cached_geometry();require(geometry.get_local_size()[0]==0.,'unmounted native geometry must have zero width');pointer=ue.FPointerEvent(0,(0.,0.),(0.,0.),'LeftMouseButton');require(border.on_mouse_button_down(geometry,pointer) and count(widget,'scrub','seek')==1,'native zero width pointer/reply missing');self.report['native_zero_width_pointer_handled']=True
    def native_pointer(self,fraction):
        border=self.scrub.get_property('Border_0');slate=border.take_widget();geometry=slate.get_cached_geometry();width,height=geometry.get_local_size();require(width>0. and height>0.,'actual rendered scrub geometry missing');native_geometry=border.call_function('GetCachedGeometry');absolute=one(browser_policy.lib('SlateBlueprintLibrary').call_function('LocalToAbsolute',native_geometry,ue.find_struct('Vector2D')(X=width*fraction,Y=height*.5)));pointer=ue.FPointerEvent(0,(float(absolute.x),float(absolute.y)),(float(absolute.x),float(absolute.y)),'LeftMouseButton');before=count(self.scrub,'scrub','seek');handled=bool(slate.on_mouse_button_down(geometry,pointer));require(handled and count(self.scrub,'scrub','seek')==before+1,'bound native pointer/Handled route missing');length,x,w=policy.evidence(self.scrub,'scrub')['last_seek_inputs'];target=float(length)*float(x)/float(w);require(abs(float(x)/float(w)-fraction)<.002,'native geometry scalar fraction differs');self.report['native_handled_replies'].append(handled);self.seek_target=target;self.seek_started=time.monotonic();self.enter('runtime_seek')
    def observe(self):
        require(time.monotonic()-self.phase_started<(120. if self.phase=='playback' else 35.),'replay runtime phase timeout: '+self.phase)
        if self.phase=='runtime_idle':
            self.frames+=1
            if self.frames<4 or count(self.idle,'scrub','tick')<1 or count(self.wrong_component,'handler','begin')<1:return
            require(self.wrong_component.get_property('As Lyra Replay Player Controller') is None,'wrong controller owner stored replay controller');self.report['native_wrong_controller_owner_no_effect']=True;require(abs(float(self.idle.get_property('TimeScrubberWidget').get_property('Percent')))<1e-6,'native idle tick percent differs');self.report['native_idle_umg_tick_zero_percent']=True;self.idle.call_function('RemoveFromParent');self.zero_pointer();self.frames=0;self.enter('runtime_idle_quiet');return
        if self.phase=='runtime_idle_quiet':
            self.frames+=1
            if self.frames<6 or 'Divide by zero: Divide_DoubleDouble' not in self.path.with_suffix('.log').read_text(encoding='utf-8-sig',errors='replace'):return
            self.report['native_zero_divide_warning_preserved']=True
            # This fixture controller belongs to the initial world. Destroy it
            # and verify destruction before replay travel invalidates wrappers.
            for actor in self.fixture_actors:actor.actor_destroy();require(not valid(actor),'owned generic controller destruction failed')
            self.fixture_actors=[];self.enter('empty');return
        if self.phase=='playback' and not self.runtime_checks_done:
            if not self.engine.call_function('IsPlaying'):return
            for world in ue.all_worlds():
                if world.get_world_type() not in (1,3) or world==self.original_world:continue
                controller=browser_policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)
                if not valid(controller) or not controller.is_a(ue.find_class('LyraReplayPlayerController')):continue
                self.world=world;self.controller=controller
                huds=[w for w in ue.tobject_iterator(self.runtime_classes['hud']) if w.call_function('IsInViewport') and w.call_function('IsActivated')]
                if not huds:return
                hud=huds[0];handlers=components(controller,self.runtime_classes['handler']);require(len(handlers)==1 and count(handlers[0],'handler','begin')>0 and handlers[0].get_property('As Lyra Replay Player Controller')==controller and str(ue.get_mixin_profile(handlers[0]))==self.profile,'natural replay handler/profile missing');require(count(hud,'hud','construct')>0 and str(ue.get_mixin_profile(hud))==self.profile,'natural replay HUD activation/profile missing');self.scrub=hud.get_property('W_Replay_ScrubBar');require(valid(self.scrub) and str(ue.get_mixin_profile(self.scrub))==self.profile,'natural replay scrub Profile missing');self.widgets.append(hud);self.report.update(natural_replay_controller_component_creates_hud=True,native_replay_hud_construct_activates=True);self.world=world;self.controller=controller;self.runtime_hud=hud;self.frames=0;self.enter('runtime_ticks');return
            return
        if self.phase=='runtime_ticks':
            sample=policy.evidence(self.scrub,'scrub').get('last_tick_inputs')
            if not sample or sample[1]<=0:return
            expected=float(sample[0])/float(sample[1]);actual=float(self.scrub.get_property('TimeScrubberWidget').get_property('Percent'));require(abs(actual-expected)<.00001,'actual UMG tick percent differs from sampled native getters');self.report['native_tick_samples']+=1
            if self.report['native_tick_samples']<3:return
            self.report['native_umg_tick_percent_matches_actual_getter_samples']=True;self.native_pointer(.75);return
        if self.phase=='runtime_seek':
            require(time.monotonic()-self.seek_started<20.,'native replay seek did not settle');current=float(self.lyra.call_function('GetReplayCurrentTime'))
            # GotoTime publishes the target before its async checkpoint task
            # finishes. Wait for actual playback to resume before the next
            # pointer event;the native driver ignores overlapping goto tasks.
            if current<self.seek_target+.05 or current>self.seek_target+.25:return
            self.report['native_seek_samples'].append(dict(fraction=[.75,.2][self.seek_index],target=self.seek_target,observed=current));self.seek_index+=1
            if self.seek_index<2:self.native_pointer(.2)
            else:self.report.update(native_slate_pointer_events_seek_forward_and_back=True,native_original_handled_reply_preserved=True);self.runtime_checks_done=True;self.enter('playback')
            return
        if self.phase=='stopped':self.report['native_real_recordings_query_and_playback']=True
        super().observe()
    def cleanup(self):
        if hasattr(self,'world') and (not valid(self.world) or not valid(self.controller)):
            for world in ue.all_worlds():
                if world.get_world_type() not in (1,3):continue
                controller=browser_policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)
                if valid(controller):self.world=world;self.controller=controller;break
        super().cleanup()
        for widget,profile in self.template_profiles.items():widget.set_property('PythonMixinProfile',profile)
        for actor in self.fixture_actors:
            if valid(actor) and actor.is_a(ue.find_class('Actor')):actor.actor_destroy()
        self.report['owned_roots_profiles_settings_input_and_fixture_actors_restored']=self.report.get('owned_roots_profiles_settings_and_input_restored',False) and all(not valid(a) or a.call_function('IsActorBeingDestroyed') for a in self.fixture_actors) and all(widget.get_property('PythonMixinProfile')==p for widget,p in self.template_profiles.items())
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_REPLAY_RUNTIME_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_REPLAY_RUNTIME_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPReplayRuntimeResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
