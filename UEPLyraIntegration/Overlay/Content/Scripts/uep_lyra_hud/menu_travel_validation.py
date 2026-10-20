"""Native open-menu button, actual confirmation and original soft-map travel."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import menu_layers_mixin as policy
from . import startup_login_mixin as startup_policy
from . import frontend_menu_mixin as frontend_policy
from .menu_travel_contract import MAP,EXPERIENCE,EXPERIENCE_CLASS,FRONTEND,FALSE_FIELDS,require,validate

def path(obj):return obj.get_path_name() if obj is not None else None
def count(widget,name):return sum(policy.evidence(widget)[p+'_menu_'+name] for p in ('python','fallback'))

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPMenuTravelProfile=')),'Python');self.report=dict(status='running',error=None,profile=self.profile,native_frontend_press_start_interaction=False);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.class_roots=[];self.widgets=[];self.roots=[];self.proxies=[];self.frontend_start_clicked=False
    def begin(self):
        self.report['initial_native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.report['old_world_path']=path(self.world);self.health_before=self.healths();self.classes={'menu':ue.load_class(policy.CLASSES['menu']),'layout':ue.load_class(policy.CLASSES['layout']),'frontend':ue.load_class(frontend_policy.CLASS),'open':ue.load_class('/Game/UI/Hud/W_OpenMenuTouchButton.W_OpenMenuTouchButton_C'),**{k:ue.load_class(v) for k,v in startup_policy.CLASSES.items()}}
        for cls in self.classes.values():
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            ue.register_declared_mixin(cls)
        self.cdos={cls:cls.get_cdo().get_property('PythonMixinProfile') for cls in self.classes.values()}
        for cls in self.cdos:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        file=self.path.parent/'menu-original-reference-cdo.t3d';require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(self.classes['menu'].get_cdo(),str(file)),'native menu reference export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');require('FrontEndMapReference="'+MAP+'"' in text and 'FrontEndExperienceReference="LyraExperienceDefinition:'+EXPERIENCE+'"' in text,'original menu map/experience CDO references changed');self.report['original_reference_payload_preserved']=True
        initial_mode=policy.lib('GameplayStatics').call_function('GetGameMode',self.world);options=initial_mode.get_property('OptionsString');require(policy.lib('GameplayStatics').call_function('HasOption',options,'UEPMenuTravelSentinel'),'initial travel sentinel missing');self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'));self.push_cls=ue.find_class('AsyncAction_PushContentToLayerForPlayer');self.confirm_cls=ue.find_class('AsyncAction_ShowConfirmation');before={path(p) for p in ue.tobject_iterator(self.push_cls)}
        self.button=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes['open'],self.controller);self.button.add_to_root();self.roots.append(self.button);self.widgets.append(self.button);ue.set_mixin_profile(self.button,self.profile);self.afterpush=[];self.button.get_property('OpenButton').call_function('HandleButtonClicked');new=[p for p in ue.tobject_iterator(self.push_cls) if path(p) not in before];require(len(new)==1,'native touch-menu component handler must create one push proxy')
        def pushed(widget):self.afterpush.append(widget)
        new[0].bind_event('AfterPush',pushed);self.proxies.append((new[0],'AfterPush',pushed));self.enter('menu')
    def observe(self):
        require(time.monotonic()-self.phase_started<(120. if self.phase=='arrival' else 30.),'native menu travel phase timeout: '+self.phase)
        if self.phase=='menu':
            if not self.afterpush:return
            require(len(self.afterpush)==1 and path(self.afterpush[0].get_class())==policy.CLASSES['menu'],'native open-menu AfterPush differs');self.menu=self.afterpush[0]
            if not self.menu.is_rooted():self.menu.add_to_root();self.roots.append(self.menu)
            self.widgets.append(self.menu);ue.set_mixin_profile(self.menu,self.profile);require(self.menu.call_function('IsActivated'),'native pushed game menu inactive');self.report['native_open_menu_click_afterpush']=True;baseline={path(p) for p in ue.tobject_iterator(self.confirm_cls)};self.results=[];self.menu.get_property('ReturnButton').call_function('HandleButtonClicked');new=[p for p in ue.tobject_iterator(self.confirm_cls) if path(p) not in baseline];require(len(new)==1,'native return button must create one confirmation')
            def result(value):self.results.append(int(value))
            new[0].bind_event('OnResult',result);self.proxies.append((new[0],'OnResult',result));self.enter('confirmation')
        elif self.phase=='confirmation':
            dialogs=[w for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen')) if w.call_function('IsActivated')]
            if not dialogs:return
            require(len(dialogs)==1,'expected one native return-to-frontend confirmation');buttons=dialogs[0].get_property('EntryBox_Buttons').call_function('GetAllEntries');require(len(buttons)==2,'native confirmation Yes/No buttons missing');buttons[0].call_function('HandleButtonClicked');calls=count(self.menu,'result');require(self.results==[0] and calls==1,'native confirmed menu result missing');require(self.healths()==self.health_before,'menu travel request changed original gameplay health');self.report.update(confirmation_results=list(self.results),menu_result_handler_calls=calls,native_yes_confirmation_result=True,native_confirmed_branch=True,original_gameplay_health_unchanged_until_travel_requested=True);self.enter('arrival')
        elif self.phase=='arrival':
            for world in ue.all_worlds():
                if world.get_world_type() not in (1,3) or path(world)!=MAP:continue
                controller=startup_policy.controller(world,0)
                if not valid(controller) or controller is self.controller:continue
                mode=policy.lib('GameplayStatics').call_function('GetGameMode',world);state=policy.lib('GameplayStatics').call_function('GetGameState',world)
                if not valid(mode) or not valid(state):continue
                options=mode.get_property('OptionsString');experience_option=policy.lib('GameplayStatics').call_function('ParseOption',options,'Experience');require(experience_option==EXPERIENCE and not policy.lib('GameplayStatics').call_function('HasOption',options,'UEPMenuTravelSentinel') and not policy.lib('GameplayStatics').call_function('HasOption',options,'NumBots'),'native absolute travel map options differ')
                manager=state.get_component_by_type(ue.find_class('LyraExperienceManagerComponent'))
                if not valid(manager):continue
                experience=manager.get_property('CurrentExperience')
                if not valid(experience):continue
                require(path(experience.get_class())==EXPERIENCE_CLASS,'native frontend experience differs');frontend_component=state.get_component_by_type(ue.find_class('LyraFrontendStateComponent'))
                if not valid(frontend_component):continue
                startup=[w for w in ue.tobject_iterator(self.classes['startup']) if w.call_function('GetOwningPlayer')==controller and w.call_function('IsActivated')]
                if startup and not self.frontend_start_clicked:
                    require(len(startup)==1,'unexpected duplicate native frontend startup screens');startup[0].get_property('PressStartButton').call_function('HandleButtonClicked');self.frontend_start_clicked=True;self.report['native_frontend_press_start_interaction']=True
                menus=[w for w in ue.tobject_iterator(self.classes['frontend']) if w.call_function('GetOwningPlayer')==controller and w.call_function('IsActivated')]
                if not menus:continue
                require(len(menus)==1,'native frontend main menu duplicated');frontend=menus[0];layouts=[w for w in ue.tobject_iterator(self.classes['layout']) if w.call_function('GetOwningPlayer')==controller and w.call_function('IsInViewport')]
                require(len(layouts)==1 and layouts[0].get_property('Menu_Stack').call_function('GetActiveWidget')==frontend,'native root menu layer active widget differs');sub=startup_policy.subsystem(world);user_state=int(sub.call_function('GetLocalPlayerInitializationState',0));require(user_state==5 and ue.get_mixin_profile(frontend)==self.profile,'native frontend user initialization/Profile differs')
                self.report.update(new_world_path=path(world),native_experience_option=experience_option,native_experience_class=path(experience.get_class()),native_frontend_widget_class=path(frontend.get_class()),native_frontend_profile=ue.get_mixin_profile(frontend),native_primary_local_user_state=user_state,native_old_world_replaced=True,native_frontend_experience_object_matches=True,native_frontend_state_component_present=True,native_frontend_main_menu_active_in_menu_layer=True,native_absolute_url_drops_old_options=True);self.finish();return
    def cleanup(self):
        for proxy,name,fn in self.proxies:
            if valid(proxy):proxy.unbind_event(name,fn)
        for widget in self.widgets:
            if not valid(widget):continue
            ue.clear_mixin_profile(widget)
            if widget.is_a(ue.find_class('CommonActivatableWidget')) and widget.call_function('IsActivated'):widget.call_function('DeactivateWidget')
            widget.call_function('StopAllAnimations');widget.call_function('RemoveFromParent')
            if widget in self.roots and widget.is_rooted():widget.remove_from_root()
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        for cls in self.class_roots:cls.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before)
        self.report['owned_roots_profiles_and_input_restored']=all(not valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.roots) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items())
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<270.,'native menu travel total timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_MENU_TRAVEL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_MENU_TRAVEL_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPMenuTravelResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
