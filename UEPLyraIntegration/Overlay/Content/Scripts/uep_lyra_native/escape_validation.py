"""Separate actual OS Escape evidence from headless native/Python policy checks."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_world.effect_pad_mixin import valid
from .message_validation import arg
from . import escape_menu as policy
from .escape_validation_contract import PLAN,require,validate,validate_headless


def lib(name):return ue.find_class(name).get_cdo()
def path(obj):return obj.get_path_name() if valid(obj) else None
def count(widget):return sum(policy.metrics(widget)[p+'escape'] for p in ('python_','native_'))


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeEscapeResult'));self.run=arg('UEPNativeEscapeRun');self.root=self.path.parent;self.started=time.monotonic();self.finished=False;self.phase='world';self.stage_index=0;self.serial=0;self.sources={};self.selectors={};self.owned_roots=[];self.overrides=[];self.destructs=[];self.pending_travel=None
        self.constructs=[];self.transitions=[]
        self.headless='-UEPNativeEscapeHeadless' in sys.argv;self.dispatched_serial=0
        self.report=dict(status='running',error=None,run_id=self.run,stages=[],cycles=[],travels=[],destruct_events=self.destructs,construct_events=self.constructs,validation_mode='headless_policy' if self.headless else 'actual_window',direct_handle_calls=self.headless,direct_handle_call_count=0,direct_deactivate_call_count=0,actual_os_keyboard_events=False if self.headless else None,visible_ui_observed=False if self.headless else None,synthetic_keyboard_events=False,cook_package_executed=False,next_action=None,action_serial=0,test_world_kind='isolated CommonUI worlds',full_shooter_scene_rendering_acceptance=False)
        self.classes={name:ue.load_class(name) for name in policy.CLASSES}
        for name,cls in self.classes.items():
            if not cls.is_rooted():cls.add_to_root();self.owned_roots.append(cls)
            ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[cls]={p:v['python_class'] for p,v in row['profiles'].items()};self.selectors[cls]=cls.get_cdo().get_property('PythonMixinProfile')
            for profile,base in self.sources[cls].items():
                attrs={k:v for k,v in vars(base).items() if not k.startswith('__')}
                def destruct(widget):
                    self.destructs.append(dict(widget=widget.get_path_name(),wrapper_id=id(widget),class_path=widget.get_class().get_path_name()));widget.call_mixin_original('Destruct')
                def construct(widget):
                    self.constructs.append(dict(widget=widget.get_path_name(),wrapper_id=id(widget),class_path=widget.get_class().get_path_name()));widget.call_mixin_original('Construct')
                attrs['Destruct']=destruct;attrs['Construct']=construct;ue.register_mixin_profile(cls,profile,type('ObservedEscape'+profile,(),attrs))
        self.set_selectors('NativeFallback');atexit.register(self.finalize)

    def set_selectors(self,profile):
        for cls in self.classes.values():cls.get_cdo().set_property('PythonMixinProfile',profile)
    def enter(self,phase,action=None):
        self.phase=phase;self.phase_started=time.monotonic();self.report['next_action']=action
        if action:self.serial+=1;self.report['action_serial']=self.serial
    def owner_widgets(self,cls,controller):return [w for w in ue.tobject_iterator(cls) if valid(w) and w.call_function('GetOwningPlayer')==controller]
    def ready(self):
        desired=PLAN[self.stage_index][0]
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or desired not in world.get_name():continue
            controller=lib('GameplayStatics').call_function('GetPlayerController',world,0)
            if not valid(controller):continue
            layouts=self.owner_widgets(ue.find_class('PrimaryGameLayout'),controller)
            if len(layouts)!=1:continue
            game_stack=layouts[0].get_property('GameLayer_Stack')
            if self.headless:
                for container in (game_stack,layouts[0].get_property('Menu_Stack')):
                    if not any(c==container for c,value in self.transitions):
                        self.transitions.append((container,float(container.call_function('GetTransitionDuration'))));container.call_function('SetTransitionDuration',0.)
            hosts=[w for w in game_stack.get_property('WidgetList') if w.is_a(self.classes[policy.CLASSES[2]])]
            if not hosts:game_stack.call_function('BP_AddWidget',self.classes[policy.CLASSES[2]]);return
            require(len(hosts)==1,'one original HUD fixture required')
            if not hosts[0].call_function('IsActivated'):continue
            self.world=world;self.controller=controller;self.hud=hosts[0];self.game_stack=game_stack;self.stack=layouts[0].get_property('Menu_Stack')
            if self.pending_travel:
                old=self.pending_travel;destroyed=any(e['wrapper_id']==old['wrapper_id'] or e['widget']==old['widget'] for e in self.destructs[old['destruct_start']:])
                rebuilt=id(self.hud)!=old['wrapper_id'] or any(e['wrapper_id']==id(self.hud) for e in self.constructs[old['construct_start']:])
                self.report['travels'].append(dict(from_world=old['world'],to_world=world.get_path_name(),native_destruct_observed=destroyed,new_hud_observed=rebuilt));self.pending_travel=None
            self.prepare_stage();return

    def prepare_stage(self):
        name,profile,cycles=PLAN[self.stage_index];ue.set_mixin_profile(self.hud,profile);self.overrides.append(self.hud);self.cycles_left=cycles
        self.report['stages'].append(dict(world=self.world.get_path_name(),profile=profile,cycles=cycles,hud=path(self.hud)));self.begin_cycle()
    def begin_cycle(self):
        require(not self.stack.get_property('WidgetList'),'native Menu layer must begin empty')
        self.before=count(self.hud);self.requested=self.hud.call_function('UEPGetEscapeMenuPath');self.input_before=int(self.hud.call_function('UEPGetCurrentUIInputMode'));self.ignore_before=self.ignored()
        require(self.requested and self.input_before in (1,2),'natural gameplay HUD/menu/input configuration missing')
        self.enter('open','press_escape_to_open')
    def ignored(self):return [bool(self.controller.call_function(name)) for name in ('IsMoveInputIgnored','IsLookInputIgnored')]
    def observe(self):
        if self.phase=='open':
            menu=self.stack.call_function('GetActiveWidget')
            if not valid(menu) or not menu.call_function('IsActivated'):return
            require(count(self.hud)==self.before+1,'actual Escape did not enter the selected native/Python handler once')
            mode=int(self.hud.call_function('UEPGetCurrentUIInputMode'));self.report['last_open_input_mode']=mode
            self.report['last_menu']=dict(class_path=menu.get_class().get_path_name(),input_config=int(menu.get_property('InputConfig')),active=True)
            if not self.headless and mode!=0:
                require(time.monotonic()-self.phase_started<15.,'native Menu did not own input after activation settled: '+str(mode));return
            self.menu=menu;self.open_count=count(self.hud);self.row=dict(map=self.world.get_name(),profile=PLAN[self.stage_index][1],requested_class=self.requested,menu_class=menu.get_class().get_path_name(),menu_desired_input_config=int(menu.get_property('InputConfig')),open_dispatch_delta=self.open_count-self.before,input_before=self.input_before,input_open=int(self.hud.call_function('UEPGetCurrentUIInputMode')),ignore_before=self.ignore_before,original_menu_layer=menu in self.stack.get_property('WidgetList'),owning_player_matches=menu.call_function('GetOwningPlayer')==self.controller)
            self.enter('close','press_escape_to_close')
        elif self.phase=='close':
            if self.stack.get_property('WidgetList') or (valid(self.menu) and self.menu.call_function('IsActivated')):return
            if int(self.hud.call_function('UEPGetCurrentUIInputMode'))!=self.input_before or self.ignored()!=self.ignore_before:
                require(time.monotonic()-self.phase_started<15.,'native gameplay input did not resume after deactivation settled');return
            self.row.update(close_dispatch_delta=count(self.hud)-self.open_count,input_after=int(self.hud.call_function('UEPGetCurrentUIInputMode')),ignore_after=self.ignored(),menu_deactivated_and_removed=not valid(self.menu) or not self.menu.call_function('IsActivated'))
            require(self.row['input_after']==self.input_before and self.row['ignore_after']==self.ignore_before,'native gameplay input did not resume')
            self.report['cycles'].append(self.row);self.cycles_left-=1
            if self.cycles_left:self.begin_cycle()
            else:self.next_stage()
        elif self.phase=='await_finish':
            if self.headless:self.finish();return
            token=read_json(self.root/'finish.json')
            if token is not None:require(token['run_id']==self.run,'foreign UI completion token');self.finish()

    def next_stage(self):
        self.stage_index+=1
        if self.stage_index==len(PLAN):self.enter('await_finish','capture_final_state_and_finish');return
        map_name,profile,cycles=PLAN[self.stage_index];self.set_selectors(profile)
        if map_name in self.world.get_name():self.prepare_stage();return
        self.pending_travel=dict(widget=self.hud.get_path_name(),wrapper_id=id(self.hud),world=self.world.get_path_name(),destruct_start=len(self.destructs),construct_start=len(self.constructs));self.old_hud=self.hud
        self.game_stack.call_function('ClearWidgets')
        self.enter('world');lib('GameplayStatics').call_function('OpenLevel',self.world,'/Game/UEPValidation/'+map_name,True,'')

    def cleanup(self):
        self.report['menu_stack_empty_at_exit']=not hasattr(self,'stack') or not valid(self.stack) or not self.stack.get_property('WidgetList')
        for widget in self.overrides:
            if valid(widget):ue.clear_mixin_profile(widget)
        for cls,profiles in self.sources.items():
            for profile,base in profiles.items():ue.register_mixin_profile(cls,profile,base)
            cls.get_cdo().set_property('PythonMixinProfile',self.selectors[cls])
        for cls in self.owned_roots:cls.remove_from_root()
        for container,value in self.transitions:
            if valid(container):container.call_function('SetTransitionDuration',value)
        self.report['headless_transition_overrides']=len(self.transitions)
        self.report['stack_transitions_restored_or_released']=all(not valid(c) or float(c.call_function('GetTransitionDuration'))==value for c,value in self.transitions)
        self.report['profile_classes_selectors_roots_restored']=all(not c.is_rooted() for c in self.owned_roots) and all(c.get_cdo().get_property('PythonMixinProfile')==value for c,value in self.selectors.items()) and all(any(r['target_class']==c and all(r['profiles'][p]['python_class'] is base for p,base in profiles.items()) for r in ue.get_registered_mixins()) for c,profiles in self.sources.items())

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<(180. if self.headless else 900.),'Escape validation timed out')
            if self.headless and self.serial>self.dispatched_serial and self.phase in ('open','close'):
                self.dispatched_serial=self.serial
                if self.phase=='open':self.report['direct_handle_call_count']+=1;self.hud.call_function('HandleEscapeAction')
                else:self.report['direct_deactivate_call_count']+=1;self.menu.call_function('DeactivateWidget')
            if self.phase=='world':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.report['stage_index']=self.stage_index;atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report);(ue.log_error if error else ue.log)(('UEP_NATIVE_ESCAPE_HEADLESS_' if self.headless else 'UEP_NATIVE_ESCAPE_DIFFERENTIAL_')+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';(validate_headless if self.headless else validate)(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)(('UEP_NATIVE_ESCAPE_HEADLESS_SHUTDOWN_' if self.headless else 'UEP_NATIVE_ESCAPE_SHUTDOWN_')+self.report['status'].upper())


validation=Validation();ticker=ue.add_ticker(validation.tick)
