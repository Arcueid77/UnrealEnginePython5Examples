"""Native selection activation, original host/browse routes and NULL quickplay."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import experience_screen_mixin as policy
from . import experience_list_mixin as list_policy
from . import experience_entry_mixin as entry_policy
from .experience_screen_contract import PROFILES,FALSE_FIELDS,require,validate

def arg(name,default):return next((v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'=')),default)
def path(obj):return obj.get_path_name() if obj is not None else None
def count(widget,name):return sum(policy.evidence(widget)[p+'_'+name] for p in ('python','fallback'))
def asset_id(value):return [str(value.PrimaryAssetType.Name),str(value.PrimaryAssetName)]

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.mode=arg('UEPExperienceScreenMode','life');self.only_profile=arg('UEPExperienceScreenProfile','Python');self.report=dict(status='running',error=None,mode=self.mode,profiles=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.class_roots=[];self.widgets=[];self.roots=[];self.bindings=[];self.proxy_roots=[];self.index=0;self.states=[]
    def log(self):return self.path.with_suffix('.log').read_text(encoding='utf-8-sig',errors='replace')
    def bind(self,obj,name,fn,root=False):
        obj.bind_event(name,fn);self.bindings.append((obj,name,fn))
        if root and not obj.is_rooted():obj.add_to_root();self.proxy_roots.append(obj)
    def begin(self):
        require('oss: tryloadsubsystemandsetdefault: loaded subsystem for type [null]' in self.log().casefold(),'selection fixture needs native NULL backend');self.health_before=self.healths();self.report['initial_native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.classes={k:ue.load_class(v) for k,v in dict(screen=policy.CLASS,list=list_policy.CLASS,tile=entry_policy.CLASS).items()}
        for cls in self.classes.values():
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            ue.register_declared_mixin(cls)
        self.cdos={cls:cls.get_cdo().get_property('PythonMixinProfile') for cls in self.classes.values()};self.push_cls=ue.find_class('AsyncAction_PushContentToLayerForPlayer');self.init_cls=ue.find_class('AsyncAction_CommonUserInitialize');self.sub=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('CommonSessionSubsystem'));self.loading=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('LyraLoadingScreenSubsystem'));self.loading_before=self.loading.call_function('GetLoadingScreenContentWidget');self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'));self.start_profile()
    def start_profile(self):
        self.profile=self.only_profile if self.mode=='quick' else PROFILES[self.index]
        for cls in self.cdos:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes['screen'],self.controller);self.w.add_to_root();self.roots.append(self.w);self.widgets.append(self.w);ue.set_mixin_profile(self.w,self.profile);self.list=self.w.get_property('W_ExperienceList');self.loaded=0
        def loaded():self.loaded+=1
        self.bind(self.list,'OnExperiencesLoaded',loaded);self.w.call_function('AddToPlayerScreen',0);self.w.call_function('ActivateWidget');self.row=dict(profile=self.profile);self.state={};self.frames=0;self.enter('settle')
    def request(self,value):return dict(map=asset_id(value.get_property('MapID')),mode=int(value.get_property('OnlineMode')),args=dict(value.get_property('ExtraArgs')),players=int(value.get_property('MaxPlayerCount')),advertisement=str(value.get_property('ModeNameForAdvertisement')))
    def active_menu(self):
        roots=[r for r in ue.tobject_iterator(ue.find_class('PrimaryGameLayout')) if r.call_function('GetOwningPlayer')==self.controller and r.call_function('IsInViewport')];require(len(roots)==1,'actual primary root layout missing/duplicated');return roots[0].get_property('Menu_Stack').call_function('GetActiveWidget')
    def push(self,button,phase):
        self.afterpush=[];self.push_expected_class='/Game/UI/Menu/Experiences/'+('W_HostSessionScreen.W_HostSessionScreen_C' if button=='HostButton' else 'W_SessionBrowserScreen.W_SessionBrowserScreen_C');self.old_active=self.active_menu();self.push_before={path(p) for p in ue.tobject_iterator(self.push_cls)};self.w.get_property(button).call_function('HandleButtonClicked');self.push_bound=False;self.bind_push();self.enter(phase)
    def bind_push(self):
        if not self.push_bound:
            new=[p for p in ue.tobject_iterator(self.push_cls) if path(p) not in self.push_before]
            if not new:return
            require(len(new)==1,'selection route creates duplicate native push');self.bind(new[0],'AfterPush',lambda widget:self.afterpush.append(widget) if widget not in self.afterpush else None);self.push_bound=True
        # A cached native class can finish before this observer attaches. Read
        # the real root's active stack widget;never replay AfterPush or a login.
        if not self.afterpush:
            active=self.active_menu()
            if valid(active) and active!=self.old_active and path(active.get_class())==self.push_expected_class and active.call_function('IsActivated'):self.afterpush.append(active)
    def close(self,widget):
        if widget.call_function('IsActivated'):widget.call_function('DeactivateWidget')
        policy.lib('CommonUIExtensions').call_function('PopContentFromLayer',widget);widget.call_function('RemoveFromParent')
    def observe(self):
        require(time.monotonic()-self.phase_started<(110. if self.phase=='arrival' else 40.),'experience screen phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if not self.loaded or self.frames<4:return
            require(float(self.w.call_function('GetAnimationCurrentTime',self.w.get_property('OnActivated')))>.005 and self.w.call_function('BP_GetDesiredFocusTarget')==self.w.get_property('QuickplayButton') and count(self.w,'activate')>0,'native selection activation/focus differs');self.row['native_activation_animation_and_const_focus']=True;spinner=self.w.get_property('ProgressSpinner');states=[]
            for show in (True,False,True,False):self.w.call_function('ShowProgressSpinner',show);states.append(int(spinner.call_function('GetVisibility')))
            require(states==[0,2,0,2],'native spinner must use Hidden,not Collapsed');self.row['native_visible_hidden_spinner_states']=True;self.state['spinner']=states;self.list.call_function('SelectFirstExperience');self.exp=self.w.get_property('SelectedExperience');require(valid(self.exp) and count(self.w,'selected')>0,'real list dispatcher did not assign selection');self.row['native_list_selection_assigns_exact_definition']=True
            if self.mode=='quick':
                self.request_before={path(p) for p in ue.tobject_iterator(ue.find_class('CommonSession_HostSessionRequest'))};self.loading_seen=[];self.bind(self.loading,'OnLoadingScreenWidgetChanged',lambda cls:self.loading_seen.append(cls));self.w.get_property('QuickplayButton').call_function('HandleButtonClicked');self.enter('quick_request')
            else:
                actual=self.w.call_function(policy.NATIVE['request'],self.exp);expected=self.exp.call_function('CreateHostingRequest',self.w);expected.set_property('OnlineMode',2);a=self.request(actual);b=self.request(expected);require(a==b and a['mode']==2,'native online request payload differs');self.state['request']=a;self.row['native_online_request_payload_matches_definition']=True;self.push('HostButton','host')
        elif self.phase=='host':
            self.bind_push()
            if not self.afterpush:return
            require(len(self.afterpush)==1 and path(self.afterpush[0].get_class())=='/Game/UI/Menu/Experiences/W_HostSessionScreen.W_HostSessionScreen_C','native host AfterPush differs');self.widgets.append(self.afterpush[0]);self.row['native_host_afterpush']=True;self.close(self.afterpush[0]);self.frames=0;self.enter('host_closed')
        elif self.phase=='host_closed':
            self.frames+=1
            if self.frames<5:return
            self.search_before=self.log().count('LogCommonSession: OnFindSessionsComplete(bWasSuccessful:');self.browse_before=count(self.w,'browse_result');self.push('BrowseButton','browse')
        elif self.phase=='browse':
            self.bind_push()
            if not self.afterpush:return
            require(len(self.afterpush)==1 and path(self.afterpush[0].get_class())=='/Game/UI/Menu/Experiences/W_SessionBrowserScreen.W_SessionBrowserScreen_C' and count(self.w,'browse_result')==self.browse_before+1,'native online initialization/browser continuation differs');self.browser=self.afterpush[0];self.widgets.append(self.browser);self.row['native_browse_online_callback_then_browser_afterpush']=True;self.enter('browser_search')
        elif self.phase=='browser_search':
            if self.log().count('LogCommonSession: OnFindSessionsComplete(bWasSuccessful:')<=self.search_before:return
            require(valid(self.browser.get_property('SearchRequest')),'native browser search request missing');self.row['native_browser_search_completes']=True;self.close(self.browser);self.close(self.w);self.report['profiles'].append(self.row);self.states.append(self.state);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report.update(source_python_state_pairs_match=self.states[0]==self.states[1],matrices=self.states);self.finish()
        elif self.phase=='quick_request':
            if count(self.w,'prepared')<1:return
            requests=[r for r in ue.tobject_iterator(ue.find_class('CommonSession_HostSessionRequest')) if path(r) not in self.request_before];require(len(requests)==1 and count(self.w,'quick_result')==1 and count(self.w,'prepared')==1,'native quickplay callback/request count differs');self.host_request=requests[0];self.payload=self.request(self.host_request);self.exp=self.w.get_property('SelectedExperience');require(valid(self.exp) and self.payload['mode']==2 and self.payload['args'].get('Experience')==str(self.exp.get_property('ExperienceID').PrimaryAssetName) and self.loading_seen and int(self.w.get_property('ProgressSpinner').call_function('GetVisibility'))==0,'native preparation/request/submit/spinner ordering differs');require(self.healths()==self.health_before,'quickplay request changed original gameplay health');self.report.update(profile=self.profile,online_request_mode=2,quickplay_handler_calls=count(self.w,'quick_result'),prepared_handler_calls=count(self.w,'prepared'),native_online_initialize_success=True,native_async_preparation_then_online_request=True,online_request_payload=self.payload);self.enter('arrival')
        elif self.phase=='arrival':
            for world in ue.all_worlds():
                if world.get_world_type() not in (1,3):continue
                controller=policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)
                if not valid(controller) or controller is self.controller:continue
                bridge=policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
                if not valid(bridge):continue
                snap=bridge.call_function('CaptureSnapshot')
                if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
                level=policy.lib('GameplayStatics').call_function('GetCurrentLevelName',world,True);mode=policy.lib('GameplayStatics').call_function('GetGameMode',world);options=mode.get_property('OptionsString');experience=policy.lib('GameplayStatics').call_function('ParseOption',options,'Experience');require(level==self.payload['map'][1].rsplit('/',1)[-1] and experience==self.payload['args']['Experience'],'native quickplay destination differs');log=self.log();require('QuickPlay Search Finished' in log and '(Results 0)' in log and 'OnCreateSessionComplete(SessionName: GameSession, bWasSuccessful: 1)' in log,'NULL quickplay did not take actual empty-search host path');self.report.update(native_quickplay_search_empty_then_host=True,native_destination_map_experience_and_player_ready=True,native_destination_level=level,native_destination_experience=experience,native_destination_mode=str(snap.NetMode));self.new_world=world;self.new_controller=controller;self.destroyed=[];proxy=ue.find_class('DestroySessionCallbackProxy').get_cdo().call_function('DestroySession',world,controller);self.bind(proxy,'OnSuccess',lambda:self.destroyed.append(True),True);self.bind(proxy,'OnFailure',lambda:self.destroyed.append(False));proxy.call_function('Activate');self.enter('destroy');return
        elif self.phase=='destroy':
            if not self.destroyed:return
            require(self.destroyed==[True],'fixture-owned quickplay session failed native destruction');self.report['owned_native_session_destroyed']=True;self.finish()
    def cleanup(self):
        for obj,name,fn in self.bindings:
            if valid(obj):obj.unbind_event(name,fn)
        for widget in self.widgets:
            if not valid(widget):continue
            if widget in self.roots:ue.clear_mixin_profile(widget)
            self.close(widget);widget.call_function('StopAllAnimations')
            if widget in self.roots and widget.is_rooted():widget.remove_from_root()
        for obj in self.proxy_roots:
            if valid(obj) and obj.is_rooted():obj.remove_from_root()
        if hasattr(self,'loading'):self.loading.call_function('SetLoadingScreenContentWidget',self.loading_before)
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        for cls in self.class_roots:cls.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before)
        self.report['owned_roots_profiles_input_and_loading_class_restored']=all(not valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.roots) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items()) and (not hasattr(self,'loading') or self.loading.call_function('GetLoadingScreenContentWidget')==self.loading_before);self.report['original_gameplay_health_unchanged']=self.mode=='quick' or not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<280.,'native experience screen timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPERIENCE_SCREEN_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPERIENCE_SCREEN_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExperienceScreenResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
