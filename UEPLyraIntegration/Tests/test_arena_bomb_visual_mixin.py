import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


def load():
    unreal = types.ModuleType('unreal_engine')
    unreal.FVector = lambda x=0., y=0., z=0.: types.SimpleNamespace(x=x, y=y, z=z)
    spec = importlib.util.spec_from_file_location('arena_bomb_visual_test', Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/arena_bomb_visual_mixin.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'unreal_engine': unreal}):
        spec.loader.exec_module(module)
    module.lib = lambda name: types.SimpleNamespace(call_function=lambda n, a, b: a*b)
    return module


def actor(radii, directions):
    values = dict(DirectionalRadius=radii, DirectionsExpanding=[types.SimpleNamespace(X=x, Y=y) for x, y in directions])
    return types.SimpleNamespace(get_property=lambda name: values[name])


class ArenaBombVisualPolicyTests(unittest.TestCase):
    def test_local_array_resets_instead_of_accumulating(self):
        policy = load()
        bomb = actor([2], [(1, 0)])
        self.assertEqual(len(policy.positions(bomb)), 2)
        bomb.get_property = lambda name: []
        self.assertEqual(policy.positions(bomb), [])

    def test_duplicate_directions_use_add_unique_and_preserve_order(self):
        policy = load()
        result = policy.positions(actor([2, 3], [(1, 0), (1, 0)]))
        self.assertEqual([(v.x, v.y, v.z) for v in result], [(100., 0., 50.), (200., 0., 50.), (300., 0., 50.)])

    def test_zero_negative_and_out_of_range_direction_semantics(self):
        policy = load()
        self.assertEqual(policy.positions(actor([0, -2], [])), [])
        result = policy.positions(actor([2], []))
        self.assertEqual([(v.x, v.y, v.z) for v in result], [(0., 0., 50.)])

    def test_native_integer_multiply_overflow_is_not_python_unbounded_math(self):
        policy = load()
        calls = []
        def call(name, a, b):
            calls.append(name)
            return ((a*b+2**31) % 2**32)-2**31 if name == 'Multiply_IntInt' else a*b
        policy.lib = lambda name: types.SimpleNamespace(call_function=call)
        result = policy.positions(actor([2], [(2**30, 0)]))
        self.assertEqual(result[-1].x, -(2**31)*100.)
        self.assertEqual(calls.count('Multiply_IntInt'), 4)

    def test_visuals_keep_audio_before_array_and_reset_only_niagara(self):
        policy = load()
        calls = []
        component = lambda name: types.SimpleNamespace(call_function=lambda method, *args: calls.append((name, method, args)))
        values = dict(ExplosionAudio=component('audio'), NS_BombFuse1=component('niagara'), DirectionsExpanding=[], DirectionalRadius=[])
        policy.lib = lambda name: component(name)
        policy.LyraArenaBombVisualPythonProfile.ClientUpdateFireballVisuals(types.SimpleNamespace(get_property=lambda name: values[name]))
        self.assertEqual([(name, method) for name, method, _ in calls], [('audio', 'Activate'), ('NiagaraDataInterfaceArrayFunctionLibrary', 'SetNiagaraArrayVector'), ('niagara', 'Activate')])
        self.assertEqual(calls[0][2], (False,))
        self.assertEqual(calls[-1][2], (True,))

    def test_construct_uses_real_time_and_one_shared_mid(self):
        policy = load()
        calls = []
        material = types.SimpleNamespace(call_function=lambda name, *args: calls.append((name, args)))
        sphere = types.SimpleNamespace(call_function=lambda name, *args: material)
        cylinder = types.SimpleNamespace(call_function=lambda name, *args: calls.append((name, args)))
        values = dict(SphereMesh=sphere, CylinderMesh=cylinder, BombLifespan=7.)
        bomb = types.SimpleNamespace(get_property=lambda name: values[name], set_property=lambda name, value: values.__setitem__(name, value))
        policy.lib = lambda name: types.SimpleNamespace(call_function=lambda method, obj: 123. if method == 'GetRealTimeSeconds' else self.fail(method))
        self.assertFalse(policy.LyraArenaBombVisualPythonProfile.UEPArenaBombConstructVisuals(bomb))
        self.assertIs(values['BombMID'], material)
        self.assertEqual(calls, [('SetMaterial', (0, material)), ('SetScalarParameterValue', ('InitialTime', 123.)), ('SetScalarParameterValue', ('BombLifespan', 7.))])
