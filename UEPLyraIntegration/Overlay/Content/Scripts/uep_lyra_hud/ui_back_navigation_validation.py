"""Opt-in real CommonUI layer, focus and bound Back-button observations."""
import atexit,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from . import menu_layers_mixin as menu,settings_screens_mixin as settings,bound_action_mixin as bound
from .ui_back_navigation_contract import FORBIDDEN,validate

class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.selectors=[];self.roots=[];self.widgets=[];self.cycle=0
        self.profile=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPUIBackProfile='))
        self.report=dict(status='running',error=None,profile=self.profile,cases=[]);self.report.update(dict.fromkeys(FORBIDDEN,False))
        self.classes={k:ue.load_class(p) for k,p in dict(menu=menu.CLASSES['menu'],screen=settings.CLASSES['screen'],panel=settings.CLASSES['panel'],back=bound.CLASS).items()}
        for cls in self.classes.values():
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
            self.selectors.append((cls,cls.get_cdo().get_property('PythonMixinProfile')));cls.get_cdo().set_property('PythonMixinProfile',self.profile)

    def begin(self):
        self.report['native_mode']=str(menu.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode)
        self.health_before=self.healths();self.world_path=self.world.get_path_name();self.start_cycle()

    def own(self,w):
        if w not in self.widgets:w.add_to_root();self.widgets.append(w)
        return w

    def focused(self,w):return bool(w.call_function('HasUserFocus',self.controller) or w.call_function('HasUserFocusedDescendants',self.controller))

    def start_cycle(self):
        for cls,_ in self.selectors:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.current=self.own(menu.lib('CommonUIExtensions').call_function('PushContentToLayer_ForPlayer',self.controller.get_property('Player'),GameplayTag(TagName='UI.Layer.GameMenu'),self.classes['menu']))
        self.row=dict(profile=self.profile,cycle=self.cycle,native_push_entry='CommonUIExtensions.PushContentToLayer_ForPlayer',world=self.world_path)
        self.enter('menu');self.frames=0

    def observe(self):
        if time.monotonic()-self.phase_started>30.:raise AssertionError('Native UI Back timeout in '+self.phase+'; '+str(self.report.get('pending')))
        self.frames+=1
        if self.phase=='menu':
            target=self.current.get_property('OptionsButtons');active=bool(self.current.call_function('IsActivated'));focused=self.focused(target)
            self.report['pending']=dict(menu_active=active,options_focused=focused)
            if self.frames<8 or not active or not focused:return
            self.row['menu_options_native_focus']=True
            selected='python_' if self.profile=='Python' else 'fallback_';other='fallback_' if self.profile=='Python' else 'python_'
            self.menu_before=dict(menu.evidence(self.current));self.selected=selected;self.other=other
            target.call_function('HandleButtonClicked');self.enter('settings');self.frames=0
        elif self.phase=='settings':
            screens=[w for w in ue.tobject_iterator(self.classes['screen']) if menu.valid(w.call_function('GetOwningPlayer')) and w.call_function('GetOwningPlayer')==self.controller and w.call_function('IsActivated')]
            self.report['pending']=dict(active_settings=len(screens))
            if len(screens)!=1:return
            self.screen=self.own(screens[0]);focused=self.focused(self.screen);self.report['pending']['settings_focused']=focused
            if self.frames<8 or not focused:return
            buttons=[]
            for w in ue.tobject_iterator(self.classes['back']):
                if w.call_function('GetOwningPlayer')!=self.controller or not w.call_function('IsVisible'):continue
                label=str(w.get_property('Text_ActionName').call_function('GetText'))
                if label=='Back':buttons.append(w)
            self.report['pending']['native_back_buttons']=len(buttons)
            if len(buttons)!=1:return
            self.back=buttons[0]
            if str(ue.get_mixin_profile(self.screen))!=self.profile or str(ue.get_mixin_profile(self.back))!=self.profile:raise AssertionError('Native UI child did not inherit selected profile')
            counts=menu.evidence(self.current)
            self.row.update(settings_native_focus=True,menu_settings_selected_callbacks=counts[self.selected+'menu_settings']-self.menu_before[self.selected+'menu_settings'],
                menu_settings_other_callbacks=counts[self.other+'menu_settings']-self.menu_before[self.other+'menu_settings'],
                native_back_text='Back',screen_profile_matches=True,back_profile_matches=True,native_back_entry='CommonBoundActionButton.HandleButtonClicked',
                menu_inactive_after_settings_push=not self.current.call_function('IsActivated'))
            self.back_before=dict(bound.evidence(self.back));self.back.call_function('HandleButtonClicked');self.enter('back');self.frames=0
        elif self.phase=='back':
            active=bool(self.screen.call_function('IsActivated'));self.report['pending']=dict(settings_active=active)
            if self.frames<12 or active:return
            counts=bound.evidence(self.back)
            self.row.update(settings_closed_by_native_back=True,closed_settings_has_no_focus=not self.focused(self.screen),
                back_selected_click_callbacks=counts[self.selected+'click']-self.back_before[self.selected+'click'],
                back_other_click_callbacks=counts[self.other+'click']-self.back_before[self.other+'click'],
                world_unchanged=self.world.get_path_name()==self.world_path,health_unchanged=self.healths()==self.health_before)
            self.report['cases'].append(self.row);self.cycle+=1
            if self.cycle==2:self.finish()
            else:self.start_cycle()

    def cleanup(self):
        # Pop only after the observed native Back action has completed (or a
        # failed observation has been recorded). Never use this as its stimulus.
        for w in reversed(self.widgets):
            if menu.valid(w):
                menu.lib('CommonUIExtensions').call_function('PopContentFromLayer',w);w.call_function('RemoveFromParent');w.remove_from_root()
        for cls,value in self.selectors:cls.get_cdo().set_property('PythonMixinProfile',value)
        for cls in self.roots:cls.remove_from_root()
        self.report.update(owned_widgets_unmounted_and_unrooted=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets),
            class_selectors_restored=all(cls.get_cdo().get_property('PythonMixinProfile')==value for cls,value in self.selectors),class_roots_restored=all(not c.is_rooted() for c in self.roots),
            health_unchanged=not hasattr(self,'health_before') or self.healths()==self.health_before)

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_UI_BACK_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_UI_BACK_SHUTDOWN_'+self.report['status'].upper())

    def tick(self,delta):
        if self.finished:return False
        try:
            if time.monotonic()-self.started>210.:raise AssertionError('Native UI Back total timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write()
        except Exception:self.finish(traceback.format_exc())
        return not self.finished

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPUIBackResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
