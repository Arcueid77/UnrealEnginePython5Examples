"""Exact native Pop target and Original fallback for the two Explorer screens."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
calls=[];library=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');library.lib=lambda name:types.SimpleNamespace(call_function=lambda method,*args:calls.append((name,method,*args)))
spec=importlib.util.spec_from_file_location('_explorer_screen_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/explorer_screens_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_weapons.hero_burst_cue_mixin':library}):spec.loader.exec_module(policy)
class ExplorerScreenPolicyTests(unittest.TestCase):
    def setUp(self):calls.clear()
    def test_python_passes_exact_self_to_original_native_function(self):
        actor=types.SimpleNamespace();policy.LyraExplorerScreenPythonProfile.BP_OnDeactivated(actor);self.assertEqual(calls,[('CommonUIExtensions','PopContentFromLayer',actor)]);self.assertEqual(policy.evidence(actor),dict(python=1,fallback=0))
    def test_fallback_executes_original_deactivation_only(self):
        actor=types.SimpleNamespace(call_mixin_original=lambda name:calls.append(('original',name)));policy.LyraExplorerScreenBlueprintFallbackProfile.BP_OnDeactivated(actor);self.assertEqual(calls,[('original','BP_OnDeactivated')]);self.assertEqual(policy.evidence(actor),dict(python=0,fallback=1))
    def test_one_original_method_per_profile(self):
        for cls in (policy.LyraExplorerScreenPythonProfile,policy.LyraExplorerScreenBlueprintFallbackProfile):self.assertEqual([n for n,v in vars(cls).items() if callable(v)],['BP_OnDeactivated'])
