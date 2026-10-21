import importlib.util,types,unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('arena_ready_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/arena_ready_mixin.py');policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)

class ArenaReadyPolicyTests(unittest.TestCase):
    def test_construct_only_plays_original_animation_forward_at_source_defaults(self):
        animation=object();calls=[];w=types.SimpleNamespace(get_property=lambda name:animation,call_function=lambda *a:calls.append(a));policy.LyraArenaReadyPythonProfile.Construct(w);self.assertEqual(calls,[('PlayAnimationForward',animation,1.,False)]);self.assertEqual(policy.evidence(w),dict(python_constructs=1,fallback_constructs=0,plays=1))
    def test_fallback_calls_untouched_construct_once(self):
        calls=[];w=types.SimpleNamespace(call_mixin_original=lambda *a:calls.append(a));policy.LyraArenaReadyBlueprintFallbackProfile.Construct(w);self.assertEqual(calls,[('Construct',)]);self.assertEqual(policy.evidence(w)['plays'],0)
    def test_empty_preconstruct_and_tick_are_not_python_noops(self):
        for cls in (policy.LyraArenaReadyPythonProfile,policy.LyraArenaReadyBlueprintFallbackProfile):self.assertEqual([n for n,v in vars(cls).items() if callable(v)],['Construct'])
