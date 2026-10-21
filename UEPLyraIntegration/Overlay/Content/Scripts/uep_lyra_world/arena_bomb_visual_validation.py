"""Actual construction, native virtual calls and unreplayed parent fuse lifecycle."""
import atexit, copy, sys, time, traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import IntPoint
from uep_lyra_network_io import atomic_write
from .effect_pad_mixin import valid
from . import arena_bomb_visual_mixin as policy
from .arena_bomb_visual_contract import validate
PROBE = '/Game/UEPValidation/BP_ArenaBombVisualProbe.BP_ArenaBombVisualProbe_C'


def arg(name):
    return next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def game(obj):
    return float(policy.lib('GameplayStatics').call_function('GetTimeSeconds', obj))


class Validation:
    def __init__(self, result):
        self.path = Path(result)
        self.mode = arg('UEPArenaBombVisualMode')
        self.started = time.monotonic()
        self.finished = False
        self.actors, self.roots = [], []
        self.selector = None
        self.report = dict(status='running', error=None, mode=self.mode, cases=[])
        for key in ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested', 'audio_playback_tested', 'callbacks_replayed', 'native_fuse_replaced'):
            self.report[key] = False
        self.cls, self.probe_cls = ue.load_class(policy.CLASS), ue.load_class(PROBE)
        for cls in (self.cls, self.probe_cls):
            if not cls.is_rooted():
                cls.add_to_root()
                self.roots.append(cls)
        self.probe = self.probe_cls.get_cdo()
        if self.mode != 'Baseline':
            self.selector = self.cls.get_cdo().get_property('PythonMixinProfile')
            self.cls.get_cdo().set_property('PythonMixinProfile', self.mode)
            ue.register_declared_mixin(self.cls)

    def spawn(self, lifespan, index):
        statics = policy.lib('GameplayStatics')
        transform = policy.lib('KismetMathLibrary').call_function('MakeTransform', ue.FVector(450000.+1000.*index, 450000., 3000.), ue.FRotator(), ue.FVector(1., 1., 1.))
        actor = statics.call_function('BeginDeferredActorSpawnFromClass', self.world, self.cls, transform, 1, None, 0)
        self.actors.append(actor)
        actor.set_property('Instigator', self.pawn)
        actor.set_property('BombLifespan', lifespan)
        statics.call_function('FinishSpawningActor', actor, transform, 0)
        return actor

    def setup(self, world, pawn):
        self.world, self.pawn = world, pawn
        before = float(policy.lib('GameplayStatics').call_function('GetRealTimeSeconds', world))
        self.bomb = self.spawn(2., 0)
        after = float(policy.lib('GameplayStatics').call_function('GetRealTimeSeconds', world))
        self.bomb.set_property('IsFuseStillBurning', False)
        material = self.bomb.get_property('BombMID')
        initial = float(material.call_function('K2_GetScalarParameterValue', 'InitialTime'))
        self.report['materials'] = dict(same_mid_on_both_meshes=all(self.bomb.get_property(n).call_function('GetMaterial', 0) == material for n in ('SphereMesh', 'CylinderMesh')),
            lifespan=float(material.call_function('K2_GetScalarParameterValue', 'BombLifespan')), real_time_bounded=before-.001 <= initial <= after+.001)
        plan = [([], []), ([2, 1, 2, 1], [(1, 0), (-1, 0), (0, 1), (0, -1)]),
                ([2, 2], [(1, 0), (1, 0)]), ([0, -2], [(1, 0), (0, 1)]),
                ([2], [(0, 0)]), ([2], [(-2, 3)])]
        arrays = policy.lib('NiagaraDataInterfaceArrayFunctionLibrary')
        for radii, directions in plan:
            self.bomb.set_property('DirectionalRadius', radii)
            self.bomb.set_property('DirectionsExpanding', [IntPoint(X=x, Y=y) for x, y in directions])
            self.probe.call_function('UpdateVisuals', self.bomb)
            component = self.bomb.get_property('NS_BombFuse1')
            positions = [[float(v.x), float(v.y), float(v.z)] for v in arrays.call_function('GetNiagaraArrayVector', component, 'User.PositionArray')]
            self.report['cases'].append(dict(positions=positions, niagara_active=bool(component.call_function('IsActive'))))
        self.report['counts'] = copy.deepcopy(policy.evidence(self.bomb))
        self.natural = self.spawn(.6, 1)
        self.natural.set_property('ExplosionRadius', 2)
        self.natural.set_property('DirectionsExpanding', [IntPoint(X=1, Y=0), IntPoint(X=-1, Y=0), IntPoint(X=0, Y=1), IntPoint(X=0, Y=-1)])
        self.natural.set_property('DirectionsBlocked', [False]*4)
        self.natural.set_property('DirectionalRadius', [0]*4)
        self.natural_counts = policy.evidence(self.natural)
        self.natural_started = game(world)
        self.report['natural'] = dict(fuse_was_lit=bool(self.natural.get_property('IsFuseStillBurning')), fuse_extinguished=False, radius_seen=0, destroyed=False)

    def tick(self, delta):
        if self.finished:
            return False
        try:
            if time.monotonic()-self.started > 150.:
                raise RuntimeError('native bomb visual timeout')
            if not hasattr(self, 'world'):
                for world in ue.all_worlds():
                    if world.get_world_type() not in (1, 3) or 'TopDown' not in world.get_name():
                        continue
                    controller = policy.lib('GameplayStatics').call_function('GetPlayerController', world, 0)
                    if not valid(controller):
                        continue
                    pawn = controller.get_controlled_pawn()
                    if valid(pawn) and valid(pawn.get_property('PlayerState')):
                        self.setup(world, pawn)
                        break
            else:
                row = self.report['natural']
                if valid(self.natural) and not self.natural.call_function('IsActorBeingDestroyed'):
                    row['fuse_extinguished'] |= not bool(self.natural.get_property('IsFuseStillBurning'))
                    row['radius_seen'] = max(row['radius_seen'], int(self.natural.get_property('RadiusState')))
                else:
                    row.update(destroyed=True, elapsed_game_seconds=game(self.world)-self.natural_started)
                    self.report['natural_counts'] = copy.deepcopy(self.natural_counts)
                    self.finish()
            atomic_write(self.path, self.report)
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def cleanup(self):
        for actor in reversed(self.actors):
            if valid(actor) and not actor.call_function('IsActorBeingDestroyed'):
                actor.actor_destroy()
        if self.selector is not None:
            self.cls.get_cdo().set_property('PythonMixinProfile', self.selector)
        for cls in reversed(self.roots):
            cls.remove_from_root()
        self.report['cleanup_complete'] = all(not cls.is_rooted() for cls in self.roots) and (self.selector is None or self.cls.get_cdo().get_property('PythonMixinProfile') == self.selector)

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.cleanup()
        except Exception:
            error = (error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown', error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)('UEP_ARENA_BOMB_VISUAL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        if self.report['status'] == 'awaiting_shutdown':
            try:
                self.report['status'] = 'passed'
                validate(self.report)
            except Exception:
                self.report.update(status='failed', error=traceback.format_exc())
        atomic_write(self.path, self.report)
        (ue.log if self.report['status'] == 'passed' else ue.log_error)('UEP_ARENA_BOMB_VISUAL_SHUTDOWN_'+self.report['status'].upper())


result = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPArenaBombVisualResult=')), None)
if result:
    validation = Validation(result)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
