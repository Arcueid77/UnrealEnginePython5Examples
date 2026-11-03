"""Opt-in packaged GPU frame/CPU comparison; never controls the desktop."""
import atexit
import math
import os
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_native import global_policy, rule_policies, world_policies


def arg(key, default=None):
    return next((v.split('=', 1)[1] for v in sys.argv if v.startswith('-'+key+'=')), default)


def require(value, message):
    if not value:
        raise RuntimeError(message)


class Comparison:
    def __init__(self):
        require('-NullRHI' not in sys.argv and '-RenderOffscreen' in sys.argv, 'actual offscreen rendering required')
        self.output = Path(arg('UEPPerfResult'))
        self.prefix = arg('UEPPerfPrefix')
        self.pilot = '-UEPPerfPilot' in sys.argv
        self.warmup = float(arg('UEPPerfWarmup', '45'))
        self.duration = float(arg('UEPPerfSeconds', '20'))
        self.settle = 3. if self.pilot else 5.
        order = ('Native', 'Python', 'Python', 'Native', 'Python', 'Native', 'Native', 'Python')
        self.plan = [(work, requests, profile) for work, requests in
                     ([('Scene', 0)] if self.pilot else [('Scene', 0), ('RuleStress', 200)])
                     for profile in (order[:4] if self.pilot else order)]
        self.started = time.monotonic()
        self.phase = 'ready'
        self.index = -1
        self.finished = False
        self.capturing = False
        self.last_write = 0.
        self.statics = ue.find_class('GameplayStatics').get_cdo()
        self.report = dict(schema_version=1, status='running', error=None, pilot=self.pilot,
            physical_input_tested=False, actual_rendering_requested=True, blueprint_layer_fixed='Python',
            comparison_scope='NativeGameplayFallback versus Python on the shared native world policy carrier; other Blueprint/native mixins remain fixed',
            logical_processors=os.cpu_count(), warmup_seconds=self.warmup, capture_seconds=self.duration,
            settle_seconds=self.settle, blocks=[], phase=self.phase)
        self.write()

    def write(self):
        self.report.update(phase=self.phase, elapsed_seconds=time.monotonic()-self.started)
        atomic_write(self.output, self.report)
        self.last_write = time.monotonic()

    def command(self, text):
        ue.find_class('KismetSystemLibrary').get_cdo().call_function('ExecuteConsoleCommand', self.world, text, self.controller)

    def counters(self):
        return dict(native_admissions=global_policy.metrics(self.host)['native_routes'],
            rule_applications=sum(rule_policies.metrics(self.host)['applied'].values()),
            world_applications=sum(world_policies.metrics(self.host)['applied'].values()),
            camera_choices=world_policies.metrics(self.host)['camera_choices'],
            pawn_choices=rule_policies.metrics(self.host)['object_choices'])

    def settings(self):
        return {name: (ue.IConsoleManager.get_float(name) if ue.IConsoleManager.is_variable_float(name)
                       else float(ue.IConsoleManager.get_int(name))) for name in self.expected_cvars}

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3) or 'L_Expanse' not in world.get_name():
                continue
            bridge = ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld', world)
            if not valid(bridge):
                continue
            snap = bridge.call_function('CaptureSnapshot')
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health > 0 and not snap.bDamageImmune):
                continue
            self.world = world
            self.controller = self.statics.call_function('GetPlayerController', world, 0)
            self.pawn = self.controller.get_controlled_pawn()
            self.state = self.controller.PlayerState
            self.host = ue.find_class('UEPNativeGameplayPolicySubsystem').get_cdo().call_function('GetPolicyForContext', world)
            self.original = str(ue.get_mixin_profile(self.host))
            self.fixture = ue.find_class('UEPNativeRuleFixture').get_cdo()
            self.teams = ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem', world, ue.find_class('LyraTeamSubsystem'))
            self.game_mode = self.statics.call_function('GetGameMode', world)
            self.expected_data = self.fixture.call_function('PawnData', self.game_mode, self.controller).get_path_name()
            self.pawn_path = self.pawn.get_path_name()
            self.report['bot_isolation'] = isolate_bots(self.statics, world, ue.find_class('AIController'))
            require(len(self.report['bot_isolation']) == 3 and all(not r['running'] for r in self.report['bot_isolation']), 'three stable noncombat AI owners required')
            self.report['viewport'] = list(ue.get_viewport_size())
            require(self.report['viewport'] == [1920, 1080], 'fixed 1920x1080 viewport required')
            values = [('r.VSync', 0), ('t.MaxFPS', 0), ('t.IdleWhenNotForeground', 0), ('r.ScreenPercentage', 100)]
            values += [(name, 1) for name in ('sg.ViewDistanceQuality', 'sg.AntiAliasingQuality', 'sg.ShadowQuality', 'sg.GlobalIlluminationQuality', 'sg.ReflectionQuality', 'sg.PostProcessQuality', 'sg.TextureQuality', 'sg.EffectsQuality', 'sg.FoliageQuality', 'sg.ShadingQuality')]
            self.command('Slate.bAllowThrottling 0')
            for name, value in values:
                self.command(name+' '+str(value))
            self.expected_cvars = {name: value for name, value in values}
            self.report['settings'] = self.settings()
            for key, expected in self.expected_cvars.items():
                require(math.isclose(self.report['settings'][key], expected, abs_tol=.001), 'fixed rendering setting differs: '+key)
            self.until = time.monotonic()+self.warmup
            self.phase = 'warmup'
            self.write()
            return

    def select(self, name):
        ue.set_mixin_profile(self.host, 'NativeGameplayFallback' if name == 'Native' else 'Python')

    def begin_settle(self):
        self.index += 1
        if self.index == len(self.plan):
            self.finish()
            return
        self.workload, self.requests, self.profile = self.plan[self.index]
        self.select(self.profile)
        ue.find_class('KismetSystemLibrary').get_cdo().call_function('CollectGarbage')
        self.until = time.monotonic()+self.settle
        self.phase = 'settle'
        self.write()

    def begin_capture(self):
        self.row = dict(index=self.index, workload=self.workload, requests_per_frame=self.requests, profile=self.profile,
            selected_profile=str(ue.get_mixin_profile(self.host)), csv_basename=self.prefix+'_%02d_%s_%s.csv' % (self.index, self.workload, self.profile),
            frames=0, query_pairs=0, before_counters=self.counters(), pawn=self.pawn_path,
            settings=self.settings())
        require(self.row['settings'] == self.report['settings'], 'rendering settings drifted')
        self.command('CsvProfile STARTFILE='+self.row['csv_basename'])
        self.command('CsvProfile START')
        self.capture_started = time.monotonic()
        self.row['started_unix_ms'] = time.time_ns()/1e6
        self.cpu_started = time.process_time_ns()
        self.until = self.capture_started+self.duration
        self.capturing = True
        self.phase = 'capture'
        self.write()

    def queries(self, count):
        for _ in range(count//2):
            require(self.fixture.call_function('DamageAllowed', self.teams, self.pawn, self.pawn, True), 'native self-damage admission changed')
            require(self.fixture.call_function('PawnData', self.game_mode, self.controller).get_path_name() == self.expected_data, 'native Pawn data result changed')

    def end_capture(self):
        ended, cpu = time.monotonic(), time.process_time_ns()
        self.command('CsvProfile STOP')
        self.capturing = False
        self.row.update(wall_seconds=ended-self.capture_started, process_cpu_seconds=(cpu-self.cpu_started)/1e9,
            ended_unix_ms=time.time_ns()/1e6,
            after_counters=self.counters(), owner_pawn_unchanged=self.controller.get_controlled_pawn().get_path_name() == self.pawn_path)
        self.row['cpu_machine_percent'] = 100*self.row['process_cpu_seconds']/self.row['wall_seconds']/os.cpu_count()
        require(self.row['owner_pawn_unchanged'], 'fixed scene owner respawned')
        self.report['blocks'].append(self.row)
        # Give the independent native CSV writer time to close outside sampling.
        self.phase = 'flush'
        self.until = time.monotonic()+2.
        self.write()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < (360 if self.pilot else 900), 'rendered performance deadline exceeded')
            now = time.monotonic()
            if self.phase == 'ready':
                self.ready()
            elif self.phase == 'warmup':
                self.select(('Native', 'Python')[int(now-self.started)//3 % 2])
                self.queries(20)
                if now >= self.until:
                    self.begin_settle()
            elif self.phase == 'settle':
                self.queries(self.requests)
                if now >= self.until:
                    self.begin_capture()
            elif self.phase == 'capture':
                if now >= self.until:
                    self.end_capture()
                else:
                    self.queries(self.requests)
                    self.row['frames'] += 1
                    self.row['query_pairs'] += self.requests//2
            elif self.phase == 'flush' and now >= self.until:
                self.begin_settle()
            if now-self.last_write >= 2.:
                self.write()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            if self.capturing:
                self.command('CsvProfile STOP')
            if hasattr(self, 'host') and valid(self.host):
                ue.set_mixin_profile(self.host, self.original)
                self.report['selector_restored'] = str(ue.get_mixin_profile(self.host)) == self.original
        except Exception:
            error = (error or '')+traceback.format_exc()
        self.phase = 'shutdown'
        self.report.update(status='failed' if error else 'awaiting_shutdown', error=error)
        self.write()
        (ue.log_error if error else ue.log)('UEP_RENDERED_PERFORMANCE_'+('FAILED '+error if error else 'READY'))
        ue.request_exit()

    def finalize(self):
        if self.report['status'] == 'awaiting_shutdown':
            self.report['status'] = 'passed'
        self.write()
        (ue.log if self.report['status'] == 'passed' else ue.log_error)('UEP_RENDERED_PERFORMANCE_SHUTDOWN_'+self.report['status'].upper())


comparison = Comparison()
atexit.register(comparison.finalize)
ticker = ue.add_ticker(comparison.tick)
