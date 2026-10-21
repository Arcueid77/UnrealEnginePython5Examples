import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


def load():
    unreal = types.ModuleType('unreal_engine')
    unreal.FVector = lambda x=0., y=0., z=0.: types.SimpleNamespace(x=x, y=y, z=z)
    unreal.load_class = lambda name: name
    enums = types.ModuleType('unreal_engine.enums')
    enums.EObjectTypeQuery = types.SimpleNamespace(ObjectTypeQuery2=1)
    structs = types.ModuleType('unreal_engine.structs')
    structs.GameplayTag = lambda **values: values
    structs.GameplayTagContainer = lambda **values: values
    native = types.ModuleType('uep_lyra_abilities.melee_trace_mixin')
    native.native_outputs = lambda cls, method, value: value
    spec = importlib.util.spec_from_file_location('arena_drop_bomb_test', Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_abilities/arena_drop_bomb_mixin.py')
    policy = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'unreal_engine': unreal, 'unreal_engine.enums': enums,
            'unreal_engine.structs': structs, 'uep_lyra_abilities.melee_trace_mixin': native}):
        spec.loader.exec_module(policy)
    return policy


class Ability:
    def __init__(self, **returns):
        self.returns, self.calls = returns, []
    def call_function(self, method, *args):
        self.calls.append((method, args))
        return self.returns.get(method)


class ArenaDropBombPolicyTests(unittest.TestCase):
    def test_location_flattens_z_before_native_grid_snap(self):
        policy = load()
        calls = []
        policy.lib = lambda name: types.SimpleNamespace(call_function=lambda method, value, grid: calls.append((method, value, grid)) or 'snapped')
        actor = Ability(K2_GetActorLocation=policy.ue.FVector(-50., 149.9, 999.))
        self.assertEqual(policy.LyraArenaDropBombPythonProfile.GetBombSpawnLocation(Ability(), actor), 'snapped')
        self.assertEqual((calls[0][0], calls[0][1].x, calls[0][1].y, calls[0][1].z, calls[0][2]), ('Vector_SnappedToGrid', -50., 149.9, 0., 100.))

    def test_can_activate_keeps_native_class_object_type_radius_and_failure_tag(self):
        policy = load()
        calls = []
        policy.lib = lambda name: types.SimpleNamespace(call_function=lambda method, **kwargs: calls.append(kwargs) or dict(ReturnValue=True))
        ability = Ability(GetBombSpawnLocation='position')
        result = policy.LyraArenaDropBombPythonProfile.K2_CanActivateAbility(ability, types.SimpleNamespace(AvatarActor='avatar'), object())
        self.assertFalse(result['ReturnValue'])
        self.assertEqual(result['RelevantTags'], dict(GameplayTags=[dict(TagName=policy.FAILURE)]))
        self.assertEqual(calls[0], dict(WorldContextObject=ability, SpherePos='position', SphereRadius=32., ObjectTypes=[1], ActorClassFilter=policy.BOMB, ActorsToIgnore=[]))

    def test_free_cell_returns_empty_tags(self):
        policy = load()
        policy.lib = lambda name: types.SimpleNamespace(call_function=lambda method, **kwargs: dict(ReturnValue=False))
        value = policy.LyraArenaDropBombPythonProfile.K2_CanActivateAbility(Ability(GetBombSpawnLocation='position'), types.SimpleNamespace(AvatarActor='avatar'), object())
        self.assertEqual(value, dict(ReturnValue=True, RelevantTags={}))

    def test_failed_commit_ends_before_location_or_authority_query(self):
        policy = load()
        ability = Ability(K2_CommitAbility=False)
        self.assertFalse(policy.LyraArenaDropBombPythonProfile.UEPArenaDropBombAfterMontage(ability))
        self.assertEqual(ability.calls, [('K2_CommitAbility', ()), ('K2_EndAbility', ())])

    def test_successful_authority_commit_uses_native_spawn_and_does_not_end_early(self):
        policy = load()
        ability = Ability(K2_CommitAbility=True, K2_HasAuthority=True, GetAvatarActorFromActorInfo='avatar', GetBombSpawnLocation='position')
        policy.LyraArenaDropBombPythonProfile.UEPArenaDropBombAfterMontage(ability)
        self.assertEqual(ability.calls, [('K2_CommitAbility', ()), ('GetAvatarActorFromActorInfo', ()), ('GetBombSpawnLocation', ('avatar',)), ('K2_HasAuthority', ()), (policy.SPAWN, ('position',))])

    def test_remote_branch_remains_unconnected_in_behavior(self):
        policy = load()
        ability = Ability(K2_CommitAbility=True, K2_HasAuthority=False, GetAvatarActorFromActorInfo='avatar', GetBombSpawnLocation='position')
        policy.LyraArenaDropBombPythonProfile.UEPArenaDropBombAfterMontage(ability)
        self.assertNotIn('K2_EndAbility', [name for name, _ in ability.calls])
        self.assertNotIn(policy.SPAWN, [name for name, _ in ability.calls])

    def test_spawn_terminal_handler_ends_once_without_later_actor_reads(self):
        policy = load()
        ability = Ability()
        self.assertFalse(policy.LyraArenaDropBombPythonProfile.UEPArenaDropBombAfterSpawn(ability))
        self.assertEqual(ability.calls, [('K2_EndAbility', ())])

    def test_named_return_and_tag_outputs_are_explicit_in_both_profiles(self):
        policy = load()
        ability = Ability()
        ability.call_mixin_original = lambda *args: (False, 'native-tags')
        self.assertEqual(policy.LyraArenaDropBombBlueprintFallbackProfile.K2_CanActivateAbility(ability, 'info', 'handle'), dict(ReturnValue=False, RelevantTags='native-tags'))
        self.assertTrue(policy.LyraArenaDropBombPythonProfile.K2_CanActivateAbility.uep_named_outputs)
        self.assertTrue(policy.LyraArenaDropBombBlueprintFallbackProfile.K2_CanActivateAbility.uep_named_outputs)
