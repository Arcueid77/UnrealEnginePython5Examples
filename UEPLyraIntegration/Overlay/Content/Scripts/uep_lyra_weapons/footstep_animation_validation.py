"""Unchanged animations run in native single-node playback; no notify replay."""
import atexit, copy, hashlib, sys, time, traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_network_io import read_json, atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_characters.hero_parent_test_profiles import defaults
from uep_lyra_characters.hero_default_ragdoll_validation import primary_state
from uep_lyra_characters import hero_default_motion_mixin as parent_policy
from .hero_burst_cue_validation import Validation as Ready
from .weapon_fire_fx_validation import parameter
from . import footstep_mixin as policy
from .footstep_animation_contract import FALSE_FIELDS, validate, require
from uep_lyra_abilities.melee_trace_mixin import break_hit


def arg(name):
    return next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def dead(actor):
    return not valid(actor) or bool(actor.call_function('IsActorBeingDestroyed'))


def path(obj):
    return obj.get_path_name() if valid(obj) else None


def vec(value):
    return [float(value.x), float(value.y), float(value.z)]


def close(left, right, tolerance=.001):
    return len(left) == len(right) and all(abs(a-b) <= tolerance for a, b in zip(left, right))


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result)
        self.role, self.run = arg('UEPFootstepAnimationRole'), arg('UEPFootstepAnimationRun')
        self.root = Path(result).parent
        self.report = dict(status='running', error=None, role=self.role, run_id=self.run, cases=[])
        self.report.update(dict.fromkeys(FALSE_FIELDS, False))
        self.actors, self.feet, self.roots, self.classes_before = [], [], [], {}
        self.current = None
        self.cleaned = False
        self.index = 0
        self.owned_counts = 0
        self.actor_paths = set()

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3):
                continue
            bridge = policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld', world)
            if not valid(bridge):
                continue
            snap = bridge.call_function('CaptureSnapshot')
            self.report['readiness'] = dict(experience=bool(snap.bExperienceLoaded), input=bool(snap.bHeroInputReady), health=float(snap.Health), health_ready=bool(snap.bHealthReady), immune=bool(snap.bDamageImmune))
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health > 0 and not snap.bDamageImmune):
                continue
            controller = self.statics.call_function('GetPlayerController', world, 0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):
                continue
            self.world, self.controller, self.pawn = world, controller, controller.get_controlled_pawn()
            self.report.update(native_mode=str(snap.NetMode), native_is_server=bool(policy.lib('KismetSystemLibrary').call_function('IsServer', world)))
            self.begin()
            return

    def root_object(self, obj):
        if not obj.is_rooted():
            obj.add_to_root();self.roots.append(obj)

    def remember_actor(self, actor):
        self.actor_paths.add(actor.get_path_name())

    def live_owned_actors(self):
        values = self.statics.call_function('GetAllActorsOfClass', self.world, ue.find_class('Actor'))
        from uep_lyra_abilities.melee_trace_mixin import native_outputs
        return {actor.get_path_name(): actor for actor in native_outputs('GameplayStatics', 'GetAllActorsOfClass', values)['OutActors'] if actor.get_path_name() in self.actor_paths}

    def begin(self):
        self.player_before, self.health_before, self.primary_before = capture(self.controller), self.healths(), primary_state(self.pawn)
        self.audit = read_json(Path(arg('UEPFootstepAnimationAudit')))
        require(self.audit and self.audit['status'] == 'passed', 'accepted original animation inventory required')
        self.parent_cls, self.foot_cls = ue.load_class(parent_policy.CLASS), ue.load_class(policy.CLASS)
        self.mesh_asset = self.pawn.get_property('Mesh').call_function('GetSkeletalMeshAsset')
        self.sequences = [ue.load_object(ue.find_class('AnimSequence'), row['package']) for row in self.audit['sequences']]
        for obj in (self.parent_cls, self.foot_cls, self.mesh_asset, *self.sequences):
            self.root_object(obj)
        self.foot_selector = self.foot_cls.get_cdo().get_property('PythonMixinProfile')
        self.parent_selector = self.parent_cls.get_cdo().get_property(parent_policy.SELECTOR)
        self.observe_profiles(self.parent_cls, 'parent')
        self.observe_profiles(self.foot_cls, 'foot')
        camera = self.statics.call_function('GetPlayerCameraManager', self.world, 0)
        location = camera.call_function('GetCameraLocation');rotation = camera.call_function('GetCameraRotation')
        forward = policy.lib('KismetMathLibrary').call_function('GetForwardVector', rotation)
        primary = self.pawn.call_function('K2_GetActorLocation')
        self.center = ue.FVector(location.x+600.*forward.x, location.y+600.*forward.y, primary.z-90.)
        self.enter('start')

    def observe_profiles(self, cls, kind):
        ue.register_declared_mixin(cls)
        binding, = [row for row in ue.get_registered_mixins() if row['target_class'] == cls]
        original = {p: row['python_class'] for p, row in binding['profiles'].items()}
        self.classes_before[kind] = (cls, original)
        owner = self
        for profile, base in original.items():
            def around(handler, selected, route):
                def invoke(actor, *args):
                    return owner.motion(actor, args, handler, selected, route)
                return invoke
            attrs = {key: value for key, value in vars(base).items() if not key.startswith('__')}
            attrs['AnimMotionEffect'] = around(base.__dict__['AnimMotionEffect'], profile, kind)
            if kind == 'foot':
                def after(handler, selected):
                    def invoke(actor):
                        if owner.current is not None and actor.get_path_name() in owner.current['foot_paths']:
                            owner.current['delays'].append(dict(time=owner.game_time(), component_valid=valid(actor.get_property('NS_FootPrint'))))
                            owner.owned_counts += 1
                        return handler(actor)
                    invoke.override = policy.AFTER
                    return invoke
                attrs['AfterDelay'] = after(base.__dict__['AfterDelay'], profile)
            ue.register_mixin_profile(cls, profile, type('NaturalAnimation'+kind+profile, (), attrs))

    def motion(self, actor, args, handler, profile, route):
        current = self.current
        owned = current is not None and ((route == 'parent' and actor == current['actor']) or
            (route == 'foot' and actor.get_property('Skeletal Mesh Component') == current['mesh']))
        if not owned:
            return handler(actor, *args)
        self.owned_counts += 1
        bone, tag, mesh, offset, rotation, animation, hit, hit_result, contexts, scale, volume, pitch = args
        sample = dict(profile=profile, bone=str(bone), sequence=path(animation), mesh_matches=mesh == current['mesh'], tag=str(tag.TagName), hit=bool(hit))
        if route == 'foot':
            self.remember_actor(actor)
            current['foot_paths'].add(actor.get_path_name())
            if actor not in self.feet:
                self.feet.append(actor)
            detail = break_hit(hit_result)
            sample['floor_matches'] = detail['HitActor'] == current['floor']
            sample['hit_location'], sample['hit_normal'] = vec(detail['Location']), vec(detail['Normal'])
            sample['trace_start'], sample['trace_end'] = vec(detail['TraceStart']), vec(detail['TraceEnd'])
        result = handler(actor, *args)
        if route == 'foot':
            sample['fields_match'] = bool(hit) and close(vec(actor.get_property('FootStepHitLocation')), sample['hit_location']) and close(vec(actor.get_property('FootStepHitNormal')), sample['hit_normal']) and str(actor.get_property('CurrentSocket')) == str(bone)+'_Socket' and bool(actor.get_property('FootStepSide')) == (str(bone).lower() == 'foot_r')
            component = actor.get_property('NS_FootPrint')
            sample['component_valid'] = valid(component)
            if valid(component):
                quat = actor.get_property('FootStepOrientation')
                sample['parameters_match'] = close(parameter(component, 'User.StepLocation', '<3f'), sample['hit_location']) and close(parameter(component, 'User.Orientation', '<4f'), [float(quat.x), float(quat.y), float(quat.z), float(quat.w)]) and bool(parameter(component, 'User.Trigger', '<i')[0]) == bool(actor.get_property('FootPrintTrigger')) and bool(parameter(component, 'User.StepSide', '<i')[0]) == bool(actor.get_property('FootStepSide')) and int(parameter(component, 'User.SurfaceType', '<i')[0]) == int(actor.get_property('FootStepSurfaceTypeNiagara'))
            else:
                sample['parameters_match'] = False
            current['last_motion'] = self.game_time()
        current[route].append(sample)
        return result

    def start_case(self):
        if self.index == 10:
            self.complete()
            return
        profile = ('BlueprintFallback', 'Python')[self.index//5]
        sequence_index = self.index % 5
        self.foot_cls.get_cdo().set_property('PythonMixinProfile', profile)
        floor = self.world.actor_spawn(ue.find_class('StaticMeshActor'), ue.FVector(self.center.x, self.center.y, self.center.z-5.))
        self.actors.append(floor)
        self.remember_actor(floor)
        floor_mesh = floor.get_component_by_type(ue.find_class('StaticMeshComponent'))
        floor_mesh.call_function('SetMobility', 2)
        floor_mesh.call_function('SetStaticMesh', ue.load_object(ue.find_class('StaticMesh'), '/Engine/BasicShapes/Cube.Cube'))
        floor_mesh.call_function('SetWorldScale3D', ue.FVector(3., 3., .1))
        floor_mesh.call_function('SetCollisionProfileName', 'BlockAll', True)
        with defaults(self.parent_cls, profile):
            actor = self.world.actor_spawn(self.parent_cls, ue.FVector(self.center.x, self.center.y, self.center.z+95.))
        self.actors.append(actor)
        self.remember_actor(actor)
        actor.call_function('SetReplicates', False)
        actor.get_property('CharacterMovement').call_function('DisableMovement')
        mesh = actor.get_property('Mesh')
        mesh.call_function('SetSkeletalMeshAsset', self.mesh_asset)
        mesh.call_function('K2_SetRelativeLocation', NewLocation=self.pawn.get_property('Mesh').get_property('RelativeLocation'), bSweep=False, bTeleport=True)
        mesh.set_property('VisibilityBasedAnimTickOption', 0)
        mesh.set_property('bEnableUpdateRateOptimizations', False)
        mesh.call_function('SetVisibility', True, True)
        actor.call_function('SetActorHiddenInGame', False)
        ue.set_mixin_profile(actor, profile)
        self.current = dict(actor=actor, mesh=mesh, floor=floor, profile=profile, sequence_index=sequence_index,
            parent=[], foot=[], foot_paths=set(), delays=[], last_motion=None, maximum_delta=0., positions=[])
        mesh.call_function('PlayAnimation', self.sequences[sequence_index], False)
        instance = mesh.call_function('GetAnimInstance')
        self.current['length'] = float(instance.call_function('GetLength'))
        self.current['asset_matches'] = instance.get_property('CurrentAsset') == self.sequences[sequence_index]
        self.current['started'] = self.game_time()
        self.enter('playing')

    def playing(self):
        current = self.current
        current['maximum_delta'] = max(current['maximum_delta'], float(self.statics.call_function('GetWorldDeltaSeconds', self.world)))
        current['positions'].append(float(current['mesh'].call_function('GetPosition')))
        if current['mesh'].call_function('IsPlaying'):
            require(self.game_time()-current['started'] < current['length']+2., 'native animation failed to complete')
            return
        if self.role == 'client' and not current['delays']:
            require(self.game_time()-current['started'] < current['length']+7., 'native footstep delay did not resume')
            return
        self.end_case()

    def end_case(self):
        current = self.current
        source = self.audit['sequences'][current['sequence_index']]
        expected = [row for row in source['notifies'] if row.get('effect_tag')]
        parent, foot = current['parent'], current['foot']
        row = dict(profile=current['profile'], sequence_index=current['sequence_index'], sequence=source['package'],
            expected_context_notifies=len(expected), playback_entry='SkeletalMeshComponent.PlayAnimation',
            single_node_asset_matches=current['asset_matches'], native_position_advanced=bool(current['positions']) and max(current['positions']) > .1,
            native_playback_completed=not current['mesh'].call_function('IsPlaying'),
            parent_calls=len(parent), footstep_calls=len(foot),
            input_sequence_and_bones_match_original=all(s['sequence'] == source['package'] and s['mesh_matches'] and s['tag'] == 'AnimEffect.Footstep.Walk' for s in parent) and sorted(s['bone'] for s in parent) == sorted(n['socket'] for n in expected),
            parent_profile_only=all(s['profile'] == current['profile'] for s in parent),
            no_footstep_spawned=not current['foot_paths'],
            footstep_profile_only=all(s['profile'] == current['profile'] for s in foot),
            all_native_traces_hit_owned_floor=all(s['hit'] and s['floor_matches'] for s in foot),
            all_source_fields_match_native_payload=all(s['fields_match'] for s in foot),
            niagara_parameter_samples=sum(s['component_valid'] for s in foot),
            all_niagara_parameters_match_fields=all(s['parameters_match'] for s in foot if s['component_valid']),
            native_after_delay_observed=bool(current['delays']), maximum_world_delta=current['maximum_delta'],
            native_trace_samples=copy.deepcopy(foot))
        if current['delays']:
            first = current['delays'][0]
            row['after_delay_since_last_motion'] = first['time']-current['last_motion']
            alive = bool(current['foot_paths'] & set(self.live_owned_actors()))
            row['after_delay_source_validity_branch_preserved'] = alive == first['component_valid']
        self.report['cases'].append(row)
        self.close_case()
        self.index += 1
        self.enter('start')

    def close_case(self):
        if self.current is not None:
            self.current['mesh'].call_function('Stop')
            for actor in self.live_owned_actors().values():
                if actor.is_a(self.parent_cls) or actor.is_a(self.foot_cls):
                    ue.clear_mixin_profile(actor)
                actor.actor_destroy()
            self.current = None

    def cleanup(self):
        if self.cleaned:
            return
        self.cleaned = True
        self.close_case()
        for kind, (cls, profiles) in self.classes_before.items():
            for profile, source in profiles.items():
                ue.register_mixin_profile(cls, profile, source)
        if hasattr(self, 'foot_selector'):
            self.foot_cls.get_cdo().set_property('PythonMixinProfile', self.foot_selector)
        if hasattr(self, 'parent_selector'):
            self.parent_cls.get_cdo().set_property(parent_policy.SELECTOR, self.parent_selector)
        for obj in reversed(self.roots):
            obj.remove_from_root()
        self.report['primary_player_unchanged'] = capture(self.controller) == self.player_before and self.healths() == self.health_before and primary_state(self.pawn) == self.primary_before
        self.report['owned_objects_profiles_and_roots_restored'] = not self.live_owned_actors() and all(not obj.is_rooted() for obj in self.roots) and self.foot_cls.get_cdo().get_property('PythonMixinProfile') == self.foot_selector and self.parent_cls.get_cdo().get_property(parent_policy.SELECTOR) == self.parent_selector
        self.report['original_profile_classes_restored'] = all(next(row for row in ue.get_registered_mixins() if row['target_class'] == cls)['profiles'][profile]['python_class'] is source for cls, profiles in self.classes_before.values() for profile, source in profiles.items())
        self.report['native_animation_hashes_unchanged'] = all(hashlib.sha256(Path(path).read_bytes()).hexdigest().upper() == digest.upper() for path, digest in self.audit['frozen_asset_hashes'].items())

    def complete(self):
        self.cleanup()
        self.report['status'] = 'awaiting_release'
        self.write()
        atomic_write(self.root/('ready-'+self.role+'.json'), dict(run_id=self.run))
        self.enter('release')

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 360., 'native animation observation timeout: '+self.phase)
            if self.phase == 'ready':
                self.ready()
            elif self.phase == 'start':
                self.start_case()
            elif self.phase == 'playing':
                self.playing()
            else:
                release = read_json(self.root/'release.json')
                if release and release.get('run_id') == self.run:
                    self.finish()
            self.report['phase'] = self.phase
            if self.current is not None:
                self.report['current_observation'] = dict(sequence_index=self.current['sequence_index'], profile=self.current['profile'], parent_calls=len(self.current['parent']), footstep_calls=len(self.current['foot']), delayed_callbacks=len(self.current['delays']), native_trace_samples=copy.deepcopy(self.current['foot'][-2:]))
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
            self.cleanup()
        except Exception:
            error = (error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown', error=error)
        self.write()
        (ue.log_error if error else ue.log)('UEP_FOOTSTEP_ANIMATION_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        if self.report['status'] == 'awaiting_shutdown':
            try:
                self.report['status'] = 'passed';validate(self.report)
            except Exception:
                self.report.update(status='failed', error=traceback.format_exc())
        self.write()
        (ue.log if self.report['status'] == 'passed' else ue.log_error)('UEP_FOOTSTEP_ANIMATION_SHUTDOWN_'+self.report['status'].upper())


result = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPFootstepAnimationResult=')), None)
if result:
    validation = Validation(result);atexit.register(validation.finalize);ticker = ue.add_ticker(validation.tick)
