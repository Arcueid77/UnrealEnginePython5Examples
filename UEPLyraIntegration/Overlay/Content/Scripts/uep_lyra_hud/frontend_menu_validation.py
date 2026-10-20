"""Actual native frontend button->async UI/prompt result chains, no replay."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import frontend_menu_mixin as policy
from .frontend_menu_contract import PROFILES,ROUTES,FALSE_FIELDS,require,validate

def arg(k,default):return next((v.split('=',1)[1] for v in sys.argv if v.startswith('-'+k+'=')),default)
def path(o):return o.get_path_name() if o is not None else None
def count(w,m):return sum(policy.evidence(w)[p+'_'+m] for p in ('python','fallback'))
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.mode=arg('UEPFrontendMenuMode','life');self.only_profile=arg('UEPFrontendMenuProfile','Python');self.report=dict(status='running',error=None,mode=self.mode,profiles=[],native_request_exit_fallback_used=False);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.proxies=[];self.owned_ui=[];self.index=0;self.matrices=[];self.cdo_before=None;self.class_owned_root=False
    def users(self):
        n=int(self.user_subsystem.call_function('GetNumLocalPlayers'));return [n]+[int(self.user_subsystem.call_function('GetLocalPlayerInitializationState',i)) for i in range(n)]
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.user_subsystem=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('CommonUserSubsystem'));self.users_before=self.users();self.cls=ue.load_class(policy.CLASS);self.class_owned_root=not self.cls.is_rooted()
        if self.class_owned_root:self.cls.add_to_root()
        ue.register_declared_mixin(self.cls);self.cdo_before=self.cls.get_cdo().get_property('PythonMixinProfile');self.push_cls=ue.find_class('AsyncAction_PushContentToLayerForPlayer');self.confirm_cls=ue.find_class('AsyncAction_ShowConfirmation');self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'));self.start_profile()
    def start_profile(self):
        self.profile=self.only_profile if self.mode=='quit' else PROFILES[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.menu=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);self.menu.add_to_root();self.widgets.append(self.menu);ue.set_mixin_profile(self.menu,self.profile);self.menu.call_function('AddToPlayerScreen',0);self.menu.call_function('ActivateWidget');self.row=dict(profile=self.profile,native_afterpush_routes=[],native_declined_confirmation_results=[]);self.matrix=dict(routes=[],prompts=[]);self.route_index=0;self.prompt_index=0;self.frames=0;self.enter('settle')
    def push(self):
        name,button,cls=ROUTES[self.route_index];baseline={path(p) for p in ue.tobject_iterator(self.push_cls)};self.afterpush=[];self.menu.get_property(button).call_function('HandleButtonClicked');created=[p for p in ue.tobject_iterator(self.push_cls) if path(p) not in baseline];require(len(created)==1,'frontend click must create exactly one native push proxy');proxy,=created
        def done(widget):self.afterpush.append(widget)
        proxy.bind_event('AfterPush',done);self.proxies.append((proxy,'AfterPush',done));self.enter('push')
    def confirmation(self):
        self.prompt='quit' if self.mode=='quit' or self.prompt_index==0 else 'logout';button='QuitGameButton' if self.prompt=='quit' else 'LogoutButton';baseline={path(p) for p in ue.tobject_iterator(self.confirm_cls)};self.results=[];self.menu.get_property(button).call_function('HandleButtonClicked');created=[p for p in ue.tobject_iterator(self.confirm_cls) if path(p) not in baseline];require(len(created)==1,'frontend native confirmation proxy count differs');proxy,=created
        def result(value):self.results.append(int(value))
        proxy.bind_event('OnResult',result);self.proxies.append((proxy,'OnResult',result));self.enter('confirmation')
    def text_history(self,widget,name):
        file=self.path.parent/(self.profile+'-'+self.prompt+'-'+name+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(widget,str(file)),'native frontend prompt export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [line.strip() for line in text.splitlines() if line.strip().startswith('Text=')]
    def close_owned(self,widget):
        if path(widget.get_class())=='/Game/UI/Credits/W_Credits.W_Credits_C':widget.call_function('ToggleScrollTimer',False)
        if widget.call_function('IsActivated'):widget.call_function('DeactivateWidget')
        policy.lib('CommonUIExtensions').call_function('PopContentFromLayer',widget)
    def observe(self):
        require(time.monotonic()-self.phase_started<30.,'frontend phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<3 or float(self.menu.call_function('GetAnimationCurrentTime',self.menu.get_property('OnActivated')))<.005:return
            require(count(self.menu,'activate')>0 and one(self.menu.call_function('BP_GetDesiredFocusTarget'))==self.menu.get_property('StartGameButton'),'frontend actual activation/const focus differs');self.row['actual_activation_animation_and_focus_target']=True
            if self.mode=='quit':self.confirmation()
            else:self.push()
        elif self.phase=='push':
            if not self.afterpush:return
            name,button,cls=ROUTES[self.route_index];require(len(self.afterpush)==1 and path(self.afterpush[0].get_class())==cls and count(self.menu,name)>0,'frontend native AfterPush route differs');widget,=self.afterpush;self.owned_ui.append(widget);self.row['native_afterpush_routes'].append([name,cls]);self.matrix['routes'].append([name,cls]);self.close_owned(widget);self.frames=0;self.enter('closed')
        elif self.phase=='closed':
            self.frames+=1
            if self.frames<5:return
            self.route_index+=1
            if self.route_index<len(ROUTES):self.push()
            else:self.confirmation()
        elif self.phase=='confirmation':
            dialogs=[w for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen')) if w.call_function('IsActivated')]
            if not dialogs:return
            require(len(dialogs)==1,'frontend expected one active actual confirmation');dialog,=dialogs;self.owned_ui.append(dialog);title=self.text_history(dialog.get_property('Text_Title'),'title');body=self.text_history(dialog.get_property('RichText_Description'),'body');require(any('NSLOCTEXT' in v for v in title) and any('NSLOCTEXT' in v for v in body),'frontend original localized prompt lost');self.row['original_prompt_localization_preserved']=True;self.matrix['prompts'].append([self.prompt,title,body]);buttons=dialog.get_property('EntryBox_Buttons').call_function('GetAllEntries');require(len(buttons)==2,'frontend native Yes/No buttons missing');buttons[0 if self.mode=='quit' else 1].call_function('HandleButtonClicked')
            if self.mode=='quit':
                require(self.results==[0] and count(self.menu,'quit_result')>0,'frontend native confirmed result missing');self.report.update(profile=self.profile,native_confirmed_quit_result=list(self.results),native_quit_requested_from_original_confirmation=True);self.finish(request_exit=False)
            else:self.frames=0;self.enter('declined')
        elif self.phase=='declined':
            self.frames+=1
            if self.frames<4:return
            require(self.results==[1] and count(self.menu,self.prompt+'_result')>0 and self.controller.get_world()==self.world and self.users()==self.users_before,'frontend declined result modified world/user state');self.row['declines_leave_original_controller_world']=True;self.row['native_declined_confirmation_results'].append([self.prompt,1]);self.prompt_index+=1
            if self.prompt_index<2:self.confirmation();return
            self.menu.call_function('DeactivateWidget');self.menu.call_function('RemoveFromParent');self.report['profiles'].append(self.row);self.matrices.append(self.matrix);self.report['matrices']=self.matrices;self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report['source_python_state_pairs_match']=self.matrices[0]==self.matrices[1];self.finish()
    def cleanup(self):
        for proxy,name,fn in self.proxies:
            if valid(proxy):proxy.unbind_event(name,fn)
        for widget in self.owned_ui:
            if valid(widget):self.close_owned(widget)
        for widget in self.widgets:
            ue.clear_mixin_profile(widget)
            if widget.call_function('IsActivated'):widget.call_function('DeactivateWidget')
            widget.call_function('StopAllAnimations');widget.call_function('RemoveFromParent');widget.remove_from_root()
        if self.cdo_before is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.cdo_before)
        if self.class_owned_root:self.cls.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before)
        self.report['owned_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and (self.cdo_before is None or self.cls.get_cdo().get_property('PythonMixinProfile')==self.cdo_before);self.report['original_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before;self.report['native_user_initialization_state_unchanged']=not hasattr(self,'users_before') or self.users()==self.users_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,'native frontend timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None,request_exit=True):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_FRONTEND_MENU_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        if request_exit:self.report['native_request_exit_fallback_used']=self.mode=='quit';self.write();ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_FRONTEND_MENU_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPFrontendMenuResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
