"""Observe normal actual-player AnimBP notifications while injecting native input."""
import atexit, copy, math, sys, time, traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.enums import ETraceTypeQuery, EDrawDebugTrace
from uep_lyra_network_io import read_json, atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_abilities.melee_trace_mixin import native_outputs, break_hit
from uep_lyra_characters import hero_default_motion_mixin as parent_policy
from .footstep_animation_validation import Validation as Animation, vec, path, close
from .weapon_fire_fx_validation import parameter
from . import footstep_mixin as policy
from .footstep_locomotion_contract import PLAN, FALSE_FIELDS, require, validate


def arg(name):
    return next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-'+name+'='))


class Validation(Animation):
    def __init__(self, result):
        super().__init__(result)
        self.report = dict(status='running', error=None, role=self.role, run_id=self.run, cases=[])
        self.report.update(dict.fromkeys(FALSE_FIELDS, False))
        self.requested_profile = arg('UEPFootstepLocomotionProfile')
        self.plan = [row for row in PLAN if row[0] == self.requested_profile]
        self.boot_selectors = []
        for class_path in (parent_policy.CLASS, '/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin_C'):
            cls = ue.load_class(class_path)
            for selector in (parent_policy.SELECTOR, 'PythonMixinProfile'):
                if selector in cls.get_cdo().properties():
                    self.boot_selectors.append((cls, selector, cls.get_cdo().get_property(selector)))
                    cls.get_cdo().set_property(selector, self.requested_profile)
        self.report.update(requested_profile=self.requested_profile, profile_selected_before_player_creation=True)
        self.input = None
        self.target = None
        self.player_profiles = []
        self.input_vectors = 0

    def begin(self):
        super().begin()
        self.current = None
        self.anim_mode = int(self.pawn.get_property('Mesh').call_function('GetAnimationMode'))
        self.anim_class = path(self.pawn.get_property('Mesh').call_function('GetAnimInstance').get_class())
        self.original_control = self.controller.call_function('GetControlRotation')
        self.player_id = int(self.controller.get_property('PlayerState').get_property('PlayerId'))
        self.instance_profile = str(ue.get_mixin_profile(self.pawn))
        self.parent_instance_selector = self.pawn.get_property(parent_policy.SELECTOR)
        if self.role == 'client':
            self.target = self.pawn
            self.target_controller = self.controller
            self.input = policy.lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubsystem', self.controller, ue.find_class('EnhancedInputLocalPlayerSubsystem'))
            self.action = ue.load_object(ue.find_class('InputAction'), '/Game/Input/Actions/IA_Move.IA_Move')
            require(valid(self.input), 'actual owner EnhancedInput subsystem required')
            self.root_object(self.action)
            self.choose_corridor()
            atomic_write(self.root/'locomotion-owner.json', dict(run_id=self.run, player_id=self.player_id))
            self.enter('request')
        else:
            self.enter('server-wait')

    def input_value(self, value):
        self.input.call_function('InjectInputVectorForAction', self.action, ue.FVector(0., value, 0.))
        self.input_vectors += 1

    def trace(self, start, end):
        value = policy.lib('KismetSystemLibrary').call_function('LineTraceSingle', WorldContextObject=self.world,
            Start=start, End=end, TraceChannel=ETraceTypeQuery.TraceTypeQuery1, bTraceComplex=False,
            ActorsToIgnore=[self.pawn], DrawDebugType=getattr(EDrawDebugTrace, 'None'), bIgnoreSelf=True,
            TraceColor=ue.FLinearColor(1., 0., 0., 1.), TraceHitColor=ue.FLinearColor(0., 1., 0., 1.), DrawTime=0.)
        return native_outputs('KismetSystemLibrary', 'LineTraceSingle', value)

    def choose_corridor(self):
        origin = self.pawn.call_function('K2_GetActorLocation')
        half = float(self.pawn.get_property('CapsuleComponent').call_function('GetScaledCapsuleHalfHeight'))
        base_yaw = float(self.original_control.yaw)
        for offset in (0., 90., -90., 180., 45., -45., 135., -135.):
            yaw = base_yaw+offset;rad = math.radians(yaw);x, y = math.cos(rad), math.sin(rad)
            clear = True
            for distance in range(100, 801, 100):
                point = ue.FVector(origin.x+x*distance, origin.y+y*distance, origin.z)
                floor = self.trace(ue.FVector(point.x, point.y, point.z+30.), ue.FVector(point.x, point.y, point.z-200.))
                if not floor['ReturnValue'] or abs(float(break_hit(floor['OutHit'])['Location'].z)-(origin.z-half)) > 20.:
                    clear = False;break
                if self.trace(origin, point)['ReturnValue']:
                    clear = False;break
            if clear:
                rotation = policy.lib('KismetMathLibrary').call_function('MakeRotator', Roll=0., Pitch=0., Yaw=yaw)
                self.controller.call_function('SetControlRotation', rotation)
                self.report['selected_original_floor_corridor_yaw'] = yaw
                return
        raise RuntimeError('no unchanged original floor corridor long enough for locomotion trials')

    def select_target(self, pawn, controller, profile):
        if not any(entry[0] == pawn for entry in self.player_profiles):
            self.player_profiles.append((pawn, str(ue.get_mixin_profile(pawn)), pawn.get_property(parent_policy.SELECTOR)))
        ue.set_mixin_profile(pawn, profile)
        pawn.set_property(parent_policy.SELECTOR, profile)
        self.foot_cls.get_cdo().set_property('PythonMixinProfile', profile)
        foot = pawn.get_property('FootStep')
        if valid(foot):
            ue.set_mixin_profile(foot, profile)
        mesh = pawn.get_property('Mesh')
        return dict(actor=pawn, controller=controller, mesh=mesh, profile=profile, parent=[], foot=[], foot_paths=set(), delays=[],
                    started=self.game_time(), start_location=vec(pawn.call_function('K2_GetActorLocation')),
                    pawn_path=path(pawn), player_id=int(controller.get_property('PlayerState').get_property('PlayerId')),
                    anim_class=path(mesh.call_function('GetAnimInstance').get_class()), maximum_speed=0.)

    def motion(self, actor, args, handler, profile, route):
        current = self.current
        owned = current is not None and ((route == 'parent' and actor == current['actor']) or
            (route == 'foot' and actor.get_property('Skeletal Mesh Component') == current['mesh']))
        if not owned:
            return handler(actor, *args)
        bone, tag, mesh, offset, rotation, animation, hit, result, contexts, scale, volume, pitch = args
        sample = dict(profile=profile, bone=str(bone), sequence=path(animation), hit=bool(hit), tag=str(tag.TagName))
        if route == 'foot':
            current['foot_paths'].add(actor.get_path_name())
            self.remember_actor(actor)
            detail = break_hit(result)
            sample.update(location=vec(detail['Location']), normal=vec(detail['Normal']), hit_actor=path(detail['HitActor']))
            before = self.footprint_state(actor)
        returned = handler(actor, *args)
        if route == 'foot':
            sample['fields_match'] = not hit or close(vec(actor.get_property('FootStepHitLocation')), sample['location']) and close(vec(actor.get_property('FootStepHitNormal')), sample['normal'])
            sample['miss_preserved'] = bool(hit) or self.footprint_state(actor) == before
            component = actor.get_property('NS_FootPrint')
            sample['parameters_valid'] = bool(hit) and valid(component)
            sample['parameters_match'] = not hit or valid(component) and close(parameter(component, 'User.StepLocation', '<3f'), sample['location']) and bool(parameter(component, 'User.Trigger', '<i')[0]) == bool(actor.get_property('FootPrintTrigger'))
        current[route].append(sample)
        return returned

    def footprint_state(self, actor):
        component = actor.get_property('NS_FootPrint')
        state = dict(location=vec(actor.get_property('FootStepHitLocation')), normal=vec(actor.get_property('FootStepHitNormal')),
            trigger=bool(actor.get_property('FootPrintTrigger')), side=bool(actor.get_property('FootStepSide')),
            socket=str(actor.get_property('CurrentSocket')), surface=int(actor.get_property('FootStepSurfaceType')),
            surface_niagara=int(actor.get_property('FootStepSurfaceTypeNiagara')), component=path(component))
        if valid(component):
            state['parameters'] = {name: parameter(component, name, fmt) for name, fmt in (
                ('User.StepLocation', '<3f'), ('User.Orientation', '<4f'), ('User.Trigger', '<i'), ('User.StepSide', '<i'), ('User.SurfaceType', '<i'))}
        return state

    def request(self):
        if self.index == len(self.plan):
            atomic_write(self.root/'locomotion-done.json', dict(run_id=self.run))
            self.complete()
            return
        profile, name = self.plan[self.index]
        self.current = self.select_target(self.pawn, self.controller, profile)
        self.current.update(name=name, value=(.35 if name.startswith('walk') else 1.)*(-1. if name.endswith('back') else 1.), duration=1.8 if name.startswith('walk') else 1.1)
        atomic_write(self.root/'locomotion-case.json', dict(run_id=self.run, index=self.index, profile=profile, name=name, player_id=self.player_id))
        self.enter('await-server')

    def observe_client(self):
        if self.phase == 'request':
            self.request();return
        if self.phase == 'await-server':
            ack = read_json(self.root/'locomotion-server-ready.json')
            if ack and ack.get('run_id') == self.run and ack.get('index') == self.index:
                self.current['started'] = self.game_time()
                self.enter('moving')
            return
        current = self.current
        speed = current['actor'].call_function('GetVelocity').size()
        current['maximum_speed'] = max(current['maximum_speed'], float(speed))
        if self.phase == 'moving':
            self.input_value(current['value'])
            if self.game_time()-current['started'] >= current['duration']:
                self.input_value(0.)
                self.enter('stopping')
            return
        self.input_value(0.)
        if self.game_time()-current['started'] < current['duration']+.4 or speed > 5.:
            require(self.game_time()-current['started'] < current['duration']+5., 'native movement did not stop after input release')
            return
        row = self.row(current)
        self.report['cases'].append(row)
        atomic_write(self.root/'locomotion-case-ended.json', dict(run_id=self.run, index=self.index))
        self.enter('await-server-end')

    def row(self, current):
        pawn = current['actor'];position = vec(pawn.call_function('K2_GetActorLocation'))
        foot, parent = current['foot'], current['parent']
        return dict(profile=current['profile'], name=current['name'], input_entry='EnhancedInputLocalPlayerSubsystem.InjectInputVectorForAction',
            same_real_player_identity=int(current['controller'].get_property('PlayerState').get_property('PlayerId')) == current['player_id'],
            same_native_pawn=path(current['controller'].get_controlled_pawn()) == current['pawn_path'],
            native_animation_class_preserved=path(current['mesh'].call_function('GetAnimInstance').get_class()) == current['anim_class'] and int(current['mesh'].call_function('GetAnimationMode')) == 0,
            native_movement_distance=math.dist(position, current['start_location']), maximum_speed=current['maximum_speed'],
            stopped_after_release=float(pawn.call_function('GetVelocity').size()) <= 5., parent_calls=len(parent), native_footstep_actor_calls=len(foot),
            actual_animation_sequence_observed=bool(parent) and all(sample['sequence'] and '/Animations/' in sample['sequence'] for sample in parent),
            only_selected_profile_called=all(sample['profile'] == current['profile'] for sample in parent+foot),
            successful_hits=sum(bool(sample['hit']) and bool(sample['hit_actor']) for sample in foot),
            misses_preserve_original_state=all(sample['miss_preserved'] for sample in foot),
            all_fields_match_native_hit=bool(foot) and all(sample['fields_match'] for sample in foot),
            niagara_samples=sum(sample['parameters_valid'] for sample in foot), all_parameters_match=all(sample['parameters_match'] for sample in foot if sample['parameters_valid']),
            native_motion_samples=copy.deepcopy(foot))

    def observe_server(self):
        done = read_json(self.root/'locomotion-done.json')
        if done and done.get('run_id') == self.run:
            self.complete();return
        request = read_json(self.root/'locomotion-case.json')
        if not request or request.get('run_id') != self.run:
            return
        index = request['index']
        if self.current is None or self.current.get('index') != index:
            controllers = native_outputs('GameplayStatics', 'GetAllActorsOfClass', self.statics.call_function('GetAllActorsOfClass', self.world, ue.find_class('PlayerController')))['OutActors']
            controller = next((c for c in controllers if int(c.get_property('PlayerState').get_property('PlayerId')) == request['player_id']), None)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):
                return
            self.target_controller, self.target = controller, controller.get_controlled_pawn()
            self.current = self.select_target(self.target, controller, request['profile'])
            self.current.update(index=index, name=request['name'])
            atomic_write(self.root/'locomotion-server-ready.json', dict(run_id=self.run, index=index))
        current = self.current
        current['maximum_speed'] = max(current['maximum_speed'], float(current['actor'].call_function('GetVelocity').size()))
        ended = read_json(self.root/'locomotion-case-ended.json')
        if ended and ended.get('run_id') == self.run and ended.get('index') == index and not current.get('recorded'):
            if float(current['actor'].call_function('GetVelocity').size()) > 5.:
                return
            self.report['cases'].append(self.row(current));current['recorded'] = True
            atomic_write(self.root/'locomotion-server-ended.json', dict(run_id=self.run, index=index))

    def cleanup(self):
        if self.cleaned:
            return
        self.cleaned = True
        if valid(self.input):
            self.input_value(0.)
            self.controller.call_function('SetControlRotation', self.original_control)
        self.current = None
        for pawn, previous, selector in self.player_profiles:
            ue.set_mixin_profile(pawn, previous);pawn.set_property(parent_policy.SELECTOR, selector)
            foot = pawn.get_property('FootStep')
            if valid(foot):
                ue.clear_mixin_profile(foot)
        for kind, (cls, profiles) in self.classes_before.items():
            for profile, source in profiles.items():
                ue.register_mixin_profile(cls, profile, source)
        self.foot_cls.get_cdo().set_property('PythonMixinProfile', self.foot_selector)
        self.parent_cls.get_cdo().set_property(parent_policy.SELECTOR, self.parent_selector)
        for cls, selector, previous in reversed(self.boot_selectors):
            cls.get_cdo().set_property(selector, previous)
        for obj in reversed(self.roots):
            obj.remove_from_root()
        self.report['inventory_and_health_unchanged'] = capture(self.controller) == self.player_before and self.healths() == self.health_before
        mesh = self.pawn.get_property('Mesh')
        self.report['original_animation_class_and_mode_preserved'] = int(mesh.call_function('GetAnimationMode')) == self.anim_mode and path(mesh.call_function('GetAnimInstance').get_class()) == self.anim_class
        self.report['input_released'] = self.role == 'server' or valid(self.input)
        self.report['profiles_selectors_roots_and_observers_restored'] = all(str(ue.get_mixin_profile(pawn)) == previous and pawn.get_property(parent_policy.SELECTOR) == selector for pawn, previous, selector in self.player_profiles) and all(not obj.is_rooted() for obj in self.roots) and all(next(row for row in ue.get_registered_mixins() if row['target_class'] == cls)['profiles'][profile]['python_class'] is source for cls, profiles in self.classes_before.values() for profile, source in profiles.items())

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 360., 'normal locomotion timed out: '+self.phase)
            if self.phase == 'ready':
                self.ready()
            elif self.phase == 'release':
                release = read_json(self.root/'release.json')
                if release and release.get('run_id') == self.run:
                    self.finish()
            elif self.role == 'server':
                self.observe_server()
            elif self.phase == 'await-server-end':
                ack = read_json(self.root/'locomotion-server-ended.json')
                if ack and ack.get('run_id') == self.run and ack.get('index') == self.index:
                    self.index += 1;self.enter('request')
            else:
                self.observe_client()
            self.report.update(phase=self.phase, current_case=self.index)
            if self.current is not None:
                self.report['current_observation'] = dict(parent_calls=len(self.current['parent']), footstep_calls=len(self.current['foot']), maximum_speed=self.current['maximum_speed'])
            self.write()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc());return False

    def finalize(self):
        if self.report['status'] == 'awaiting_shutdown':
            try:
                self.report['status'] = 'passed';validate(self.report)
            except Exception:
                self.report.update(status='failed', error=traceback.format_exc())
        self.write()
        (ue.log if self.report['status'] == 'passed' else ue.log_error)('UEP_FOOTSTEP_LOCOMOTION_SHUTDOWN_'+self.report['status'].upper())

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.cleanup()
        except Exception:
            error = (error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown', error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_FOOTSTEP_LOCOMOTION_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()


result = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPFootstepLocomotionResult=')), None)
if result:
    validation = Validation(result);atexit.register(validation.finalize);ticker = ue.add_ticker(validation.tick)
