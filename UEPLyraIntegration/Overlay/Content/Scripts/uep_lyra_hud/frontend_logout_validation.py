"""Real Yes->identity Logout->local reset->startup->local initialization."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import frontend_menu_mixin as menu_policy
from . import startup_login_mixin as startup_policy
from .frontend_logout_contract import PROFILES,IDENTITY_PROXY,FALSE_FIELDS,require,validate

def path(obj):return obj.get_path_name() if obj is not None else None
def count(widget,name):return sum(menu_policy.evidence(widget)[p+'_'+name] for p in ('python','fallback'))

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.class_roots=[];self.widgets=[];self.widget_roots=[];self.proxies=[];self.proxy_roots=[];self.index=0;self.states=[];self.seen=[];self.bound=False
    def users(self):
        n=int(self.sub.call_function('GetNumLocalPlayers'));return [n]+[int(self.sub.call_function('GetLocalPlayerInitializationState',i)) for i in range(n)]
    def begin(self):
        log=self.path.with_suffix('.log').read_text(encoding='utf-8-sig',errors='replace');require('oss: tryloadsubsystemandsetdefault: loaded subsystem for type [null]' in log.casefold(),'frontend identity logout requires native NULL default online subsystem');self.report['native_default_online_subsystem_is_null']=True;self.health_before=self.healths();self.sub=startup_policy.subsystem(self.world);require(self.users()[0]==1,'identity logout fixture requires one original local player');self.report['native_mode']=str(menu_policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode)
        self.classes={'menu':ue.load_class(menu_policy.CLASS),**{k:ue.load_class(v) for k,v in startup_policy.CLASSES.items()}}
        for cls in self.classes.values():
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            ue.register_declared_mixin(cls)
        self.cdos={cls:cls.get_cdo().get_property('PythonMixinProfile') for cls in self.classes.values()};self.identity_cls=ue.find_class('LogoutCallbackProxy');self.destroy_cls=ue.find_class('DestroySessionCallbackProxy');self.confirm_cls=ue.find_class('AsyncAction_ShowConfirmation');self.push_cls=ue.find_class('AsyncAction_PushContentToLayerForPlayer');self.input=menu_policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'))
        def initialized(user,success,error,privilege,context):self.seen.append([int(user.get_property('LocalPlayerIndex')) if valid(user) else None,bool(success),int(privilege),int(context)])
        self.initialized=initialized;self.sub.bind_event('OnUserInitializeComplete',initialized);self.bound=True;self.primary_initialized=[];proxy=ue.find_class('AsyncAction_CommonUserInitialize').get_cdo().call_function('InitializeForLocalPlay',self.sub,0,ue.find_struct('InputDeviceId')(),False);self.bind(proxy,'OnInitializationComplete',lambda user,success,error,privilege,context:self.primary_initialized.append([int(user.get_property('LocalPlayerIndex')) if valid(user) else None,bool(success),int(privilege),int(context)]),True);proxy.call_function('Activate');self.enter('initial_user')
    def bind(self,proxy,name,callback,root=False):
        proxy.bind_event(name,callback);self.proxies.append((proxy,name,callback))
        if root and not proxy.is_rooted():proxy.add_to_root();self.proxy_roots.append(proxy)
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for cls in self.cdos:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.menu=menu_policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes['menu'],self.controller);self.menu.add_to_root();self.widget_roots.append(self.menu);self.widgets.append(self.menu);ue.set_mixin_profile(self.menu,self.profile);self.menu.call_function('AddToPlayerScreen',0);self.menu.call_function('ActivateWidget');self.row=dict(profile=self.profile,confirmation_results=[]);self.state={};self.frames=0;self.enter('settle')
    def confirmation(self):
        require(not any(w.call_function('IsActivated') for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen'))),'owned confirmation requires an initially empty modal layer');self.old_info_path=path(self.sub.call_function('GetUserInfoForLocalPlayerIndex',0));self.success_before=count(self.menu,'logout_success');self.push_before={path(p) for p in ue.tobject_iterator(self.push_cls)};self.confirm_before={path(p) for p in ue.tobject_iterator(self.confirm_cls)};self.identity_before={path(p) for p in ue.tobject_iterator(self.identity_cls)};self.destroy_before={path(p) for p in ue.tobject_iterator(self.destroy_cls)};self.results=[];self.menu.get_property('LogoutButton').call_function('HandleButtonClicked');new=[p for p in ue.tobject_iterator(self.confirm_cls) if path(p) not in self.confirm_before];require(len(new)==1,'owned logout must create one native confirmation');self.bind(new[0],'OnResult',lambda value:self.results.append(int(value)));self.afterpush=[];self.push_bound=False;self.enter('confirmation')
    def text(self,widget,label):
        file=self.path.parent/(self.profile+'-'+label+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(widget,str(file)),'native logout prompt export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [line.strip() for line in text.splitlines() if line.strip().startswith('Text=')]
    def bind_startup(self):
        if self.push_bound:return
        new=[p for p in ue.tobject_iterator(self.push_cls) if path(p) not in self.push_before]
        if not new:return
        require(len(new)==1,'identity logout success must create one startup push');self.bind(new[0],'AfterPush',lambda widget:self.afterpush.append(widget));self.push_bound=True
    def close_ui(self,widget):
        if widget.call_function('IsActivated'):widget.call_function('DeactivateWidget')
        menu_policy.lib('CommonUIExtensions').call_function('PopContentFromLayer',widget);widget.call_function('RemoveFromParent')
    def observe(self):
        require(time.monotonic()-self.phase_started<30.,'frontend identity logout phase timeout: '+self.phase)
        if self.phase=='initial_user':
            if not self.primary_initialized:return
            require(self.primary_initialized==[[0,True,0,0]] and self.users()==[1,5],'initialized-local-play precondition failed');self.users_before=self.users();self.report['fixture_primary_local_play_precondition_complete']=True;self.start_profile()
        elif self.phase=='settle':
            self.frames+=1
            if self.frames<4:return
            self.confirmation()
        elif self.phase=='confirmation':
            dialogs=[w for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen')) if w.call_function('IsActivated')]
            if not dialogs:return
            require(len(dialogs)==1,'expected one native logout confirmation');dialog,=dialogs;self.widgets.append(dialog);title=self.text(dialog.get_property('Text_Title'),'logout-title');body=self.text(dialog.get_property('RichText_Description'),'logout-body');require(any('NSLOCTEXT' in s for s in title) and any('NSLOCTEXT' in s for s in body),'localized logout prompt lost');self.state['prompt']=[title,body];self.row['native_localized_confirmation_preserved']=True;buttons=dialog.get_property('EntryBox_Buttons').call_function('GetAllEntries');require(len(buttons)==2,'native Yes/No buttons missing');ue.log('UEP_IDENTITY_LOGOUT_BEGIN '+self.profile);buttons[0].call_function('HandleButtonClicked');require(self.results==[0] and count(self.menu,'logout_result')>0,'native confirmed identity logout result missing');self.row.update(confirmation_results=list(self.results),native_confirmed_logout_result_delivered=True);self.bind_startup();self.enter('startup')
        elif self.phase=='startup':
            self.bind_startup()
            if not self.afterpush:return
            identity=[p for p in ue.tobject_iterator(self.identity_cls) if path(p) not in self.identity_before];destroy=[p for p in ue.tobject_iterator(self.destroy_cls) if path(p) not in self.destroy_before];require(len(identity)==1 and path(identity[0].get_class())==IDENTITY_PROXY and not destroy,'original async action must be identity LogoutCallbackProxy');require(len(self.afterpush)==1 and path(self.afterpush[0].get_class())==startup_policy.CLASSES['startup'],'native startup AfterPush differs');self.startup=self.afterpush[0]
            if not self.startup.is_rooted():self.startup.add_to_root();self.widget_roots.append(self.startup)
            self.widgets.append(self.startup);ue.set_mixin_profile(self.startup,self.profile);delta=count(self.menu,'logout_success')-self.success_before;new_info=path(self.sub.call_function('GetUserInfoForLocalPlayerIndex',0));require(delta==1 and new_info!=self.old_info_path and self.controller.get_world()==self.world and self.users()==[1,0],'identity success/local logout/reset/player-retention order differs');require(self.startup.get_property('bWaitingForPlayerInitialize') and self.startup.get_property('bWaitingForLoginInput') and self.startup.call_function('IsActivated'),'startup waiting state missing');self.row.update(native_logout_success_delta=delta,native_original_identity_logout_success_handler_executed=True,native_user_info_object_replaced_by_reset=True,native_startup_afterpush_and_waiting_state=True,native_async_logout_proxy_class=path(identity[0].get_class()),new_destroy_session_proxies=len(destroy));self.state['reset_initialization_state']=self.users();self.events_before=len(self.seen);self.startup.get_property('PressStartButton').call_function('HandleButtonClicked');self.enter('initialized')
        elif self.phase=='initialized':
            events=self.seen[self.events_before:]
            if not events:return
            require(events==[[0,True,0,0]] and not self.startup.call_function('IsActivated') and not self.startup.get_property('bWaitingForPlayerInitialize') and self.users()==self.users_before,'primary reinitialization/close differs');require(self.healths()==self.health_before and startup_policy.controller(self.world,0)==self.controller,'identity logout changed original controller or health');ue.log('UEP_IDENTITY_LOGOUT_END '+self.profile);self.row.update(native_initialize_user_indices=[0],native_primary_initialization_deactivates_startup=True);self.state['restored_initialization_state']=self.users();self.close_ui(self.startup);self.menu.call_function('DeactivateWidget');self.menu.call_function('RemoveFromParent');self.report['profiles'].append(self.row);self.states.append(self.state);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report.update(source_python_state_pairs_match=self.states[0]==self.states[1],matrices=self.states);self.finish()
    def cleanup(self):
        if self.bound:self.sub.unbind_event('OnUserInitializeComplete',self.initialized)
        for proxy,name,callback in self.proxies:
            if valid(proxy):proxy.unbind_event(name,callback)
        for widget in self.widgets:
            if not valid(widget):continue
            if widget.is_a(self.classes.get('startup',ue.find_class('CommonActivatableWidget'))):widget.call_function('SetListenForLoginInput',False)
            ue.clear_mixin_profile(widget);self.close_ui(widget);widget.call_function('StopAllAnimations')
            if widget in self.widget_roots and widget.is_rooted():widget.remove_from_root()
        for proxy in self.proxy_roots:
            if valid(proxy) and proxy.is_rooted():proxy.remove_from_root()
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        for cls in self.class_roots:cls.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before)
        self.report['owned_roots_and_profiles_restored']=all(not valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widget_roots) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['original_controller_health_and_initialized_local_user_state_preserved']=not hasattr(self,'users_before') or self.healths()==self.health_before and startup_policy.controller(self.world,0)==self.controller and self.users()==self.users_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,'native frontend identity logout timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_FRONTEND_LOGOUT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_FRONTEND_LOGOUT_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPFrontendLogoutResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
