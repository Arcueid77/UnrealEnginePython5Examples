"""Already-loaded-class observer models, not native Pawn-race acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

module_path=Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/lazy_pawn_lifecycle_observation.py"
helper=types.ModuleType("uep_lyra_abilities.melee_character_default_control");helper.CHARACTER="character"
readiness=types.ModuleType("uep_lyra_abilities.melee_replica_readiness")
class Watch:
    def __init__(self,*args): self.files=[];self.events=[];self.closed=False
    def poll(self): self.events.append("poll")
    def birth(self,pawn): self.events.append("birth")
    def constructed(self,pawn): self.events.append("construction")
    def reset(self,pawn):self.events.append('reset')
    def close(self): self.closed=True
readiness.EarlyWatch=Watch
spec=importlib.util.spec_from_file_location("uep_lyra_abilities._lazy_lifecycle_model",module_path)
observation=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":types.ModuleType("unreal_engine"),"uep_lyra_abilities.melee_character_default_control":helper,"uep_lyra_abilities.melee_replica_readiness":readiness}): spec.loader.exec_module(observation)


class TestLazyPawnLifecycleObservation(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        class Production:
            def ReceiveBeginPlay(pawn): self.calls.append("original-begin")
        self.original=Production;self.actual=Production;self.available=False
        self.cls=types.SimpleNamespace(get_path_name=lambda:"character")
        def registered(): return [dict(target_class=self.cls,profiles=dict(Python=dict(python_class=self.actual)))] if self.available else []
        native=types.SimpleNamespace(get_registered_mixins=registered,register_mixin_profile=lambda cls,name,value:setattr(self,"actual",value))
        item=patch.object(observation,"ue",native);item.start();self.addCleanup(item.stop)
        self.value=observation.LazyPawnLifecycleObservation(Path("unused"),"A","model");self.addCleanup(self.value.close)
    def test_wait_does_not_load_class_or_write_cdo(self):
        self.value.poll();self.assertFalse(self.value.report["installed"]);self.assertIs(self.actual,self.original)
    def test_existing_handler_runs_once_after_capture(self):
        self.available=True;self.value.poll();self.actual.ReceiveBeginPlay(object())
        self.assertEqual(self.calls,["original-begin"]);self.assertIn("birth",self.value.watch.events)
    def test_original_construction_called_once(self):
        self.available=True;self.value.poll();calls=[]
        self.actual.UserConstructionScript(types.SimpleNamespace(call_mixin_original=lambda name:calls.append(name)))
        self.assertEqual(calls,["UserConstructionScript"]);self.assertIn("construction",self.value.watch.events)
    def test_native_reset_observed_and_original_result_preserved_once(self):
        sentinel=object();calls=[]
        def reset(pawn):calls.append(pawn);return sentinel
        self.original.K2_OnReset=reset;self.available=True;self.value.poll();pawn=object()
        self.assertIs(self.actual.K2_OnReset(pawn),sentinel);self.assertEqual(calls,[pawn])
        self.assertIn('reset',self.value.watch.events);self.assertEqual(self.value.report['reset_observation_errors'],[])
    def test_native_reset_capture_error_cannot_block_production_handler(self):
        calls=[]
        self.original.K2_OnReset=lambda pawn:calls.append('original-reset')
        self.available=True;self.value.poll()
        def fail(pawn):raise RuntimeError('readonly reset capture failed')
        self.value.watch.reset=fail;self.actual.K2_OnReset(object())
        self.assertEqual(calls,['original-reset']);self.assertIn('readonly reset capture failed',self.value.report['reset_observation_errors'][0])
    def test_missing_python_reset_uses_original_native_event_once(self):
        self.available=True;self.value.poll();calls=[]
        self.actual.K2_OnReset(types.SimpleNamespace(call_mixin_original=lambda name:calls.append(name)))
        self.assertEqual(calls,['K2_OnReset'])
    def test_handler_overwrite_rejected(self):
        self.available=True;self.value.poll();self.actual=self.original
        with self.assertRaisesRegex(RuntimeError,"overwritten"): self.value.poll()
    def test_close_restores_and_does_not_read_dead_world(self):
        self.available=True;self.value.poll();self.value.close();self.value.poll();self.value.close()
        self.assertIs(self.actual,self.original);self.assertTrue(self.value.watch.closed)
        self.assertFalse(self.value.report["preloaded"]);self.assertFalse(self.value.report["cdo_written"])
