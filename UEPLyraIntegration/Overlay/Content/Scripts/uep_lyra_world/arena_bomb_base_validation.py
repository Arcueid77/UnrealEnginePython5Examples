"""Natural bomb fuse/chain and actual native collision matrix in the Arena map."""
import atexit, copy, sys, time, traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import IntPoint, GameplayTag, HitResult
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .effect_pad_mixin import valid, ability_system
from . import arena_bomb_base_mixin as policy
from . import arena_bomb_visual_mixin as child_policy
from .arena_bomb_base_contract import validate
PROBE = '/Game/UEPValidation/BP_ArenaBombBaseProbe.BP_ArenaBombBaseProbe_C'
DECREMENT = '/TopDownArena/Game/Bombs/GE_DecrementBombsRemaining.GE_DecrementBombsRemaining_C'


def arg(name):
    return next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def game(obj):
    return float(policy.lib('GameplayStatics').call_function('GetTimeSeconds', obj))


def destroyed(actor):
    return not valid(actor) or bool(actor.call_function('IsActorBeingDestroyed'))


class Validation:
    def __init__(self, result):
        self.path = Path(result)
        self.mode = arg('UEPArenaBombBaseMode')
        self.started = time.monotonic()
        self.finished = False
        self.stage = 'discover'
        self.actors, self.roots, self.selectors, self.counter_refs, self.child_refs = [], [], [], [], []
        self.report = dict(status='running', error=None, mode=self.mode, collision_cases=[])
        for key in ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested', 'audio_playback_tested', 'callbacks_replayed', 'native_delays_replaced', 'global_rng_replaced'):
            self.report[key] = False
        self.base, self.child, self.probe_cls = ue.load_class(policy.CLASS), ue.load_class(child_policy.CLASS), ue.load_class(PROBE)
        for cls in (self.base, self.child, self.probe_cls):
            if not cls.is_rooted():
                cls.add_to_root()
                self.roots.append(cls)
        self.probe = self.probe_cls.get_cdo()
        if self.mode != 'Baseline':
            for cls, selectors in ((self.base, (policy.SELECTOR,)), (self.child, (policy.SELECTOR, 'PythonMixinProfile'))):
                for selector in selectors:
                    self.selectors.append((cls, selector, cls.get_cdo().get_property(selector)))
                    cls.get_cdo().set_property(selector, self.mode)
            ue.register_declared_mixin(self.base)
        ue.register_declared_mixin(self.child)

    def own(self, actor):
        self.actors.append(actor)
        return actor

    def spawn(self, position, lifespan=100., instigator=None):
        transform = policy.lib('KismetMathLibrary').call_function('MakeTransform', position, ue.FRotator(), ue.FVector(1., 1., 1.))
        actor = self.own(policy.lib('GameplayStatics').call_function('BeginDeferredActorSpawnFromClass', self.world, self.child, transform, 1, None, 0))
        actor.set_property('Instigator', instigator if instigator is not None else self.character)
        actor.set_property('BombLifespan', lifespan)
        policy.lib('GameplayStatics').call_function('FinishSpawningActor', actor, transform, 0)
        actor.set_property('PercentageDropBonus', 0)
        actor.set_property('RadiusState', 1)
        actor.set_property('DirectionsExpanding', [IntPoint(X=1, Y=0), IntPoint(X=-1, Y=0), IntPoint(X=0, Y=1), IntPoint(X=0, Y=-1)])
        actor.set_property('DirectionsBlocked', [False]*4)
        actor.set_property('DirectionalRadius', [0]*4)
        self.counter_refs.append(policy.evidence(actor))
        self.child_refs.append(child_policy.evidence(actor))
        return actor

    def setup(self, world, pawn):
        self.world, self.pawn = world, pawn
        self.state = pawn.get_property('PlayerState')
        self.character = self.own(world.actor_spawn(ue.find_class('Character'), ue.FVector(470000., 470000., 3000.)))
        self.character.get_property('CharacterMovement').call_function('DisableMovement')
        self.overlap_bomb = self.spawn(self.character.call_function('K2_GetActorLocation'))
        self.overlap_bomb.set_property('IsFuseStillBurning', False)
        self.stage = 'overlap'
        self.since = game(world)

    def overlap(self):
        if game(self.world)-self.since < .1:
            return
        capsule = self.character.get_property('CapsuleComponent')
        collision = self.overlap_bomb.get_property('CollisionBox')
        self.report['overlap'] = dict(ignored_initially=collision in capsule.call_function('CopyArrayOfMoveIgnoreComponents'))
        self.character.call_function('K2_SetActorLocation', ue.FVector(471000., 470000., 3000.), False, HitResult(), True)
        self.stage = 'overlap-end'
        self.since = game(self.world)

    def prepare_cases(self):
        if game(self.world)-self.since < .1:
            return
        capsule = self.character.get_property('CapsuleComponent')
        self.report['overlap']['restored_after_native_end'] = self.overlap_bomb.get_property('CollisionBox') not in capsule.call_function('CopyArrayOfMoveIgnoreComponents')
        self.cases = []
        for index, name in enumerate(('empty', 'static', 'destructible', 'pickup', 'asc')):
            position = ue.FVector(480000.+2000.*index, 480000., 3000.)
            actor = self.spawn(position)
            actor.set_property('IsFuseStillBurning', False)
            target_position = ue.FVector(position.x+100., position.y, position.z+50.)
            target = None
            if name == 'static':
                target = self.own(self.world.actor_spawn(ue.find_class('StaticMeshActor'), target_position))
                mesh = target.get_component_by_type(ue.find_class('StaticMeshComponent'))
                mesh.call_function('SetMobility', 2)
                mesh.call_function('SetStaticMesh', ue.load_object(ue.find_class('StaticMesh'), '/Engine/BasicShapes/Cube.Cube'))
                mesh.call_function('SetCollisionProfileName', 'BlockAll', True)
            elif name in ('destructible', 'pickup'):
                target = self.own(self.world.actor_spawn(ue.load_class(policy.BLOCK if name == 'destructible' else policy.PICKUP), target_position))
            elif name == 'asc':
                target = self.pawn
                self.pawn.get_property('CharacterMovement').call_function('DisableMovement')
                self.pawn.call_function('K2_SetActorLocation', target_position, False, HitResult(), True)
            self.cases.append((name, actor, target))
        self.stage = 'cases'
        self.since = game(self.world)

    def run_cases(self):
        if game(self.world)-self.since < .1:
            return
        for name, actor, target in self.cases:
            component = actor.get_property('FireballCollision')
            before = int(component.call_function('GetInstanceCount'))
            health = self.pawn.get_component_by_type(ue.find_class('LyraHealthComponent')) if name == 'asc' else None
            hp = float(health.call_function('GetHealth')) if health is not None else None
            queried = False
            if name == 'asc':
                from unreal_engine.enums import EObjectTypeQuery
                position = actor.call_function('K2_GetActorLocation')
                result = policy.lib('KismetSystemLibrary').call_function('BoxOverlapActors', self.world, ue.FVector(position.x+100., position.y, position.z+50.), ue.FVector(48., 48., 48.), [EObjectTypeQuery.ObjectTypeQuery2, EObjectTypeQuery.ObjectTypeQuery1, EObjectTypeQuery.ObjectTypeQuery3], None, [actor])
                queried = self.pawn in native_outputs('KismetSystemLibrary', 'BoxOverlapActors', result)['OutActors']
            space, spawned = self.probe.call_function('ServerAddFireballInstance', actor, 1, 0)
            row = dict(name=name, space_blocked=bool(space), spawned=bool(spawned), instance_delta=int(component.call_function('GetInstanceCount'))-before,
                       target_destroyed=target is not None and destroyed(target))
            if name == 'asc':
                row.update(native_query_contains_pawn=queried, health_before=hp, health_after=float(health.call_function('GetHealth')))
            self.report['collision_cases'].append(row)
        bomb = self.cases[0][1]
        bomb.set_property('ExplosionRadius', 7)
        bomb.set_property('InstigatingPlayerState', None)
        self.probe.call_function('SnapshotRange', bomb)
        missing = int(bomb.get_property('ExplosionRadius'))
        bomb.set_property('InstigatingPlayerState', self.state)
        value, found = self.probe.call_function('ReadBombRange', self.state)
        self.probe.call_function('SnapshotRange', bomb)
        self.report['snapshot'] = dict(attribute=float(value), found=bool(found), radius=int(bomb.get_property('ExplosionRadius')), missing_keeps_radius=missing)
        self.before_visuals = copy.deepcopy(child_policy.evidence(bomb))
        self.probe.call_function('OnRep_DirectionalRadius', bomb)
        self.report['authority_rep_does_not_update_visuals'] = child_policy.evidence(bomb) == self.before_visuals
        bomb.set_property('DirectionsBlocked', [])
        bomb.set_property('DirectionalRadius', [])
        self.probe.call_function('ServerExpandFireballInAllDirections', bomb)
        self.report['short_arrays'] = dict(blocked_length=len(bomb.get_property('DirectionsBlocked')), radius_length=len(bomb.get_property('DirectionalRadius')))
        self.bonus_target = self.own(self.world.actor_spawn(ue.find_class('StaticMeshActor'), ue.FVector(510000., 510000., 3000.)))
        pickup_cls = ue.load_class(policy.PICKUP)
        self.pickups_before = set(native_outputs('GameplayStatics', 'GetAllActorsOfClass', policy.lib('GameplayStatics').call_function('GetAllActorsOfClass', self.world, pickup_cls))['OutActors'])
        bomb.set_property('PercentageDropBonus', 0)
        self.probe.call_function('SpawnBonus', bomb, self.bonus_target)
        after_zero = set(native_outputs('GameplayStatics', 'GetAllActorsOfClass', policy.lib('GameplayStatics').call_function('GetAllActorsOfClass', self.world, pickup_cls))['OutActors'])
        bomb.set_property('PercentageDropBonus', 101)
        self.probe.call_function('SpawnBonus', bomb, self.bonus_target)
        after_one = set(native_outputs('GameplayStatics', 'GetAllActorsOfClass', policy.lib('GameplayStatics').call_function('GetAllActorsOfClass', self.world, pickup_cls))['OutActors'])
        created = list(after_one-after_zero)
        self.actors.extend(created)
        self.report['bonus'] = dict(zero_count=len(after_zero-self.pickups_before), guaranteed_count=len(created), original_effect_class=len(created) == 1 and created[0].get_property('GameplayEffectToApply').get_path_name() in policy.BONUSES,
                                   original_location=len(created) == 1 and created[0].call_function('K2_GetActorLocation') == self.bonus_target.call_function('K2_GetActorLocation'))
        # Spend one native cost first, so the eventual native destruction refund is observable.
        self.remaining_before = float(self.probe.call_function('ReadBombsRemaining', self.state)[0])
        policy.apply(ability_system(self.pawn), ue.load_class(DECREMENT))
        self.remaining_spent = float(self.probe.call_function('ReadBombsRemaining', self.state)[0])
        self.main = self.spawn(ue.FVector(520000., 520000., 3000.), .6, self.pawn)
        self.main.set_property('RadiusState', 0)
        self.main.set_property('ExplosionRadius', 2)
        self.chain = self.spawn(ue.FVector(520100., 520000., 3000.))
        self.chain.set_property('RadiusState', 0)
        self.chain.set_property('ExplosionRadius', 1)
        self.chain.set_property('DirectionsExpanding', [IntPoint(X=-1, Y=0)])
        self.chain.set_property('DirectionsBlocked', [False])
        self.chain.set_property('DirectionalRadius', [0])
        self.natural_started = game(self.world)
        self.chain_triggered = None
        self.chain_blast = None
        self.report['natural'] = dict(main_destroyed=False, chain_destroyed=False, main_radius_seen=0, chain_radius_seen=0, chain_fuse_extinguished=False)
        self.stage = 'natural'

    def natural(self):
        now = game(self.world)
        row = self.report['natural']
        for name, actor in (('main', self.main), ('chain', self.chain)):
            if destroyed(actor):
                if not row[name+'_destroyed']:
                    row[name+'_destroyed'] = True
                    row[name+'_duration'] = now-self.natural_started
            else:
                radius = int(actor.get_property('RadiusState'))
                row[name+'_radius_seen'] = max(row[name+'_radius_seen'], radius)
                if name == 'chain':
                    if not actor.get_property('IsFuseStillBurning') and self.chain_triggered is None:
                        self.chain_triggered = now
                        row['chain_fuse_extinguished'] = True
                    if radius and self.chain_blast is None:
                        self.chain_blast = now
        if row['main_destroyed'] and row['chain_destroyed']:
            row['chain_minimum_burn_seconds'] = self.chain_blast-self.chain_triggered if self.chain_blast is not None and self.chain_triggered is not None else -1.
            row['bombs_remaining_restored'] = self.remaining_spent < self.remaining_before and float(self.probe.call_function('ReadBombsRemaining', self.state)[0]) == self.remaining_before
            self.finish()

    def discover(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3) or 'TopDown' not in world.get_name():
                continue
            controller = policy.lib('GameplayStatics').call_function('GetPlayerController', world, 0)
            if not valid(controller):
                continue
            pawn = controller.get_controlled_pawn()
            phases = policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem', world, ue.find_class('LyraGamePhaseSubsystem'))
            if valid(pawn) and valid(ability_system(pawn)) and phases.call_function('IsPhaseActive', GameplayTag(TagName='ShooterGame.GamePhase.Playing')):
                self.setup(world, pawn)
                return

    def tick(self, delta):
        if self.finished:
            return False
        try:
            if time.monotonic()-self.started > 150.:
                raise RuntimeError('base bomb native observation timed out: '+self.stage)
            {'discover': self.discover, 'overlap': self.overlap, 'overlap-end': self.prepare_cases,
             'cases': self.run_cases, 'natural': self.natural}[self.stage]()
            atomic_write(self.path, self.report)
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def cleanup(self):
        for actor in reversed(self.actors):
            if not destroyed(actor):
                actor.actor_destroy()
        self.report['counts'] = {key: sum(v[key] for v in self.counter_refs) for key in self.counter_refs[0]} if self.counter_refs else {}
        self.report['child_visuals_observed'] = any(v['python_visuals']+v['fallback_visuals'] > 0 for v in self.child_refs)
        for cls, selector, previous in reversed(self.selectors):
            cls.get_cdo().set_property(selector, previous)
        for cls in reversed(self.roots):
            cls.remove_from_root()
        self.report['cleanup_complete'] = all(cls.get_cdo().get_property(selector) == previous for cls, selector, previous in self.selectors) and all(not cls.is_rooted() for cls in self.roots)

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
        (ue.log_error if error else ue.log)('UEP_ARENA_BOMB_BASE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        if self.report['status'] == 'awaiting_shutdown':
            try:
                self.report['status'] = 'passed'
                validate(self.report)
            except Exception:
                self.report.update(status='failed', error=traceback.format_exc())
        atomic_write(self.path, self.report)
        (ue.log if self.report['status'] == 'passed' else ue.log_error)('UEP_ARENA_BOMB_BASE_SHUTDOWN_'+self.report['status'].upper())


result = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPArenaBombBaseResult=')), None)
if result:
    validation = Validation(result)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
