"""Mount real CommonUI widgets and exercise native input/tab/selection routing."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import foundation_buttons_mixin as policy
from .foundation_buttons_contract import PROFILES,FALSE_FIELDS,require,validate


def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def text(w):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',w.call_function('GetText'))
def count(w,k):return sum(policy.evidence(w)[p+'_'+k] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[],manual_hover_action_and_designer_callbacks_also_used=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.classes={};self.cdos={};self.index=0;self.states=[]
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.class_roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.input=policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubSystemFromPlayerController',self.controller,ue.find_class('CommonInputSubsystem'));require(policy.valid(self.input),'actual CommonInput subsystem missing');self.input_before=int(self.input.call_function('GetCurrentInputType'));self.primary=ue.load_class('/Game/UI/Foundation/Buttons/ButtonStyle-Primary-M.ButtonStyle-Primary-M_C');self.clear=ue.load_class('/Game/UI/Foundation/Buttons/ButtonStyle-Clear.ButtonStyle-Clear_C');self.probe=self.world.actor_spawn(ue.load_class('/Game/UEPValidation/BP_FoundationButtonsProbe.BP_FoundationButtonsProbe_C'));self.start_profile()
    def create(self,key):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[key],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile);w.call_function('AddToPlayerScreen',0);return w
    def text_history(self,label,tag):
        file=self.path.parent/(self.profile+'-'+tag+'-text.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(label,str(file)),'native FText widget export failed');data=file.read_bytes();value=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [line.strip() for line in value.splitlines() if line.strip().startswith('Text=')]
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.base=self.create('base');self.tab=self.create('tab');self.tabs=self.create('tabs');self.current=[self.base,self.tab,self.tabs];self.row=dict(profile=self.profile,native_button_style_cases=0,alignment_cases=0,progress_cases=0,dynamic_tabs_created=0);self.report['pending_profile']=self.row;self.frames=0;self.enter('settle')
    def styles(self):
        w=self.base;rows=[];w.call_function('SetControllerStyle',self.clear);w.call_function('SetMouseKeyboardStyle',self.primary)
        for kind,expected in ((0,self.primary),(1,self.clear),(0,self.primary),(1,self.clear)):
            before=count(w,'combined');self.input.call_function('SetCurrentInputType',kind);w.call_function('UpdateButtonStyle');actual=w.call_function('GetStyle');style=actual.get_class() if actual is not None else None;current=w.call_function('GetCurrentTextStyleClass');labelstyle=w.get_property('Text').get_property('Style');rows.append(dict(input=kind,style=path(style),text_style=path(labelstyle),native_text_style=path(current)));require(style==expected and labelstyle==current and count(w,'combined')>before,'native button input/style callback differs');self.row['native_button_style_cases']+=1
        w.call_function('SetControllerStyle',None);w.call_function('UpdateStyle',True);require(w.call_function('GetStyle').get_class()==self.primary,'invalid controller style did not fall back');w.call_function('SetControllerStyle',self.clear);return rows
    def content(self):
        w=self.base;rows=[]
        for value in range(4):w.call_function('SetContentAlignment',value);slot=w.get_property('ContentBorder').call_function('GetContentSlot');require(int(slot.get_property('HorizontalAlignment'))==value,'native BorderSlot alignment differs');rows.append(value);self.row['alignment_cases']+=1
        progress=[]
        for value in (-.25,0.,.5,1.,1.25):w.call_function('OnActionProgress',value);actual=float(one(w.call_function('GetPressProgress')));require(actual==value,'native press progress was clamped/changed');progress.append(actual);self.row['progress_cases']+=1
        return dict(alignment=rows,progress=progress)
    def labels(self):
        self.probe.call_function('SetLocalized',self.base);self.probe.call_function('SetLocalized',self.tab);require(text(self.base.get_property('Text'))=='Red' and text(self.tab.get_property('ButtonTextBlock'))=='Red','native SetButtonText refresh failed');before=count(self.base,'text');self.base.call_function('PreConstruct',False);self.probe.call_function('SetLocalized',self.base);require(count(self.base,'text')>before,'native parent text refresh missing');return dict(base=self.text_history(self.base.get_property('Text'),'base'),tab=self.text_history(self.tab.get_property('ButtonTextBlock'),'tab'))
    def tab_list(self):
        w=self.tabs;w.set_property('TabButtonPadding',ue.find_struct('Margin')(Left=2.,Top=3.,Right=4.,Bottom=5.));w.set_property('MinTabWidth',137);w.set_property('UseButtonStyle',True);w.set_property('ButtonStyle',self.primary);states=[]
        def wrappers():return [int(w.get_property(n).call_function('GetVisibility')) for n in ('PreviousTabActionWrapper','NextTabActionWrapper')]
        for index in range(3):
            descriptor=one(self.probe.call_function('MakeTab','UEPFoundation'+str(index)));descriptor.TabId='UEPFoundation'+str(index);descriptor.TabButtonType=self.classes['tab'];require(w.call_function('RegisterDynamicTab',descriptor),'native dynamic tab registration failed');button=w.call_function('GetTabButtonBaseByID','UEPFoundation'+str(index));require(policy.valid(button),'native tab button missing');require(text(button.get_property('ButtonTextBlock'))=='Red','native parent label descriptor not delivered');slot=button.get_property('Slot');require(slot.get_property('Padding').Left==2. and int(button.get_property('MinWidth'))==137,'native horizontal slot/minimum style differs');self.row['dynamic_tabs_created']+=1;states.append(dict(count=int(w.call_function('GetTabCount')),wrappers=wrappers()))
        require(states[0]['wrappers']==[2,2] and states[1]['wrappers']==[0,0],'source Hidden/Visible navigation policy differs');before=count(w,'refresh');require(w.call_function('SelectTabByID','UEPFoundation2',True),'native tab selection failed');require(count(w,'refresh')>before,'native OnTabSelected delegate missing');before=count(w,'refresh');w.call_function('SetVisibility',1);w.call_function('SetVisibility',0);require(count(w,'refresh')>=before+2,'native visibility delegate not retained');require(w.call_function('RemoveTab','UEPFoundation2') and w.call_function('RemoveTab','UEPFoundation1'),'native tab removal failed');require(wrappers()==[2,2] and int(w.call_function('GetTabCount'))==1,'source tab removal visibility differs');w.call_function('RemoveAllTabs');w.set_property('DebugButtonTypeDisplay',self.classes['tab']);w.set_property('DebugTabCount',3);before=int(w.get_property('TabButtonBox').call_function('GetChildrenCount'));w.call_function('PreConstruct',False);require(int(w.get_property('TabButtonBox').call_function('GetChildrenCount'))==before,'runtime PreConstruct ran designer preview');w.call_function('PreConstruct',True);require(int(w.get_property('TabButtonBox').call_function('GetChildrenCount'))==3 and int(w.call_function('GetTabCount'))==0,'designer debug tabs incorrectly registered');w.get_property('TabButtonBox').call_function('ClearChildren');self.row.update(actual_native_tab_registration_labels_and_removal=True,native_tab_selection_and_visibility_delegates=True,designer_preview_is_explicit_only=True);return states
    def animation(self,name):
        a=self.tab.get_property(name);return dict(playing=bool(self.tab.call_function('IsAnimationPlaying',a)),forward=bool(self.tab.call_function('IsAnimationPlayingForward',a)),position=float(self.tab.call_function('GetAnimationCurrentTime',a)))
    def observe(self):
        require(time.monotonic()-self.phase_started<15.,'native foundation UI phase timeout: '+self.phase)
        if self.phase=='settle':
            self.frames+=1
            if self.frames<3:return
            self.row['native_construct_and_button_text_refresh']=count(self.base,'pre')>0;state=dict(styles=self.styles(),content=self.content(),history=self.labels(),tabs=self.tab_list());self.states.append(state);self.report['matrices']=self.states;self.row.update(native_input_style_and_current_text_style_match=True,alignment_and_raw_press_progress_match=True,opaque_ftext_history_preserved=all(any('NSLOCTEXT' in s for s in state['history'][k]) for k in ('base','tab')));self.tab.call_function('SetIsToggleable',True);self.tab.call_function('SetIsSelected',False,False);self.tab.call_function('BP_OnHovered');self.enter('hover')
        elif self.phase=='hover':
            if self.animation('Hovered')['position']<.01:return
            require(self.animation('Hovered')['forward'],'actual UMG hover animation not forward');before=count(self.tab,'select');self.tab.call_function('SetIsSelected',True,False);require(count(self.tab,'select')==before+1,'native selection did not call BP_OnSelected');self.enter('select')
        elif self.phase=='select':
            if self.animation('Selected')['position']<.01:return
            require(self.animation('Selected')['forward'],'actual UMG selected animation missing');before=(self.animation('Hovered'),self.animation('Selected'));self.tab.call_function('BP_OnHovered');self.tab.call_function('BP_OnUnhovered');require(before==(self.animation('Hovered'),self.animation('Selected')),'selected hover/unhover changed native animations');self.tab.call_function('SetIsSelected',False,False);self.row['native_hover_selected_animation_guards']=True;self.enter('deselect')
        elif self.phase=='deselect':
            require(not self.tab.call_function('GetSelected'),'native deselection state missing');self.row['actual_native_selection_and_deselection_callbacks']=count(self.tab,'deselect')>0;self.report['profiles'].append(self.row)
            for w in self.current:w.call_function('RemoveFromParent')
            self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.report['source_python_state_pairs_match']=self.states[0]==self.states[1];self.finish()
    def cleanup(self):
        if hasattr(self,'probe') and policy.valid(self.probe):self.probe.actor_destroy()
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        if hasattr(self,'input'):self.input.call_function('SetCurrentInputType',self.input_before);self.report['native_input_type_restored']=int(self.input.call_function('GetCurrentInputType'))==self.input_before
        for c,p in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',p)
        for c in getattr(self,'class_roots',[]):c.remove_from_root()
        self.report['all_widget_roots_and_profile_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items());self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native foundation UI timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_FOUNDATION_BUTTONS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_FOUNDATION_BUTTONS_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPFoundationButtonsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
