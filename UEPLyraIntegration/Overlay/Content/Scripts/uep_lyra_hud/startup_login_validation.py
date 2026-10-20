"""Native null-backend join/leave, primary initialization, remount and lifetime."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import startup_login_mixin as policy
from .startup_login_contract import PROFILES,FALSE_FIELDS,require,validate

def count(w,k,m):return sum(policy.evidence(w)[p+'_'+k+'_'+m] for p in ('python','fallback'))
def path(o):return o.get_path_name() if o is not None else None

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],native_retained_secondary_pawns_cleaned_by_fixture=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.widgets=[];self.holders=[];self.owned_pawns=[];self.index=0;self.states=[];self.seen=[];self.bound=False;self.owned_secondary=False
    def begin(self):
        log=self.path.with_suffix('.log').read_text(encoding='utf-8-sig',errors='replace');require('oss: tryloadsubsystemandsetdefault: loaded subsystem for type [null]' in log.casefold(),'local user fixture requires actual native NULL default online subsystem');self.report['native_default_online_subsystem_is_null']=True
        # A headless second local player has no physical device event to create
        # its Slate user. The existing SDK routes this inert character to a new
        # user's empty focus path, making native user1 focus routing available.
        ue.FSlateApplication.process_key_char_event(ue.FCharacterEvent(' ',False,ue.FModifierKeysState(),1));self.report['fixture_inert_character_event_created_secondary_slate_user']=True;self.report['fixture_slate_user_lifetime']='owned standalone process until normal shutdown'
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.report['original_pawn_health_before']=self.health_before;self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()};self.number_before=int(self.classes['login'].get_cdo().get_property('PlayerNumber'))
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.sub=policy.subsystem(self.world);require(int(self.sub.call_function('GetNumLocalPlayers'))==1 and not valid(policy.controller(self.world,1)),'owned secondary player slot must be initially empty');self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'))
        def initialized(user,success,error,privilege,context):
            index=int(user.get_property('LocalPlayerIndex')) if valid(user) else None;self.seen.append(dict(index=index,success=bool(success),privilege=int(privilege),context=int(context)))
            if index==1 and success and hasattr(self,'holder'):self.holder.call_function('SetOwningPlayer',policy.controller(self.world,1))
        self.initialized=initialized;self.sub.bind_event('OnUserInitializeComplete',initialized);self.bound=True;self.start_profile()
    def create(self,k,mount=True):
        cls=self.classes[k];cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        if k=='login':cls.get_cdo().set_property('PlayerNumber',1)
        widget=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,cls,self.controller);widget.add_to_root();self.widgets.append(widget);ue.set_mixin_profile(widget,self.profile)
        if mount:widget.call_function('AddToPlayerScreen',0)
        return widget
    def mount_login(self):
        root=self.holder.get_property('WidgetTree').get_property('RootWidget')
        root.call_function('SetContent' if root.is_a(ue.find_class('ContentWidget')) else 'AddChild',self.login)
    def start_profile(self):
        self.profile=PROFILES[self.index];self.startup=self.create('startup');self.startup.call_function('ActivateWidget');self.login=self.create('login',False);holder_class=ue.load_class('/Game/UI/Menu/Experiences/W_NonInteractiveSpinner.W_NonInteractiveSpinner_C');self.holder=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,holder_class,self.controller);self.holder.add_to_root();self.holders.append(self.holder);self.mount_login();self.holder.call_function('AddToPlayerScreen',0);self.holder.call_function('ActivateWidget');self.row=dict(profile=self.profile,controller_indices=[],logged_in_results=[],natural_initialize_user_indices=[]);self.state=dict(controllers=[],texts=[]);self.frames=0;self.enter('settle')
    def text(self,label):
        file=self.path.parent/(self.profile+'-'+label+'-button.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(self.login.get_property('LoginButton'),str(file)),'native login button export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');rows=[line.strip() for line in text.splitlines() if line.strip().startswith('ButtonText=')];require(len(rows)==1 and 'NSLOCTEXT' in rows[0],'native localized login label lost');return rows[0]
    def callbacks(self):return [count(self.startup,'startup','initialized'),count(self.login,'login','initialized')]
    def begin_primary(self,phase):
        self.event_before=len(self.seen);self.callback_before=self.callbacks();self.startup.get_property('PressStartButton').call_function('HandleButtonClicked');self.enter(phase)
    def observed_primary(self):
        events=self.seen[self.event_before:]
        if not events:return False
        require(len(events)==1 and events[0]['index']==0 and events[0]['success'] and events[0]['privilege']==0,'native primary local-play completion differs');self.row['natural_initialize_user_indices'].append(0);return True
    def observe(self):
        require(time.monotonic()-self.phase_started<30.,'startup/login phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<4:return
            require(policy.one(self.startup.call_function('BP_GetDesiredFocusTarget'))==self.startup.get_property('PressStartButton') and self.startup.get_property('bWaitingForPlayerInitialize') and self.startup.get_property('bWaitingForLoginInput') and self.login.get_property('WaitingForLoginInput'),'native Construct/focus/waiting state differs');self.row['native_construct_focus_and_waiting_flags']=True
            for index in (-1,0,1,7):
                self.login.set_property('PlayerNumber',index);self.login.call_function('RefreshLoginState');logged=bool(policy.one(self.login.call_function('IsPlayerLoggedIn')));expected=index==0;require(logged==expected and self.login.get_property('WaitingForLoginInput')==(not expected) and self.login.get_property('LoginButton').call_function('GetOwningPlayer')==self.controller,'native controller-validity/owner/listen state differs');text=self.text('index'+str(index));self.row['controller_indices'].append(index);self.row['logged_in_results'].append(logged);self.state['controllers'].append([index,logged,not expected,text])
            self.login.set_property('PlayerNumber',1);self.login.call_function('RefreshLoginState');self.event_before=len(self.seen);self.login.get_property('LoginButton').call_function('HandleButtonClicked');self.owned_secondary=True;self.enter('join')
        elif self.phase=='join':
            events=self.seen[self.event_before:]
            if not events or not valid(policy.controller(self.world,1)):return
            self.guest_pawn=policy.controller(self.world,1).get_controlled_pawn()
            if not valid(self.guest_pawn):return
            require(path(self.guest_pawn) not in self.health_before,'secondary fixture must not own an original pawn');self.owned_pawns.append(self.guest_pawn)
            require(len(events)==1 and events[0]['index']==1 and events[0]['success'] and events[0]['privilege']==0 and int(self.sub.call_function('GetNumLocalPlayers'))==2,'native secondary local-play initialization failed');require(count(self.login,'login','click')>0 and count(self.login,'login','initialized')>0 and not self.login.get_property('WaitingForLoginInput') and self.login.get_property('LoginButton').call_function('GetOwningPlayer')==policy.controller(self.world,1),'native secondary join refresh differs');self.row['natural_initialize_user_indices'].append(1);self.row['native_secondary_button_creates_local_player']=True
            require(not self.startup.get_property('bWaitingForPlayerInitialize') and not self.startup.call_function('IsActivated'),'original startup success callback must retain its lack of user-index filtering');self.row['native_secondary_completion_closes_waiting_startup_without_index_filter']=True;self.state['texts'].append(self.text('joined'));self.holder.call_function('SetOwningPlayer',self.controller);self.login.get_property('LoginButton').call_function('HandleButtonClicked');self.frames=0;self.enter('leave')
        elif self.phase=='leave':
            self.frames+=1
            if self.frames<4 or valid(policy.controller(self.world,1)):return
            require(int(self.sub.call_function('GetNumLocalPlayers'))==1 and policy.controller(self.world,0)==self.controller and self.login.get_property('WaitingForLoginInput'),'native secondary logout must destroy only owned player1');self.owned_secondary=False;self.row['native_secondary_button_destroys_only_secondary_player']=True
            if valid(self.guest_pawn):self.report['native_retained_secondary_pawns_cleaned_by_fixture'].append(path(self.guest_pawn));self.guest_pawn.actor_destroy()
            self.state['texts'].append(self.text('left'));self.row['native_localized_join_leave_text_preserved']=True
            self.startup.call_function('SwitchToPressStart');self.startup.call_function('ActivateWidget');self.startup.call_function('RemoveFromParent');self.login.call_function('RemoveFromParent');self.begin_primary('removed')
        elif self.phase=='removed':
            if not self.observed_primary():return
            deltas=[now-old for now,old in zip(self.callbacks(),self.callback_before)];require(deltas==[1,1] and not self.startup.call_function('IsInViewport') and self.login.call_function('GetParent') is None and not self.startup.get_property('bWaitingForPlayerInitialize') and self.login.get_property('WaitingForLoginInput'),'original rooted/removed callback lifetime differs');self.row.update(removed_callback_deltas=deltas,native_removed_rooted_widgets_keep_original_initialization_callbacks=True);self.startup.call_function('AddToPlayerScreen',0);self.mount_login();self.frames=0;self.enter('remount')
        elif self.phase=='remount':
            self.frames+=1
            if self.frames<4:return
            require(self.login.call_function('GetParent') is not None,'native login widget remount missing its actual parent')
            self.begin_primary('remounted_callback')
        elif self.phase=='remounted_callback':
            if not self.observed_primary():return
            deltas=[now-old for now,old in zip(self.callbacks(),self.callback_before)];require(deltas==[1,1],'remount duplicated original native initialization binding');self.row.update(remounted_callback_deltas=deltas,native_remount_does_not_duplicate_binding=True);self.startup.call_function('RemoveFromParent');self.login.call_function('RemoveFromParent');self.report['profiles'].append(self.row);self.states.append(self.state);self.report['matrices']=self.states;self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report['source_python_state_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        if self.bound:self.sub.unbind_event('OnUserInitializeComplete',self.initialized)
        if self.owned_secondary and valid(policy.controller(self.world,1)):self.sub.call_function('TryToLogOutUser',1,True)
        for pawn in self.owned_pawns:
            if valid(pawn):pawn.actor_destroy()
        for widget in self.widgets:
            widget.call_function('SetListenForLoginInput',False);ue.clear_mixin_profile(widget)
            if widget.is_a(ue.find_class('CommonActivatableWidget')) and widget.call_function('IsActivated'):widget.call_function('DeactivateWidget')
            widget.call_function('StopAllAnimations');widget.call_function('RemoveFromParent');widget.remove_from_root()
        for holder in self.holders:
            if holder.call_function('IsActivated'):holder.call_function('DeactivateWidget')
            holder.call_function('RemoveFromParent');holder.remove_from_root()
        self.report['owned_login_activatable_holders_restored']=all(not holder.is_rooted() and not holder.call_function('IsInViewport') for holder in self.holders)
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        if 'login' in self.classes:self.classes['login'].get_cdo().set_property('PlayerNumber',self.number_before)
        for cls in getattr(self,'class_roots',[]):cls.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before)
        self.report['original_pawn_health_after']=self.healths() if hasattr(self,'health_before') else {};self.report['fixture_secondary_pawns_removed']=all(not valid(pawn) or pawn.call_function('IsActorBeingDestroyed') for pawn in self.owned_pawns)
        self.report['owned_roots_profiles_cdo_player_number_and_input_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items()) and (not self.classes or int(self.classes['login'].get_cdo().get_property('PlayerNumber'))==self.number_before);self.report['original_primary_controller_and_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before and policy.controller(self.world,0)==self.controller;self.report['fixture_secondary_player_removed']=not hasattr(self,'sub') or not valid(policy.controller(self.world,1))
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,'native startup/login timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_STARTUP_LOGIN_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_STARTUP_LOGIN_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPStartupLoginResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
