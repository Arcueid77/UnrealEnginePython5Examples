"""Explicit startup-import fixture; compare native OnInitialized on both Profiles."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_network_io import atomic_write
from uep_lyra_hud import quickbar_slot_mixin as policy
from uep_lyra_hud.quickbar_slot_validation import visual
from uep_lyra_hud.quickbar_initialization_contract import PROFILES, require, validate
from uep_lyra_hud.weapon_observer import valid


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), 'ready'
        self.widgets, self.original_proxies, self.pairs = [], [], []
        self.original_defaults = None
        ue.log('UEP_QUICKBAR_INIT_STARTED')
        self.report = dict(status='running', error=None, pairs=self.pairs,
            profile_selected_before_native_create=True, native_create_api='WidgetBlueprintLibrary.Create',
            native_initialization_parity_tested=True, lifecycle_event_replayed=False,
            profile_changed_after_create=False, resume_entry_called=False, native_player_state_written=False,
            full_acceptance=False, network_acceptance=False, packaged_runtime=False)
        atexit.register(self.finalize)

    def fingerprint(self):
        return dict(active=int(self.quickbar.call_function('GetActiveSlotIndex')),
            slots=[v.get_path_name() if valid(v) else None for v in self.quickbar.call_function('GetSlots')],
            health=float(self.bridge.call_function('CaptureSnapshot').Health))

    def defaults(self):
        cdo = self.cls.get_cdo()
        return (str(cdo.get_property('PythonMixinProfile')), int(cdo.SlotIndex))

    def restore_defaults(self):
        if self.original_defaults is not None:
            self.cls.get_cdo().set_property('PythonMixinProfile', self.original_defaults[0])
            self.cls.get_cdo().set_property('SlotIndex', self.original_defaults[1])

    def create(self, index, profile):
        self.cls.get_cdo().set_property('PythonMixinProfile', profile)
        self.cls.get_cdo().set_property('SlotIndex', index)
        before = policy.snapshot()
        try:
            widget = ue.find_class('WidgetBlueprintLibrary').get_cdo().call_function(
                'Create', self.world, self.cls, self.controller)
            require(valid(widget), 'Native quickbar Create returned null')
            widget.add_to_root(); self.widgets.append(widget)
            after = policy.snapshot()
            proxies = [getattr(widget, row[3]) for row in policy.ROWS]
            self.original_proxies.extend(p for p in proxies if valid(p))
            scope = getattr(widget, '_uep_slot_scope', None)
            record = dict(profile=profile, selected_before_create=True,
                effective_profile=str(ue.get_mixin_profile(widget)), widget=widget.get_path_name(),
                **{'class':widget.get_class().get_path_name()}, initial=visual(widget),
                python_scope_open=scope is not None and not scope.closed,
                original_proxy_active=[valid(p) and bool(p.call_function('IsActive')) for p in proxies],
                python_counter_delta={k:after[k]-before[k] for k in ('slot_updates', 'scopes_created')})
            return widget, record
        finally:
            self.restore_defaults()

    def ready(self):
        statics = ue.find_class('GameplayStatics').get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5):continue
            bridge = ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld', world)
            if not valid(bridge):continue
            isolate_bots(statics, world, ue.find_class('LyraPlayerBotController'))
            snapshot = bridge.call_function('CaptureSnapshot')
            if not (snapshot.bExperienceLoaded and snapshot.bHealthReady and not snapshot.bDamageImmune):continue
            controller = statics.call_function('GetPlayerController', world, 0)
            quickbar = controller.get_component_by_type(ue.find_class('LyraQuickBarComponent')) if valid(controller) else None
            if not valid(quickbar):continue
            entries = list(quickbar.call_function('GetSlots'))
            if len(entries) != 3 or not valid(entries[0]) or any(valid(v) for v in entries[1:]):continue
            self.world, self.controller, self.quickbar, self.bridge = world, controller, quickbar, bridge
            self.cls = ue.load_class(policy.CLASS); self.original_defaults = self.defaults()
            self.native_before = self.fingerprint(); self.active_before = policy.snapshot()['active_count']
            self.mounted = []
            for index in range(3):
                values = [self.create(index, profile) for profile in PROFILES]
                pair = dict(slot_index=index, creations=[v[1] for v in values],
                    initial_states_equal=values[0][1]['initial'] == values[1][1]['initial'])
                require(pair['initial_states_equal'], 'Original/Python native OnInitialized differs')
                for widget, _ in values:
                    widget.AddToViewport(450); widget.call_function('SetRenderOpacity', 0.0)
                self.mounted.append([v[0] for v in values]); self.pairs.append(pair)
            self.phase, self.phase_started = 'mounted', time.monotonic()
            return

    def cleanup(self):
        self.restore_defaults()
        for widget in self.widgets:
            if valid(widget):
                widget.RemoveFromParent(); ue.clear_mixin_profile(widget); widget.remove_from_root()
        return dict(python_active_before=self.active_before, python_active_after=policy.snapshot()['active_count'],
            original_proxies_inactive=sum(not valid(p) or not p.call_function('IsActive') for p in self.original_proxies),
            released_roots=sum(not w.is_rooted() for w in self.widgets))

    def finish(self, error=None):
        try:
            if hasattr(self, 'active_before'):
                self.report['owned_cleanup'] = self.cleanup()
                self.report.update(original_defaults_restored=self.defaults() == self.original_defaults,
                    test_roots_released=all(not w.is_rooted() for w in self.widgets),
                    owned_widgets_removed=all(not w.call_function('IsInViewport') for w in self.widgets),
                    native_player_state_unchanged=self.fingerprint() == self.native_before)
        except Exception:
            error = (error or '') + traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown', error=error,
            elapsed_seconds=time.monotonic()-self.started)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)('UEP_QUICKBAR_INIT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def tick(self, delta):
        try:
            require(time.monotonic()-self.started < 180, 'Native quickbar initialization timeout')
            if self.phase == 'ready':self.ready(); return True
            if time.monotonic()-self.phase_started < 2:return True
            for pair, widgets in zip(self.pairs, self.mounted):
                pair['mounted'] = [visual(w) for w in widgets]
                pair['mounted_states_equal'] = pair['mounted'][0] == pair['mounted'][1]
                require(pair['mounted_states_equal'], 'Native initialized/mounted slot state differs')
            self.finish(); return False
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finalize(self):
        self.report['shutdown'] = policy.snapshot()
        if self.report['status'] == 'awaiting_shutdown':self.report['status'] = 'passed'
        try:validate(self.report)
        except Exception:
            self.report.update(status='failed', error=(self.report.get('error') or '')+traceback.format_exc())
        atomic_write(self.path, self.report)
        (ue.log if self.report['status'] == 'passed' else ue.log_error)(
            'UEP_QUICKBAR_INIT_SHUTDOWN_'+self.report['status'].upper())


result = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('-UEPQuickBarInitializationResult=')), None)
if not result:raise RuntimeError('Explicit quickbar initialization result is required for the test import')
_validation = Validation(result)
_ticker = ue.add_ticker(_validation.tick, 0.0)
