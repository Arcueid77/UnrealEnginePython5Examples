"""Native host label/choice/payload matrix and real NULL online hosting travel."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .experience_screen_validation import Validation as Shared,arg,path
from . import host_session_mixin as policy
from . import experience_list_mixin as list_policy
from . import experience_entry_mixin as entry_policy
from .host_session_contract import PROFILES,FALSE_FIELDS,require,validate

def count(w,name):return sum(policy.evidence(w)[p+'_'+name] for p in ('python','fallback'))

class Validation(Shared):
    def __init__(self,result):
        super().__init__(result);self.mode=arg('UEPHostSessionMode','life');self.only_profile=arg('UEPHostSessionProfile','Python');self.report=dict(status='running',error=None,mode=self.mode,profiles=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False))
    def begin(self):
        require('oss: tryloadsubsystemandsetdefault: loaded subsystem for type [null]' in self.log().casefold(),'host fixture requires actual native NULL backend');self.health_before=self.healths();self.report['initial_native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.classes={k:ue.load_class(v) for k,v in dict(host=policy.CLASS,list=list_policy.CLASS,tile=entry_policy.CLASS).items()}
        for cls in self.classes.values():
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            ue.register_declared_mixin(cls)
        self.cdos={cls:cls.get_cdo().get_property('PythonMixinProfile') for cls in self.classes.values()};self.loading=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('LyraLoadingScreenSubsystem'));self.loading_before=self.loading.call_function('GetLoadingScreenContentWidget');self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'));self.start_profile()
    def start_profile(self):
        self.profile=self.only_profile if self.mode=='host' else PROFILES[self.index]
        for cls in self.cdos:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes['host'],self.controller);self.w.add_to_root();self.roots.append(self.w);self.widgets.append(self.w);ue.set_mixin_profile(self.w,self.profile);self.list=self.w.get_property('ExperienceList');self.loaded=0
        def loaded():self.loaded+=1
        self.bind(self.list,'OnExperiencesLoaded',loaded);self.w.call_function('AddToPlayerScreen',0);self.w.call_function('ActivateWidget');self.frames=0;self.row=dict(profile=self.profile);self.state={};self.enter('settle')
    def text(self,name,label):
        file=self.path.parent/(self.profile+'-'+label+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(self.w.get_property(name),str(file)),'host native label export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');values=[line.strip().split('=',1)[1] for line in text.splitlines() if line.strip().startswith('Text=')];require(len(values)==1 and 'NSLOCTEXT' in values[0],'host localized native label/history missing');return values[0]
    def observe(self):
        require(time.monotonic()-self.phase_started<(110. if self.phase=='host_arrival' else 35.),'host-session phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if not self.loaded or self.frames<4:return
            require(self.w.call_function('BP_GetDesiredFocusTarget')==self.w.get_property('BotsToggleButton') and count(self.w,'activate')>0 and float(self.w.call_function('GetAnimationCurrentTime',self.w.get_property('OnActivated')))>.005,'native host activation/focus differs');self.row['native_activation_const_focus_and_labels']=True;self.exp=self.list.get_property('UserFacingExperienceList')[0]
            if self.mode=='host':
                if self.w.get_property('BotsEnabled'):self.w.get_property('BotsToggleButton').call_function('HandleButtonClicked')
                require(not self.w.get_property('BotsEnabled') and int(self.w.get_property('Online Mode'))==2,'owned native online/bots-off host precondition differs');self.request_before={path(r) for r in ue.tobject_iterator(ue.find_class('CommonSession_HostSessionRequest'))};self.loading_seen=[];self.bind(self.loading,'OnLoadingScreenWidgetChanged',lambda cls:self.loading_seen.append(cls));self.list.get_property('ExperienceWidgets')[0].get_property('ExperienceTileButton').call_function('HandleButtonClicked');self.enter('host_request')
            else:
                self.state['labels_initial']=[self.text('SessionTypeText','initial-mode'),self.text('BotsToggleText','initial-bots')];modes=[];mode_labels=[]
                for i in range(3):self.w.get_property('SessionTypeButton').call_function('HandleButtonClicked');modes.append(int(self.w.get_property('Online Mode')));mode_labels.append(self.text('SessionTypeText','mode'+str(i)))
                require(modes==[1,0,2],'native source mode cycle differs');self.row.update(native_mode_button_cycle_online_lan_offline=True,mode_cycle=modes);self.state['mode_labels']=mode_labels;bot_labels=[]
                for i,value in enumerate((False,True)):self.w.get_property('BotsToggleButton').call_function('HandleButtonClicked');require(bool(self.w.get_property('BotsEnabled'))==value,'native bot button toggle differs');bot_labels.append(self.text('BotsToggleText','bots'+str(i)))
                self.row['native_bots_button_and_localized_labels']=True;self.state['bot_labels']=bot_labels;self.w.set_property('SelectedExperience',None);require(policy.one(self.w.call_function('CreateHostingRequest')) is None,'source null selection must return null request');self.row['native_null_request_returns_none']=True;payloads=[];self.w.set_property('SelectedExperience',self.exp)
                for mode in (0,1,2):
                    for bots in (False,True):
                        self.w.set_property('Online Mode',mode);self.w.set_property('BotsEnabled',bots);actual=policy.one(self.w.call_function('CreateHostingRequest'));baseline=self.exp.call_function('CreateHostingRequest',self.w);baseline.set_property('OnlineMode',mode)
                        if not bots:args=dict(baseline.get_property('ExtraArgs'));args['NumBots']='0';baseline.set_property('ExtraArgs',args)
                        require(self.request(actual)==self.request(baseline),'native host mode/bot request payload differs');payloads.append(self.request(actual))
                self.state['payloads']=payloads;self.row.update(native_six_mode_bot_request_payloads=True,request_cases=len(payloads));self.close(self.w);self.report['profiles'].append(self.row);self.states.append(self.state);self.index+=1
                if self.index<len(PROFILES):self.start_profile()
                else:self.report.update(source_python_state_pairs_match=self.states[0]==self.states[1],matrices=self.states);self.finish()
        elif self.phase=='host_request':
            if count(self.w,'prepared')<1:return
            requests=[r for r in ue.tobject_iterator(ue.find_class('CommonSession_HostSessionRequest')) if path(r) not in self.request_before];require(len(requests)==1,'native host request count differs');self.host_request=requests[0];self.payload=self.request(self.host_request);require(self.payload['mode']==2 and self.payload['args'].get('NumBots')=='0' and count(self.w,'online_result')==1 and count(self.w,'spinner_pushed')==1 and self.loading_seen and valid(self.w.get_property('SpinnerWidget')),'native login/spinner/async preparation/request order differs');require(self.healths()==self.health_before,'host request changed original gameplay health');self.report.update(profile=self.profile,native_actual_entry_selection_and_online_init=True,native_spinner_afterpush_and_async_loading_before_submit=True,request_mode=2,request_bots='0',prepared_handler_calls=count(self.w,'prepared'),host_request_payload=self.payload);self.enter('host_arrival')
        elif self.phase=='host_arrival':
            for world in ue.all_worlds():
                if world.get_world_type() not in (1,3):continue
                controller=policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)
                if not valid(controller) or controller is self.controller:continue
                bridge=policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
                if not valid(bridge):continue
                snap=bridge.call_function('CaptureSnapshot')
                if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
                mode=policy.lib('GameplayStatics').call_function('GetGameMode',world);options=mode.get_property('OptionsString');level=policy.lib('GameplayStatics').call_function('GetCurrentLevelName',world,True);experience=policy.lib('GameplayStatics').call_function('ParseOption',options,'Experience');bots=policy.lib('GameplayStatics').call_function('ParseOption',options,'NumBots');require(level==self.payload['map'][1].rsplit('/',1)[-1] and experience==self.payload['args']['Experience'] and bots=='0' and count(self.w,'completed')==1,'native host completion/destination/bot URL differs');self.new_world=world;self.report.update(native_create_completion_handler_after_original_unbind=True,native_requested_map_experience_player_and_bot_option_ready=True,completion_handler_calls=count(self.w,'completed'),native_destination_level=level,native_destination_experience=experience,native_destination_mode=str(snap.NetMode),native_world_controller_replacement_expected=True);self.destroyed=[];proxy=ue.find_class('DestroySessionCallbackProxy').get_cdo().call_function('DestroySession',world,controller);self.bind(proxy,'OnSuccess',lambda:self.destroyed.append(True),True);self.bind(proxy,'OnFailure',lambda:self.destroyed.append(False));proxy.call_function('Activate');self.enter('host_destroy');return
        elif self.phase=='host_destroy':
            if not self.destroyed:return
            require(self.destroyed==[True],'fixture owned host session native destroy failed');self.report['owned_native_session_destroyed']=True;self.finish()
    def cleanup(self):
        if self.mode=='host' and hasattr(self,'new_world'):self.world=self.new_world
        super().cleanup()
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_HOST_SESSION_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HOST_SESSION_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHostSessionResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
