"""Actual CommonUI stack activation/deactivation; never replay the BP callback."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from . import explorer_screens_mixin as policy
from .explorer_screens_contract import FALSE_FIELDS,require,validate

def path(obj):return obj.get_path_name() if valid(obj) else None
def widgets(stack):return [path(w) for w in stack.get_property('WidgetList')]
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.widgets=[];self.selectors={};self.class_roots=[];self.plan=[(k,p) for k in ('inventory','map') for p in ('BlueprintFallback','Python')];self.index=0
    def begin(self):
        self.inventory_before=capture(self.controller);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()}
        for cls in self.classes.values():
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            self.selectors[cls]=cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(cls)
        layouts=[w for w in ue.tobject_iterator(ue.find_class('PrimaryGameLayout')) if w.call_function('GetOwningPlayer')==self.controller and w.call_function('IsInViewport')];require(len(layouts)==1,'one actual local-player root layout required');self.layout=layouts[0];self.stack=self.layout.get_property('Menu_Stack');self.baseline=widgets(self.stack);self.active_before=path(self.stack.call_function('GetActiveWidget'));require(not self.baseline,'owned Menu layer matrix requires an empty original Menu stack');self.transition=float(self.stack.call_function('GetTransitionDuration'));self.stack.call_function('SetTransitionDuration',0.);self.start_case()
    def own(self,w,profile):
        w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,profile);return w
    def start_case(self):
        self.kind,self.profile=self.plan[self.index];cls=self.classes[self.kind];cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.subject=self.own(self.stack.call_function('BP_AddWidget',cls),self.profile);self.count_before=copy.deepcopy(policy.evidence(self.subject));self.row=dict(kind=self.kind,profile=self.profile);self.enter('active')
    def observe(self):
        require(time.monotonic()-self.phase_started<15.,'Explorer screen phase timeout: '+self.phase)
        if self.phase=='active':
            if not self.subject.call_function('IsActivated') or self.stack.call_function('GetActiveWidget')!=self.subject:return
            self.row['natural_native_activation']=path(self.subject) in widgets(self.stack);self.subject.call_function('DeactivateWidget');self.enter('removed')
        elif self.phase=='removed':
            if self.subject.call_function('IsActivated') or path(self.subject) in widgets(self.stack):return
            counts={k:v-self.count_before[k] for k,v in policy.evidence(self.subject).items()};self.row.update(counts=counts,native_deactivation_callback_once=sum(counts.values())==1,removed_from_native_layer=True,original_stack_widgets_preserved=widgets(self.stack)==self.baseline)
            self.subject.call_function('DeactivateWidget');self.row['repeat_deactivation_no_extra_callback']=counts=={k:v-self.count_before[k] for k,v in policy.evidence(self.subject).items()}
            extra=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[self.kind],self.controller);self.own(extra,self.profile);extra.call_function('ActivateWidget');before=copy.deepcopy(policy.evidence(extra));extra.call_function('DeactivateWidget');self.row['unstacked_deactivation_safe']=not extra.call_function('IsActivated') and sum(policy.evidence(extra).values())-sum(before.values())==1 and widgets(self.stack)==self.baseline;self.report['cases'].append(self.row);self.index+=1
            if self.index<len(self.plan):self.start_case()
            else:self.finish()
    def cleanup(self):
        for w in self.widgets:
            if valid(w):
                if w.call_function('IsActivated'):w.call_function('DeactivateWidget')
                ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        for cls,value in self.selectors.items():cls.get_cdo().set_property('PythonMixinProfile',value)
        for cls in self.class_roots:cls.remove_from_root()
        self.report['owned_widgets_roots_profiles_and_class_selectors_restored']=all(not w.is_rooted() and not w.call_function('IsActivated') and not w.call_function('IsInViewport') for w in self.widgets) and all(cls.get_cdo().get_property('PythonMixinProfile')==value for cls,value in self.selectors.items()) and all(not cls.is_rooted() for cls in self.class_roots)
        if hasattr(self,'stack'):
            self.stack.call_function('SetTransitionDuration',self.transition);self.report['original_layer_widgets_and_transition_restored']=widgets(self.stack)==self.baseline and path(self.stack.call_function('GetActiveWidget'))==self.active_before and float(self.stack.call_function('GetTransitionDuration'))==self.transition
        self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.inventory_before and self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'Explorer screens readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_SCREENS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_SCREENS_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerScreensResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
