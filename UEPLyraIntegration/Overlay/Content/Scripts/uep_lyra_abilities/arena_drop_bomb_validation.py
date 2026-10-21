"""Actual local-player GAS requests, native montage/spawn tasks and bomb refund."""
import atexit, sys, time, traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayAbilityActorInfo, GameplayTag, HitResult
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from uep_lyra_world import arena_bomb_base_mixin as base_policy
from uep_lyra_world import arena_bomb_visual_mixin as visual_policy
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import arena_drop_bomb_mixin as policy
from .arena_drop_bomb_contract import validate
PROBE = '/Game/UEPValidation/BP_ArenaDropBombProbe.BP_ArenaDropBombProbe_C'
ATTRIBUTES = '/Game/UEPValidation/BP_ArenaBombBaseProbe.BP_ArenaBombBaseProbe_C'
MONTAGE = '/TopDownArena/Game/Bombs/DropBomb_Montage.DropBomb_Montage'


def arg(name):
    return next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def game(world):
    return float(policy.lib('GameplayStatics').call_function('GetTimeSeconds', world))


def destroyed(actor):
    return not valid(actor) or bool(actor.call_function('IsActorBeingDestroyed'))


class Validation:
    def __init__(self, result):
        self.path = Path(result)
        self.mode = arg('UEPArenaDropBombMode')
        self.started = time.monotonic()
        self.finished = False
        self.stage = 'discover'
        self.actors, self.roots, self.counter_refs = [], [], []
        self.selector = None
        self.own_grant = False
        self.report = dict(status='running', error=None, mode=self.mode, grid_cases=[], drops=[], native_request_entry='ASC.TryActivateAbilityByClass')
        for key in ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested', 'audio_playback_tested', 'physical_input_tested', 'callbacks_replayed', 'native_tasks_replaced', 'spawn_failure_native_tested', 'commit_race_failure_native_tested'):
            self.report[key] = False
        self.cls, self.base, self.child = ue.load_class(policy.CLASS), ue.load_class(base_policy.CLASS), ue.load_class(visual_policy.CLASS)
        self.probe_cls, self.attributes_cls = ue.load_class(PROBE), ue.load_class(ATTRIBUTES)
        for cls in (self.cls, self.base, self.child, self.probe_cls, self.attributes_cls):
            if not cls.is_rooted():
                cls.add_to_root()
                self.roots.append(cls)
        self.probe, self.attributes = self.probe_cls.get_cdo(), self.attributes_cls.get_cdo()
        ue.register_declared_mixin(self.base)
        ue.register_declared_mixin(self.child)
        if self.mode != 'Baseline':
            self.selector = self.cls.get_cdo().get_property('PythonMixinProfile')
            self.cls.get_cdo().set_property('PythonMixinProfile', self.mode)
            ue.register_declared_mixin(self.cls)
        self.remember(self.cls.get_cdo())

    def remember(self, ability):
        ref = policy.evidence(ability)
        if not any(ref is old for old in self.counter_refs):
            self.counter_refs.append(ref)

    def spec(self):
        return next((s for s in self.asc.get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.is_a(self.cls)), None)

    def instance(self):
        spec = self.spec()
        found = [a for a in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(a)]
        if len(found) != 1:
            raise RuntimeError('one actual instanced drop ability required')
        self.remember(found[0])
        return found[0]

    def remaining(self):
        value, found = self.attributes.call_function('ReadBombsRemaining', self.state)
        if not found:
            raise RuntimeError('actual Arena BombsRemaining attribute missing')
        return float(value)

    def bombs(self):
        return set(native_outputs('GameplayStatics', 'GetAllActorsOfClass', policy.lib('GameplayStatics').call_function('GetAllActorsOfClass', self.world, self.base))['OutActors'])

    def move(self, x, y):
        self.pawn.call_function('K2_SetActorLocation', ue.FVector(x, y, 3000.), False, HitResult(), True)

    def query(self):
        info = GameplayAbilityActorInfo(OwnerActor=self.state, AvatarActor=self.pawn, PlayerController=self.controller, AbilitySystemComponent=self.asc)
        allowed, container = self.instance().call_function('K2_CanActivateAbility', info, self.spec().Handle)
        return dict(allowed=bool(allowed), tags=[str(tag.TagName) for tag in container.GameplayTags])

    def setup(self, world, controller, pawn):
        self.world, self.controller, self.pawn = world, controller, pawn
        self.state, self.asc = pawn.get_property('PlayerState'), ability_system(pawn)
        self.original_location = pawn.call_function('K2_GetActorLocation')
        self.movement = pawn.get_property('CharacterMovement')
        self.original_mode = int(self.movement.get_property('MovementMode'))
        self.original_custom = int(self.movement.get_property('CustomMovementMode'))
        self.movement.call_function('DisableMovement')
        if self.spec() is None:
            self.grant = self.asc.call_function('K2_GiveAbility', self.cls, 1, -1)
            self.own_grant = True
        self.stage = 'ready'

    def ready(self):
        self.ability = self.instance()
        self.avatar = self.world.actor_spawn(ue.find_class('StaticMeshActor'), ue.FVector(600000., 600000., 3000.))
        self.actors.append(self.avatar)
        self.avatar.get_component_by_type(ue.find_class('StaticMeshComponent')).call_function('SetMobility', 2)
        for x, y, z in ((0., 0., 999.), (49.999, -49.999, 7.), (50., -50., 777.), (150., -150., -999.), (-50.001, 149.999, 100.), (-150.001, 250., 100.)):
            self.avatar.call_function('K2_SetActorLocation', ue.FVector(x, y, z), False, HitResult(), True)
            value = policy.one(self.probe.call_function('GetBombSpawnLocation', self.ability, self.avatar))
            self.report['grid_cases'].append([float(value.x), float(value.y), float(value.z)])
        self.move(520049., 520051.)
        self.stage = 'first'
        self.since = game(self.world)

    def request(self):
        self.before_bombs = self.bombs()
        self.remaining_before = self.remaining()
        self.drop_started = game(self.world)
        self.request_accepted = bool(self.asc.call_function('TryActivateAbilityByClass', self.cls, False))
        self.stage = 'observe-drop'

    def observe_drop(self):
        created = self.bombs()-self.before_bombs
        if not created:
            if game(self.world)-self.drop_started > 3.:
                raise RuntimeError('accepted native request did not spawn original bomb')
            return
        self.actors.extend(created)
        actor, = created
        actual = actor.call_function('K2_GetActorLocation')
        location = policy.one(self.probe.call_function('GetBombSpawnLocation', self.instance(), self.pawn))
        anim = self.pawn.get_property('Mesh').call_function('GetAnimInstance')
        montage = anim.call_function('GetCurrentActiveMontage')
        active = bool(self.instance().get_property('bIsActive'))
        self.report['drops'].append(dict(request_accepted=self.request_accepted, new_bomb_count=len(created),
            original_standard_class=actor.is_a(self.child), expected_location=actual == location,
            original_instigator=actor.get_property('Instigator') == self.pawn,
            remaining_before=self.remaining_before, remaining_after=self.remaining(), ability_active_after_spawn=active,
            montage_keeps_playing_after_end=valid(montage) and montage.get_path_name() == MONTAGE and not active))
        if len(self.report['drops']) == 1:
            self.first_bomb = actor
            self.first_started = self.drop_started
            self.report['occupied_query'] = self.query()
            self.move(523049., 523051.)
            self.stage = 'cost-denial'
            self.since = game(self.world)
        else:
            self.second_bomb = actor
            self.move(530000., 530000.)
            self.stage = 'natural'
            self.report['natural'] = dict(both_bombs_destroyed=False, remaining_after_refund=None, first_destroy_seconds=None)

    def denied(self, kind):
        if game(self.world)-self.since < .08:
            return
        before = self.bombs()
        accepted = bool(self.asc.call_function('TryActivateAbilityByClass', self.cls, False))
        self.report[kind+'_denial'] = dict(request_accepted=accepted, new_bomb_count=len(self.bombs()-before), remaining=self.remaining())
        if kind == 'cost':
            # The original native increment effect restores one test token, so the
            # next rejected request isolates occupancy instead of empty cost.
            base_policy.apply(self.asc, ue.load_class(base_policy.RESTORE))
            self.move(520049., 520051.)
            self.stage = 'occupancy-denial'
            self.since = game(self.world)
        else:
            self.move(526049., 526051.)
            self.stage = 'second'
            self.since = game(self.world)

    def natural(self):
        if destroyed(self.first_bomb) and self.report['natural']['first_destroy_seconds'] is None:
            self.report['natural']['first_destroy_seconds'] = game(self.world)-self.first_started
        if destroyed(self.first_bomb) and destroyed(self.second_bomb):
            self.report['natural'].update(both_bombs_destroyed=True, remaining_after_refund=self.remaining())
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
                self.setup(world, controller, pawn)
                return

    def tick(self, delta):
        if self.finished:
            return False
        try:
            if time.monotonic()-self.started > 150.:
                raise RuntimeError('drop bomb native observation timed out: '+self.stage)
            if self.stage == 'discover':
                self.discover()
            elif self.stage == 'ready':
                self.ready()
            elif self.stage in ('first', 'second'):
                if game(self.world)-self.since >= .08:
                    if self.stage == 'first':
                        self.report['free_query'] = self.query()
                    self.request()
            elif self.stage == 'observe-drop':
                self.observe_drop()
            elif self.stage == 'cost-denial':
                self.denied('cost')
            elif self.stage == 'occupancy-denial':
                self.denied('occupancy')
            else:
                self.natural()
            atomic_write(self.path, self.report)
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def cleanup(self):
        for actor in reversed(self.actors):
            if not destroyed(actor):
                actor.actor_destroy()
        if self.own_grant:
            self.asc.call_function('ClearAbility', self.grant)
        if hasattr(self, 'pawn') and valid(self.pawn):
            self.pawn.call_function('K2_SetActorLocation', self.original_location, False, HitResult(), True)
            self.movement.call_function('SetMovementMode', self.original_mode, self.original_custom)
        self.report['counts'] = {key: sum(ref[key] for ref in self.counter_refs) for key in self.counter_refs[0]}
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
        (ue.log_error if error else ue.log)('UEP_ARENA_DROP_BOMB_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        if self.report['status'] == 'awaiting_shutdown':
            try:
                self.report['status'] = 'passed'
                validate(self.report)
            except Exception:
                self.report.update(status='failed', error=traceback.format_exc())
        atomic_write(self.path, self.report)
        (ue.log if self.report['status'] == 'passed' else ue.log_error)('UEP_ARENA_DROP_BOMB_SHUTDOWN_'+self.report['status'].upper())


result = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPArenaDropBombResult=')), None)
if result:
    validation = Validation(result)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
