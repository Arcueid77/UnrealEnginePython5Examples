"""Actual native layer registration, async prompts and native button handlers."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import re
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import menu_layers_mixin as policy
from .menu_layers_contract import PROFILES,FALSE_FIELDS,require,validate

def arg(k,default):return next((v.split('=',1)[1] for v in sys.argv if v.startswith('-'+k+'=')),default)
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def count(w,k,m):return sum(policy.evidence(w)[p+'_'+k+'_'+m] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.mode=arg('UEPMenuLayerMode','life');self.only_profile=arg('UEPMenuLayerProfile','Python');self.report=dict(status='running',error=None,mode=self.mode,profiles=[],native_request_exit_fallback_used=False);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.widgets=[];self.explicit=[];self.proxies=[];self.modals=[];self.index=0;self.states=[]
    def create(self,k,mount=True):
        cls=self.classes[k];cls.get_cdo().set_property('PythonMixinProfile',self.profile);w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,cls,self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile);self.explicit.append(w)
        if mount:w.call_function('AddToPlayerScreen',0)
        return w
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));self.input_before=int(self.input.call_function('GetCurrentInputType'));self.push_class=ue.find_class('AsyncAction_PushContentToLayerForPlayer');self.confirm_class=ue.find_class('AsyncAction_ShowConfirmation')
        if self.mode=='quit':self.profile=self.only_profile;self.menu=self.create('menu');self.report['profile']=self.profile;self.frames=0;self.enter('quit')
        else:self.start_profile()
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.current={k:self.create(k,k!='layout') for k in self.classes};self.menu=self.current['menu'];self.row=dict(profile=self.profile,native_afterpush_callbacks=0,native_confirmation_results=[]);self.state={};self.menu.call_function('ActivateWidget');self.frames=0;self.enter('settle')
    def history(self,label,tag):
        file=self.path.parent/(self.profile+'-'+tag+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(label,str(file)),'native menu/prompt text export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [s.strip() for s in text.splitlines() if s.strip().startswith(('Text=','TextStyle='))]
    def setup_checks(self):
        require(one(self.menu.call_function('BP_GetDesiredFocusTarget'))==self.menu.get_property('OptionsButtons') and one(self.current['spinner'].call_function('BP_GetDesiredFocusTarget'))==self.current['spinner'],'const focus targets differ');self.row['menu_and_spinner_const_focus_targets']=True
        close=self.current['close'];close.get_property('CloseScreenButton').call_function('HandleButtonClicked');parent=self.current['spinner'];root=parent.get_property('WidgetTree').get_property('RootWidget')
        if root.is_a(ue.find_class('ContentWidget')):root.call_function('SetContent',close)
        else:root.call_function('AddChild',close)
        parent.call_function('ActivateWidget');require(parent.call_function('IsActivated'),'owned activatable close parent missing');close.get_property('CloseScreenButton').call_function('HandleButtonClicked');require(not parent.call_function('IsActivated') and count(close,'close','click')>=2,'native touch-close handler did not find/deactivate actual parent');self.row['touch_close_unparented_noop_and_parent_native_deactivation']=True
    def request_layer_dump(self):
        # OBJ DUMP uses FProperty::ExportText with PPF_IncludeTransient. The
        # normal T3D exporter excludes the private transient native Layers map.
        layout=self.current['layout'];self.dump_begin='UEP_MENU_LAYER_DUMP_BEGIN '+path(layout);self.dump_end='UEP_MENU_LAYER_DUMP_END '+path(layout);ue.log(self.dump_begin);policy.lib('KismetSystemLibrary').call_function('ExecuteConsoleCommand',self.world,'obj dump "'+path(layout)+'" show=PrimaryGameLayout',self.controller);ue.log(self.dump_end);self.enter('native_layer_dump')
    def check_layer_dump(self):
        text=self.path.with_suffix('.log').read_text(encoding='utf-8-sig',errors='replace')
        if self.dump_begin not in text or self.dump_end not in text:return False
        dump=text.split(self.dump_begin,1)[1].split(self.dump_end,1)[0];require(path(self.current['layout']) in dump and '*** Property dump for object ' in dump,'native layer dump object identity differs');lines=re.findall(r'\bLayers=([^\r\n]+)',dump);require(len(lines)==1,'native transient Layers property missing from debug dump');pairs=re.findall(r'\(\(TagName="([^"]+)"\),([^)]*)\)',lines[0]);layout=self.current['layout'];actual={tag:value for tag,value in pairs};require(len(pairs)==4 and len(actual)==4 and set(actual)=={tag for tag,_ in policy.LAYERS} and all(path(layout.get_property(field)) in actual[tag] for tag,field in policy.LAYERS) and count(layout,'layout','initialize')>0,'actual native OnInitialized tag/stack map differs');(self.path.parent/(self.profile+'-native-layer-dump.txt')).write_text(dump,encoding='utf-8');self.row['actual_native_initialize_four_tag_stack_pairs']=True;self.state['layers']=[name for name,_ in policy.LAYERS];return True
    def start_settings(self):
        baseline={path(p) for p in ue.tobject_iterator(self.push_class)};self.afterpush=[];self.menu.get_property('OptionsButtons').call_function('HandleButtonClicked');new=[p for p in ue.tobject_iterator(self.push_class) if path(p) not in baseline];require(len(new)==1,'menu native settings click must create one async proxy');proxy,=new
        def done(widget):self.afterpush.append(widget)
        proxy.bind_event('AfterPush',done);self.proxies.append((proxy,'AfterPush',done));self.enter('settings')
    def start_confirmation(self):
        self.menu.call_function('ActivateWidget');baseline={path(p) for p in ue.tobject_iterator(self.confirm_class)};self.results=[];self.menu.get_property('ReturnButton').call_function('HandleButtonClicked');new=[p for p in ue.tobject_iterator(self.confirm_class) if path(p) not in baseline];require(len(new)==1,'native return click must create one confirmation proxy');proxy,=new
        def result(value):self.results.append(int(value))
        proxy.bind_event('OnResult',result);self.proxies.append((proxy,'OnResult',result));self.enter('confirmation')
    def observe(self):
        require(time.monotonic()-self.phase_started<25.,'menu/layer phase timeout: '+self.phase)
        if self.phase=='quit':
            self.frames+=1
            if self.frames<4:return
            self.input.call_function('SetCurrentInputType',1);require(int(self.input.call_function('GetCurrentInputType'))==1,'owned native quit precondition needs gamepad input');self.menu.get_property('QuitButton_EditorOnly').call_function('HandleButtonClicked');require(count(self.menu,'menu','quit')>0 and int(self.input.call_function('GetCurrentInputType'))==0,'native quit handler did not reset input');self.report.update(native_quit_requested_by_owned_menu=True,native_input_reset_to_mouse_before_quit=True);self.finish(request_exit=False)
        elif self.phase=='settle':
            self.frames+=1
            if self.frames<3:return
            animation=self.menu.get_property('OnActivated')
            if float(self.menu.call_function('GetAnimationCurrentTime',animation))<.005:return
            require(count(self.menu,'menu','activate')>0,'actual native menu activation callback missing');self.row['actual_native_menu_activation_animation']=True;self.request_layer_dump()
        elif self.phase=='native_layer_dump':
            if not self.check_layer_dump():return
            self.setup_checks();self.start_settings()
        elif self.phase=='settings':
            if not self.afterpush:return
            require(len(self.afterpush)==1 and path(self.afterpush[0].get_class())=='/Game/UI/Settings/W_LyraSettingScreen.W_LyraSettingScreen_C' and not self.menu.call_function('IsActivated'),'native settings AfterPush/BeforePush menu deactivation differs');self.row.update(native_afterpush_callbacks=1,native_settings_afterpush_and_beforepush_deactivation=True);self.modals.append(self.afterpush[0]);self.afterpush[0].call_function('DeactivateWidget');policy.lib('CommonUIExtensions').call_function('PopContentFromLayer',self.afterpush[0]);self.frames=0;self.enter('settings_closed')
        elif self.phase=='settings_closed':
            self.frames+=1
            if self.frames<4:return
            self.start_confirmation()
        elif self.phase=='confirmation':
            dialogs=[w for w in ue.tobject_iterator(ue.find_class('LyraConfirmationScreen')) if w.call_function('IsActivated')]
            if not dialogs:return
            require(len(dialogs)==1,'expected one active native confirmation');dialog,=dialogs;self.modals.append(dialog);title=self.history(dialog.get_property('Text_Title'),'confirmation-title');body=self.history(dialog.get_property('RichText_Description'),'confirmation-body');require(any('NSLOCTEXT' in s for s in title) and any('NSLOCTEXT' in s for s in body),'original confirmation prompt localization lost');self.state.update(title=title,body=body);self.row['native_confirmation_prompt_localization_preserved']=True;buttons=dialog.get_property('EntryBox_Buttons').call_function('GetAllEntries');require(len(buttons)==2,'native Yes/No confirmation buttons missing');buttons[1].call_function('HandleButtonClicked');self.frames=0;self.enter('declined')
        elif self.phase=='declined':
            self.frames+=1
            if self.frames<3:return
            require(self.results==[1] and count(self.menu,'menu','result')>0 and self.world==self.controller.get_world(),'native decline result/travel behavior differs');self.row.update(native_confirmation_results=list(self.results),native_decline_button_handler_delivers_result_without_travel=True);self.menu.call_function('DeactivateWidget')
            for w in self.current.values():w.call_function('RemoveFromParent')
            self.report['profiles'].append(self.row);self.states.append(self.state);self.report['matrices']=self.states;self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report['source_python_state_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        for p,name,fn in self.proxies:
            if policy.valid(p):p.unbind_event(name,fn)
        for w in self.modals:
            if policy.valid(w):
                if w.call_function('IsActivated'):w.call_function('DeactivateWidget')
                policy.lib('CommonUIExtensions').call_function('PopContentFromLayer',w)
        for w in self.widgets:
            if w in self.explicit:ue.clear_mixin_profile(w)
            if w.is_a(ue.find_class('CommonActivatableWidget')) and w.call_function('IsActivated'):w.call_function('DeactivateWidget')
            w.call_function('StopAllAnimations');w.call_function('RemoveFromParent');w.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before)
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for c in getattr(self,'class_roots',[]):c.remove_from_root()
        self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<250.,'native menu/layer timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None,request_exit=True):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_MENU_LAYERS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        if request_exit:self.report['native_request_exit_fallback_used']=self.mode=='quit';self.write();ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_MENU_LAYERS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPMenuLayersResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
