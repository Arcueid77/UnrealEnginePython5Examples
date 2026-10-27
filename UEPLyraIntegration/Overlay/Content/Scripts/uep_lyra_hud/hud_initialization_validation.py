"""Opt-in startup import; select original/Python defaults before native Create."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_bots import isolate_bots
from uep_lyra_network_io import atomic_write
from uep_lyra_hud import action_touch_mixin as action, dash_cooldown_mixin as dash
from uep_lyra_hud import ability_failure_mixin as failure, ability_progress_mixin as progress
from uep_lyra_dash_probe import visual as dash_visual
from uep_lyra_ability_failure_probe import visual as failure_visual
from uep_lyra_ability_progress_probe import visual as progress_visual
from uep_lyra_hud.hud_initialization_contract import require, validate
from uep_lyra_hud.weapon_observer import valid


def action_visual(widget):
    return dict(duration=float(widget.Duration),started=float(widget.StartTime),charging=bool(widget.Charging),
        disabled=bool(widget.get_property('isDisabled')),materials={image:{
            field:float(action.material(widget,image).call_function('K2_GetScalarParameterValue',field))
            for field in ('Animate_Cooldown','Animate_ActiveToInactive','Animate_FromEmpty')}
            for image in ('WeaponCard','ItemGlow')})


SPECS = (
    ('action-base', action.CLASS, action, '_uep_action_scope', action.PROXY, action_visual),
    ('action-mobile', action.MOBILE_CLASS, action, '_uep_action_scope', action.PROXY, action_visual),
    ('dash', dash.CLASS, dash, '_uep_dash_scope', dash.PROXY, dash_visual),
    ('failure', failure.CLASS, failure, '_uep_failure_scope', 'UEPOriginalFailureProxy', failure_visual),
    ('progress', progress.CLASS, progress, '_uep_progress_scope', 'UEPOriginalDurationProxy', progress_visual),
)
POLICIES = dict(action=action, dash=dash, failure=failure, progress=progress)


class Validation:
    def __init__(self, result):
        self.path,self.started,self.phase=Path(result),time.monotonic(),'ready'
        self.widgets,self.proxies,self.defaults,self.pairs,self.models=[],[],{},[],[]
        self.report=dict(status='running',error=None,pairs=self.pairs,selection_before_native_create=True,
            profile_changed_after_create=False,lifecycle_or_resume_replayed=False,
            full_acceptance=False,network_acceptance=False,packaged_runtime=False)
        ue.log('UEP_HUD_INIT_STARTED');atexit.register(self.finalize)

    def native_state(self):
        return dict(health=float(self.bridge.call_function('CaptureSnapshot').Health),
            slot=int(self.quickbar.call_function('GetActiveSlotIndex')),
            items=[v.get_path_name() if valid(v) else None for v in self.quickbar.call_function('GetSlots')])

    def restore(self, cls):
        original=self.defaults[cls];cdo=cls.get_cdo()
        cdo.set_property('PythonMixinProfile',original['profile'])
        if 'tag' in original:cdo.set_property('DurationMessageTag',GameplayTag(TagName=original['tag']))

    def current_defaults(self, cls):
        cdo=cls.get_cdo();value=dict(profile=str(cdo.get_property('PythonMixinProfile')))
        if 'DurationMessageTag' in cdo.properties():value['tag']=str(cdo.get_property('DurationMessageTag').TagName)
        return value

    def create(self, spec, profile):
        kind,path,policy,scope_name,proxy_name,visual=spec;cls=ue.load_class(path)
        if cls not in self.defaults:self.defaults[cls]=self.current_defaults(cls)
        cls.get_cdo().set_property('PythonMixinProfile',profile)
        if kind.startswith('action-'):
            cls.get_cdo().set_property('DurationMessageTag',GameplayTag(TagName='Ability.Interaction.Duration.Message'))
        before=policy.snapshot()['scopes_created']
        try:
            widget=ue.find_class('WidgetBlueprintLibrary').get_cdo().call_function('Create',self.world,cls,self.controller)
            require(valid(widget),'Native HUD Create returned null');widget.add_to_root();self.widgets.append(widget)
            scope=getattr(widget,scope_name,None);proxy=widget.get_property(proxy_name)
            if valid(proxy):self.proxies.append(proxy)
            record=dict(profile=profile,effective_profile=str(ue.get_mixin_profile(widget)),widget=widget.get_path_name(),
                **{'class':widget.get_class().get_path_name()},initial=visual(widget),
                python_scope_open=scope is not None and not scope.closed,
                original_proxy_active=valid(proxy) and bool(proxy.call_function('IsActive')),
                python_scopes_created=policy.snapshot()['scopes_created']-before)
            return widget,record
        finally:self.restore(cls)

    def ready(self):
        statics=ue.find_class('GameplayStatics').get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3,5):continue
            bridge=ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            isolate_bots(statics,world,ue.find_class('LyraPlayerBotController'));snapshot=bridge.call_function('CaptureSnapshot')
            if not(snapshot.bExperienceLoaded and snapshot.bHealthReady and not snapshot.bDamageImmune):continue
            controller=statics.call_function('GetPlayerController',world,0)
            quickbar=controller.get_component_by_type(ue.find_class('LyraQuickBarComponent')) if valid(controller) else None
            if not valid(quickbar):continue
            self.world,self.controller,self.bridge,self.quickbar=world,controller,bridge,quickbar
            self.player_before=self.native_state();self.active_before={k:p.snapshot()['active_count'] for k,p in POLICIES.items()}
            for spec in SPECS:
                values=[self.create(spec,p) for p in ('BlueprintFallback','Python')]
                pair=dict(kind=spec[0],**{'class':spec[1]},creations=[v[1] for v in values])
                require(pair['creations'][0]['initial']==pair['creations'][1]['initial'],'Native initial HUD state differs: '+spec[0])
                for widget,_ in values:widget.AddToViewport(450);widget.call_function('SetRenderOpacity',0.0)
                self.pairs.append(pair);self.models.append((spec[-1],[v[0] for v in values]))
            self.phase,self.phase_started='mounted',time.monotonic();return

    def cleanup(self):
        for cls in self.defaults:self.restore(cls)
        for widget in self.widgets:
            if valid(widget):widget.RemoveFromParent();ue.clear_mixin_profile(widget);widget.remove_from_root()
        self.report.update(defaults_restored=all(self.current_defaults(c)==v for c,v in self.defaults.items()),
            released_roots=sum(not w.is_rooted() for w in self.widgets),
            inactive_original_proxies=sum(not valid(p) or not p.call_function('IsActive') for p in self.proxies),
            native_player_state_unchanged=self.native_state()==self.player_before,
            owned_cleanup=[dict(policy=k,active_before=self.active_before[k],active_after=p.snapshot()['active_count']) for k,p in POLICIES.items()])

    def finish(self,error=None):
        try:
            if hasattr(self,'active_before'):self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error,elapsed_seconds=time.monotonic()-self.started)
        atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_HUD_INIT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def tick(self,delta):
        try:
            require(time.monotonic()-self.started<180,'Independent HUD initialization timeout')
            if self.phase=='ready':self.ready();return True
            if time.monotonic()-self.phase_started<2:return True
            for pair,(visual,widgets) in zip(self.pairs,self.models):
                pair['mounted']=[visual(w) for w in widgets]
                require(pair['mounted'][0]==pair['mounted'][1],'Native mounted HUD state differs: '+pair['kind'])
            self.finish();return False
        except Exception:self.finish(traceback.format_exc());return False

    def finalize(self):
        self.report['shutdown']={k:p.snapshot() for k,p in POLICIES.items()}
        if self.report['status']=='awaiting_shutdown':self.report['status']='passed'
        try:validate(self.report)
        except Exception:self.report.update(status='failed',error=(self.report.get('error') or '')+traceback.format_exc())
        atomic_write(self.path,self.report)
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HUD_INIT_SHUTDOWN_'+self.report['status'].upper())


result=next((a.split('=',1)[1] for a in sys.argv if a.startswith('-UEPHUDInitializationResult=')),None)
if not result:raise RuntimeError('Explicit HUD initialization result flag required')
_validation=Validation(result);_ticker=ue.add_ticker(_validation.tick,0.0)
