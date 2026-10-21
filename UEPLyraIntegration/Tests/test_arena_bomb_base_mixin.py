import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


def load():
    unreal = types.ModuleType('unreal_engine')
    unreal.find_class = lambda name: name
    unreal.load_class = lambda name: name
    unreal.FVector = lambda x=0., y=0., z=0.: types.SimpleNamespace(x=x, y=y, z=z)
    unreal.FRotator = lambda: None
    enums = types.ModuleType('unreal_engine.enums')
    enums.EObjectTypeQuery = types.SimpleNamespace(ObjectTypeQuery1=0, ObjectTypeQuery2=1, ObjectTypeQuery3=2)
    structs = types.ModuleType('unreal_engine.structs')
    structs.GameplayEffectContextHandle = lambda: 'empty-context'
    native = types.ModuleType('uep_lyra_abilities.melee_trace_mixin')
    native.native_outputs = lambda cls, name, value: value
    effect = types.ModuleType('uep_lyra_world.effect_pad_mixin')
    effect.valid = lambda value: value is not None
    effect.ability_system = lambda actor: getattr(actor, 'asc', None)
    spec = importlib.util.spec_from_file_location('uep_lyra_world.arena_bomb_base_test', Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/arena_bomb_base_mixin.py')
    policy = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'unreal_engine': unreal, 'unreal_engine.enums': enums,
            'unreal_engine.structs': structs, 'uep_lyra_abilities.melee_trace_mixin': native,
            'uep_lyra_world.effect_pad_mixin': effect}):
        spec.loader.exec_module(policy)
    return policy


class Bomb:
    def __init__(self, **values):
        self.values = values
        self.calls = []
    def get_property(self, name):
        return self.values[name]
    def set_property(self, name, value):
        self.values[name] = value
    def call_function(self, name, *args):
        self.calls.append((name, args))
        return self.values.get(name)


class ArenaBombBasePolicyTests(unittest.TestCase):
    def test_chain_trigger_is_idempotent_and_only_authority_schedules_native_delay(self):
        policy = load()
        for authority in (False, True):
            bomb = Bomb(IsFuseStillBurning=True, HasAuthority=authority)
            policy.LyraArenaBombBasePythonProfile.UEPArenaBombTrigger(bomb)
            policy.LyraArenaBombBasePythonProfile.UEPArenaBombTrigger(bomb)
            self.assertFalse(bomb.values['IsFuseStillBurning'])
            self.assertEqual(sum(name == policy.MIN_BURN for name, _ in bomb.calls), int(authority))

    def test_propagation_keeps_equality_instead_of_clamping_or_greater_equal(self):
        policy = load()
        policy.lib = lambda name: types.SimpleNamespace(call_function=lambda method, a, b: a == b)
        for radius, expected in ((2, policy.HOVER), (3, 'IncrementBlastRadius'), (0, 'IncrementBlastRadius')):
            bomb = Bomb(ExplosionRadius=2, RadiusState=radius)
            policy.LyraArenaBombBasePythonProfile.UEPArenaBombAfterPropagation(bomb)
            self.assertEqual(bomb.calls, [(expected, ())])

    def test_increment_uses_native_integer_arithmetic_then_original_delay(self):
        policy = load()
        policy.lib = lambda name: types.SimpleNamespace(call_function=lambda method, a, b: -(2**31))
        bomb = Bomb(RadiusState=2**31-1)
        policy.LyraArenaBombBasePythonProfile.UEPArenaBombIncrement(bomb)
        self.assertEqual(bomb.values['RadiusState'], -(2**31))
        self.assertEqual([name for name, _ in bomb.calls], ['ServerExpandFireballInAllDirections', policy.PROPAGATE])

    def test_short_direction_arrays_never_resize(self):
        policy = load()
        direction = types.SimpleNamespace(X=1, Y=0)
        bomb = Bomb(DirectionsExpanding=[direction], DirectionsBlocked=[], DirectionalRadius=[], RadiusState=2)
        def call(name, *args):
            bomb.calls.append((name, args))
            return (True, True) if name == 'ServerAddFireballInstance' else False
        bomb.call_function = call
        policy.LyraArenaBombBasePythonProfile.ServerExpandFireballInAllDirections(bomb)
        self.assertEqual((bomb.values['DirectionsBlocked'], bomb.values['DirectionalRadius']), ([], []))

    def test_blocked_direction_skips_native_query(self):
        policy = load()
        bomb = Bomb(DirectionsExpanding=[types.SimpleNamespace(X=1, Y=0)], DirectionsBlocked=[True], DirectionalRadius=[0])
        policy.LyraArenaBombBasePythonProfile.ServerExpandFireballInAllDirections(bomb)
        self.assertEqual([name for name, _ in bomb.calls], [policy.COSMETIC])

    def test_snapshot_truncates_only_successful_native_attribute_query(self):
        policy = load()
        policy.lib = lambda name: types.SimpleNamespace(call_function=lambda method, value: int(value))
        for value, found, expected in ((-2.9, True, -2), (3.9, True, 3), (0., False, 7)):
            bomb = Bomb(InstigatingPlayerState=None, ExplosionRadius=7)
            bomb.call_function = lambda name, state: (value, found)
            policy.LyraArenaBombBasePythonProfile.SnapshotRange(bomb)
            self.assertEqual(bomb.values['ExplosionRadius'], expected)

    def test_native_bonus_probability_keeps_strict_boundary_and_inclusive_draw(self):
        policy = load()
        draws = []
        def call(name, *args):
            draws.append((name, args))
            if name == 'RandomIntegerInRange':
                return 50
            if name == 'Greater_IntInt':
                return args[0] > args[1]
            return 1
        policy.lib = lambda name: types.SimpleNamespace(call_function=call)
        target = Bomb(K2_GetActorLocation='location')
        for percent, expected in ((50, 0), (51, 1)):
            bomb = Bomb(PercentageDropBonus=percent)
            policy.LyraArenaBombBasePythonProfile.SpawnBonus(bomb, target)
            self.assertEqual(len(bomb.calls), expected)
        self.assertIn(('RandomIntegerInRange', (0, 100)), draws)

    def test_authority_repnotify_does_not_call_cosmetics(self):
        policy = load()
        for authority in (False, True):
            bomb = Bomb(HasAuthority=authority)
            policy.LyraArenaBombBasePythonProfile.OnRep_DirectionalRadius(bomb)
            self.assertEqual(sum(name == 'ClientUpdateFireballVisuals' for name, _ in bomb.calls), int(not authority))

    def test_original_named_out_order_is_explicit(self):
        policy = load()
        bomb = Bomb()
        bomb.call_mixin_original = lambda name, dx, dy: (True, False)
        self.assertEqual(policy.LyraArenaBombBaseBlueprintFallbackProfile.ServerAddFireballInstance(bomb, 1, 0), {'SpaceWasBlocked': True, 'SpawnedFireball': False})
        self.assertTrue(policy.LyraArenaBombBasePythonProfile.ServerAddFireballInstance.uep_named_outputs)

    def test_source_effect_level_and_empty_context_are_preserved(self):
        policy = load()
        component = Bomb()
        policy.apply(component, 'effect')
        self.assertEqual(component.calls, [('BP_ApplyGameplayEffectToSelf', ('effect', 0., 'empty-context'))])

    def test_hover_does_not_read_actor_after_destroying_it(self):
        policy = load()
        bomb = Bomb()
        self.assertFalse(policy.LyraArenaBombBasePythonProfile.UEPArenaBombAfterHover(bomb))
        self.assertEqual(bomb.calls, [('K2_DestroyActor', ())])

    def test_static_block_does_not_short_circuit_later_destructible_side_effects(self):
        policy = load()
        static, block = Bomb(), Bomb()
        static.is_a = lambda cls: cls == 'StaticMeshActor'
        block.is_a = lambda cls: cls == policy.BLOCK
        overlap_arguments = []
        def call(name, *args, **kwargs):
            if name.startswith('Multiply_'):
                return args[0]*args[1]
            if name == 'Add_VectorVector':
                return args[0]
            if name == 'BoxOverlapActors':
                overlap_arguments.append(kwargs)
                return dict(OutActors=[static, block])
            self.fail(name)
        policy.lib = lambda name: types.SimpleNamespace(call_function=call)
        bomb = Bomb(RadiusState=2, K2_GetActorLocation=policy.ue.FVector())
        self.assertEqual(policy.add_fireball(bomb, 1, 0), dict(SpaceWasBlocked=True, SpawnedFireball=False))
        self.assertIn(('SpawnBonus', (block,)), bomb.calls)
        self.assertEqual(block.calls, [('K2_DestroyActor', ())])
        self.assertEqual(overlap_arguments[0]['ActorsToIgnore'], [bomb])
        self.assertEqual(overlap_arguments[0]['ObjectTypes'], [1, 0, 2])
