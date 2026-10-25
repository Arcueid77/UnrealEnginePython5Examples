"""Opt-in actual CommonUI Back/reopen on both sides of native menu travel."""
import atexit,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from .menu_travel_validation import Validation as Travel,path
from . import menu_layers_mixin as menu,settings_screens_mixin as settings,bound_action_mixin as bound,frontend_menu_mixin as frontend
from . import startup_login_mixin as startup_policy
from .ui_travel_lifetime_contract import FORBIDDEN,require,validate

class Validation(Travel):
    def __init__(self,result):
        super().__init__(result);self.travel_report=self.report
        self.report=dict(status='running',error=None,profile=self.profile,cases=[],travel=self.travel_report);self.lifetime_report=self.report
        self.report.update(dict.fromkeys(FORBIDDEN,False));self.ui_cycle=0;self.origin='game';self.arrived=False;self.frames=0
    def begin(self):
        outer=self.report;self.report=self.travel_report
        try:super().begin()
        finally:self.report=outer
        for key,value in dict(screen=settings.CLASSES['screen'],panel=settings.CLASSES['panel'],back=bound.CLASS).items():
            cls=ue.load_class(value);self.classes[key]=cls;ue.register_declared_mixin(cls)
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            if cls not in self.cdos:self.cdos[cls]=cls.get_cdo().get_property('PythonMixinProfile')
            cls.get_cdo().set_property('PythonMixinProfile',self.profile)
    def own(self,widget):
        if widget not in self.widgets:self.widgets.append(widget)
        if not widget.is_rooted():widget.add_to_root();self.roots.append(widget)
        return widget
    def focused(self,widget):return bool(widget.call_function('HasUserFocus',self.controller) or widget.call_function('HasUserFocusedDescendants',self.controller))
    def evidence(self,parent):return (menu if self.origin=='game' else frontend).evidence(parent)
    def callback_key(self,prefix):return prefix+('menu_settings' if self.origin=='game' else 'options')
    def selected(self):return 'python_' if self.profile=='Python' else 'fallback_'
    def other(self):return 'fallback_' if self.profile=='Python' else 'python_'
    def open_settings(self,parent):
        self.parent=self.own(parent);self.parent_before=dict(self.evidence(parent));self.row=dict(origin=self.origin,cycle=self.ui_cycle,profile=self.profile,
            parent_focus=self.focused(parent),world=path(self.world),controller=path(self.controller))
        require(self.row['parent_focus'],'Native parent has no user focus')
        parent.get_property('OptionsButtons' if self.origin=='game' else 'OptionsButton').call_function('HandleButtonClicked');self.enter('ui_settings');self.frames=0
    def back_actions(self):
        values=[]
        for bar in ue.tobject_iterator(ue.find_class('CommonBoundActionBar')):
            for button in bar.call_function('GetAllEntries'):
                if menu.valid(button) and button.is_a(self.classes['back']) and button.call_function('GetOwningPlayer')==self.controller and str(button.get_property('Text_ActionName').call_function('GetText'))=='Back':values.append(button)
        return values
    def request_return(self):
        self.menu=self.own(menu.lib('CommonUIExtensions').call_function('PushContentToLayer_ForPlayer',self.controller.get_property('Player'),GameplayTag(TagName='UI.Layer.GameMenu'),self.classes['menu']));self.enter('return_menu');self.frames=0
    def observe(self):
        self.frames+=1
        if self.phase in ('confirmation','arrival'):
            outer=self.report;self.report=self.travel_report
            try:super().observe()
            finally:self.report=outer
            return
        require(time.monotonic()-self.phase_started<40.,'UI travel phase timeout: '+self.phase+' '+str(self.report.get('pending')))
        if self.phase=='menu':
            if not self.afterpush:return
            require(len(self.afterpush)==1,'One actual native menu AfterPush required');self.travel_report['native_open_menu_click_afterpush']=True
            if not self.focused(self.afterpush[0]):return
            self.open_settings(self.afterpush[0])
        elif self.phase=='reopen_game':
            if self.frames<8 or not self.parent.call_function('IsActivated') or not self.focused(self.parent):return
            self.open_settings(self.parent)
        elif self.phase=='ui_settings':
            screens=[w for w in ue.tobject_iterator(self.classes['screen']) if w.call_function('GetOwningPlayer')==self.controller and w.call_function('IsActivated')]
            self.report['pending']=dict(active_settings=len(screens),origin=self.origin)
            if len(screens)!=1 or self.frames<8 or not self.focused(screens[0]):return
            self.screen=self.own(screens[0]);actions=self.back_actions();self.report['pending']['back_actions']=len(actions)
            if not actions:return
            self.back=actions[0];self.back_before=dict(bound.evidence(self.back));counts=self.evidence(self.parent)
            self.row.update(settings_object=path(self.screen),settings_focus=True,screen_profile_matches=str(ue.get_mixin_profile(self.screen))==self.profile,
                back_profile_matches=str(ue.get_mixin_profile(self.back))==self.profile,parent_selected_callbacks=counts[self.callback_key(self.selected())]-self.parent_before[self.callback_key(self.selected())],
                parent_other_callbacks=counts[self.callback_key(self.other())]-self.parent_before[self.callback_key(self.other())],back_candidates=[path(w) for w in actions],clicked_back=path(self.back))
            self.back.call_function('HandleButtonClicked');self.enter('ui_closed');self.frames=0
        elif self.phase=='ui_closed':
            if self.frames<12 or self.screen.call_function('IsActivated'):return
            counts=bound.evidence(self.back);self.row.update(settings_closed=True,settings_focus_removed=not self.focused(self.screen),
                back_selected_callbacks=counts[self.selected()+'click']-self.back_before[self.selected()+'click'],back_other_callbacks=counts[self.other()+'click']-self.back_before[self.other()+'click'])
            self.report['cases'].append(self.row);self.ui_cycle+=1
            if self.origin=='game':
                if self.ui_cycle==2:self.request_return()
                else:
                    self.parent=self.own(menu.lib('CommonUIExtensions').call_function('PushContentToLayer_ForPlayer',self.controller.get_property('Player'),GameplayTag(TagName='UI.Layer.GameMenu'),self.classes['menu']));self.enter('reopen_game');self.frames=0
            else:self.enter('frontend_ready');self.frames=0
        elif self.phase=='return_menu':
            if self.frames<8 or not self.menu.call_function('IsActivated') or not self.focused(self.menu):return
            before={path(p) for p in ue.tobject_iterator(self.confirm_cls)};self.results=[];self.menu.get_property('ReturnButton').call_function('HandleButtonClicked')
            new=[p for p in ue.tobject_iterator(self.confirm_cls) if path(p) not in before];require(len(new)==1,'Actual native return confirmation required')
            def result(value):self.results.append(int(value))
            new[0].bind_event('OnResult',result);self.proxies.append((new[0],'OnResult',result));self.enter('confirmation')
        elif self.phase=='frontend_ready':
            if self.frames<8 or not self.frontend.call_function('IsActivated') or not self.focused(self.frontend):return
            self.report['new_frontend_reactivated_after_back']=True
            if self.ui_cycle==2:self.finish()
            else:self.open_settings(self.frontend)
    def finish(self,error=None):
        if self.finished:return
        self.report=self.lifetime_report
        if error is None and self.phase=='arrival' and not self.arrived:
            require(all(not menu.valid(w) or not w.call_function('IsInViewport') and not w.call_function('IsActivated') for w in self.widgets if w.is_a(ue.find_class('CommonActivatableWidget'))),'Old UI still active after native travel')
            self.report['old_ui_naturally_deactivated_before_probe_cleanup']=True
            self.old_callback_counts=(len(self.afterpush),len(self.results));outer=self.report;self.report=self.travel_report
            try:super().cleanup();self.travel_report['status']='passed'
            finally:self.report=outer
            self.report['old_travel_observers_unbound']=True;self.proxies=[];self.widgets=[];self.roots=[];self.class_roots=[]
            for cls in self.cdos:
                if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
                cls.get_cdo().set_property('PythonMixinProfile',self.profile)
            self.world=next(w for w in ue.all_worlds() if path(w)==self.travel_report['new_world_path'] and w.get_world_type() in (1,3));self.controller=startup_policy.controller(self.world,0)
            self.frontend=next(w for w in ue.tobject_iterator(self.classes['frontend']) if w.call_function('GetOwningPlayer')==self.controller and w.call_function('IsActivated'))
            self.arrived=True;self.origin='frontend';self.ui_cycle=0;self.enter('frontend_ready');self.frames=0;return
        self.finished=True
        try:
            self.report['old_travel_callbacks_quiet_after_new_ui']=self.arrived and self.old_callback_counts==(len(self.afterpush),len(self.results))
            outer=self.report;self.report=self.travel_report
            try:super().cleanup()
            finally:self.report=outer
            self.report.update(owned_ui_unmounted_and_unrooted=all(not menu.valid(w) or not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets),
                selectors_and_class_roots_restored=all(c.get_cdo().get_property('PythonMixinProfile')==p for c,p in self.cdos.items()) and all(not c.is_rooted() for c in self.class_roots))
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_UI_TRAVEL_LIFETIME_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_UI_TRAVEL_LIFETIME_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPUITravelLifetimeResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
