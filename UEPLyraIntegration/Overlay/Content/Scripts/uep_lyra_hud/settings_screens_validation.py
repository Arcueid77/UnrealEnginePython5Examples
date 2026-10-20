"""Native registry/tab/activation/modal flow with temporary HDR-state restoration."""
import atexit
import hashlib
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import settings_screens_mixin as policy
from .settings_screens_contract import PROFILES,FALSE_FIELDS,require,validate

EVENT='BndEvt__LyraSettingScreen_Settings_Panel_K2Node_ComponentBoundEvent_0_OnExecuteNamedActionBP__DelegateSignature'
ROUTES=(('GameSettings.Action.EditSafeZone','/Game/UI/Settings/Screens/SafeZone/W_SafeZoneEditor.W_SafeZoneEditor_C'),('GameSettings.Action.EditBrightness',policy.CLASSES['gamma']),('GameSettings.Action.CalibrateHDR',policy.CLASSES['hdr']))
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def count(w,k,m):return sum(policy.evidence(w)[p+'_'+k+'_'+m] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],temporary_native_hdr_overrides_exercised=False);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.profile_widgets=[];self.modals=[];self.proxies=[];self.classes={};self.cdos={};self.index=0;self.states=[]
    def config_hashes(self):
        root=Path(ue.convert_relative_path_to_full(ue.get_content_dir())).parent/'Saved/Config';return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('GameUserSettings.ini')} if root.exists() else {}
    def settings_state(self):
        return dict(ui_level=float(ue.IConsoleManager.get_float('r.HDR.UI.Level')),ui_nits=float(self.settings.call_function('GetHDRUILuminanceNits')),separate=bool(self.settings.call_function('IsHDRUILuminanceSeparate')),max_nits=int(self.settings.call_function('GetMaximumHDRDisplayNits')),safe_zone=float(self.settings.call_function('GetSafeZone')))
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.config_before=self.config_hashes();self.settings=ue.find_class('GameUserSettings').get_cdo().call_function('GetGameUserSettings');self.settings_before=self.settings_state();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.tag_class=ue.find_struct('GameplayTag');self.proxy_class=ue.find_class('AsyncAction_PushContentToLayerForPlayer');self.start_profile()
    def create(self,k):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[k],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile);self.profile_widgets.append(w);w.call_function('AddToPlayerScreen',0);return w
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.current={k:self.create(k) for k in ('gamma','hdr','screen')};self.screen=self.current['screen'];self.panel=self.screen.get_property('Settings_Panel');self.row=dict(profile=self.profile,registered_tab_callbacks=0,hdr_luminance_cases=0,native_modal_afterpush_callbacks=0);self.state={};self.screen.call_function('ActivateWidget');self.frames=0;self.enter('settle')
    def history(self,label,tag):
        file=self.path.parent/(self.profile+'-'+tag+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(label,str(file)),'native settings tab text export failed');raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [s.strip() for s in text.splitlines() if s.strip().startswith('Text=')]
    def basic(self):
        gamma=self.current['gamma'];hdr=self.current['hdr'];require(one(gamma.call_function('BP_GetDesiredFocusTarget'))==gamma,'const Gamma focus must return self');self.row['gamma_actual_const_focus_returns_self']=True;material=hdr.get_property('MID_Checkerboard');require(material==hdr.get_property('Checkerboard').call_function('GetDynamicMaterial') and count(hdr,'hdr','construct')>0,'actual HDR Construct did not cache its native material');self.row['hdr_actual_construct_caches_native_material']=True;values=[]
        for v in (-.25,0.,.125,1.,2.):hdr.call_function('OnMaxLuminanceChange',v);actual=float(one(material.call_function('K2_GetScalarParameterValue','MaxLuminance')));require(actual==v,'raw HDR luminance material value differs');values.append(actual)
        self.row.update(hdr_luminance_cases=5,hdr_raw_luminance_material_matches=True);self.state['luminance']=values;tabs=self.screen.get_property('TopSettingsTabs');expected=[];titles=[]
        for name in policy.TABS:
            collection,has=self.screen.call_function('GetSettingCollection',name)
            if has:expected.append(name)
        actual=[str(tabs.call_function('GetTabIdAtIndex',i)) for i in range(int(tabs.call_function('GetTabCount')))];require(actual==expected,'source visible tab order/hidden policy differs');self.row['registered_tab_callbacks']=count(self.screen,'screen','register');require(self.row['registered_tab_callbacks']==5,'actual Construct did not register five top-level collections');self.row['actual_construct_registers_original_tab_order']=True
        for name in actual:
            button=tabs.call_function('GetTabButtonBaseByID',name);history=self.history(button.get_property('ButtonTextBlock'),'tab-'+name);require(any('NSLOCTEXT' in s for s in history),'tab collection display-name localization lost');titles.append(dict(id=name,history=history))
        self.row['native_tab_titles_preserve_localization_and_hidden_policy']=True;before=count(self.screen,'screen','navigate');require(tabs.call_function('SelectTabByID','AudioCollection',True),'actual native tab selection failed');require(count(self.screen,'screen','navigate')>before,'native selected-tab delegate did not route navigation');self.row['actual_native_tab_selection_routes_navigation']=True;self.state['tabs']=titles;self.registry=self.screen.get_property('Registry');actions=[s for s in self.registry.get_property('RegisteredSettings') if s.is_a(ue.find_class('GameSettingAction'))];require(actions,'real native action settings missing');self.action_setting=actions[0];self.screen.call_function(EVENT,self.action_setting,self.tag_class(TagName='GameSettings.Action'));self.proxy_baseline={path(p) for p in ue.tobject_iterator(self.proxy_class)};self.frames=0;self.enter('unknown')
    def start_action(self):
        tagname,cls=ROUTES[self.action_index];before={path(p) for p in ue.tobject_iterator(self.proxy_class)};self.afterpush=[];self.screen.call_function(EVENT,self.action_setting,self.tag_class(TagName=tagname));new=[p for p in ue.tobject_iterator(self.proxy_class) if path(p) not in before];require(len(new)==1,'native async route must create one proxy');proxy,=new
        def observe(widget):self.afterpush.append(widget)
        proxy.bind_event('AfterPush',observe);self.proxies.append((proxy,observe));self.expected_modal=cls;self.enter('modal')
    def observe(self):
        require(time.monotonic()-self.phase_started<25.,'settings screen phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<3:return
            a=self.screen.get_property('OnActivated');p=self.panel.get_property('OnParentScreenActivated')
            if min(float(self.screen.call_function('GetAnimationCurrentTime',a)),float(self.panel.call_function('GetAnimationCurrentTime',p)))<.005:return
            require(count(self.screen,'screen','activate')>0 and count(self.panel,'panel','animate')>0,'actual screen activation did not animate its panel');self.row['actual_screen_and_panel_activation_animation_frames']=True;self.basic()
        elif self.phase=='unknown':
            self.frames+=1
            if self.frames<3:return
            require({path(p) for p in ue.tobject_iterator(self.proxy_class)}<=self.proxy_baseline,'unknown parent action tag created an async push');self.row['exact_unknown_action_tag_does_not_push']=True;self.action_index=0;self.modal_rows=[];self.start_action()
        elif self.phase=='modal':
            if not self.afterpush:return
            require(len(self.afterpush)==1,'native AfterPush emitted more than once');widget=self.afterpush[0];require(path(widget.get_class())==self.expected_modal and widget.call_function('IsActivated'),'native pushed modal class/activation differs');self.modals.append(widget);row=dict(tag=ROUTES[self.action_index][0],widget=path(widget.get_class()),afterpush=1);self.row['native_modal_afterpush_callbacks']+=1
            if self.action_index==2:
                state=self.settings_state();require(state['ui_level']==1. and state['ui_nits']==10000. and state['separate'] is True,'original HDR activation overrides were not exercised');self.report['temporary_native_hdr_overrides_exercised']=True;row['hdr_override']=dict(ui_level=state['ui_level'],ui_nits=state['ui_nits'],separate=state['separate'])
            widget.call_function('DeactivateWidget');policy.lib('CommonUIExtensions').call_function('PopContentFromLayer',widget);self.modal_rows.append(row);self.frames=0;self.enter('closed')
        elif self.phase=='closed':
            self.frames+=1
            if self.frames<4:return
            require(not self.modals[-1].call_function('IsActivated'),'owned modal did not deactivate');require(self.settings_state()==self.settings_before,'native calibration state did not restore');self.action_index+=1
            if self.action_index<len(ROUTES):self.start_action()
            else:
                self.row.update(actual_native_async_afterpush_widgets_match_routes=True,native_hdr_activation_overrides_and_deactivation_restore=True);self.state['modals']=self.modal_rows;self.screen.call_function('DeactivateWidget')
                for w in self.current.values():w.call_function('RemoveFromParent')
                self.report['profiles'].append(self.row);self.states.append(self.state);self.report['matrices']=self.states;self.index+=1
                if self.index<len(PROFILES):self.start_profile()
                else:self.report['source_python_state_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        for proxy,fn in self.proxies:
            if policy.valid(proxy):proxy.unbind_event('AfterPush',fn)
        for w in self.modals:
            if policy.valid(w):
                if w.call_function('IsActivated'):w.call_function('DeactivateWidget')
                policy.lib('CommonUIExtensions').call_function('PopContentFromLayer',w)
        self.report['all_owned_modal_widgets_popped']=all(not policy.valid(w) or not w.call_function('IsActivated') for w in self.modals)
        for w in self.widgets:
            if w in self.profile_widgets:ue.clear_mixin_profile(w)
            if w.call_function('IsActivated'):w.call_function('DeactivateWidget')
            w.call_function('StopAllAnimations');w.call_function('RemoveFromParent');w.remove_from_root()
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for c in getattr(self,'class_roots',[]):c.remove_from_root()
        self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['settings_and_native_hdr_overrides_restored']=not hasattr(self,'settings_before') or self.settings_state()==self.settings_before;self.report['settings_config_files_unchanged']=not hasattr(self,'config_before') or self.config_hashes()==self.config_before;self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<250.,'native settings screen timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SETTINGS_SCREENS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SETTINGS_SCREENS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSettingsScreensResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
