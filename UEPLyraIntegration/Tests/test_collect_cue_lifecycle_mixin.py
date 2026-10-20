"""Original lifespan fallthrough with an earlier native pool-return deadline."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
calls=[];components=[];library=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');library.lib=lambda name:types.SimpleNamespace(call_function=lambda method,*args:components if method=='FindComponentsByClass' else calls.append((name,method,*args)));world=types.ModuleType('uep_lyra_world.effect_pad_mixin');world.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location('_collect_cue_lifecycle_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/collect_cue_lifecycle_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':types.SimpleNamespace(find_class=lambda name:name),'uep_lyra_weapons.hero_burst_cue_mixin':library,'uep_lyra_world.effect_pad_mixin':world}):spec.loader.exec_module(policy)
def actor():return types.SimpleNamespace(set_property=lambda name,value:calls.append(('set',name,value)),call_function=lambda name:calls.append(('native',name)),call_mixin_original=lambda name,*args:calls.append(('original',name,*args)) or True)
class CollectCueLifecycleTests(unittest.TestCase):
    def setUp(self):calls.clear();components.clear()
    def test_positive_deadline_precedes_original_lifespan_and_keeps_fallthrough(self):
        a=actor();self.assertTrue(policy.schedule(a,3.,'python'));call,=calls;self.assertEqual(call[:4],('KismetSystemLibrary','K2_SetTimer',a,policy.DEADLINE));self.assertGreater(call[4],2.998);self.assertLess(call[4],3.);self.assertEqual(call[5:],(False,False,0.,0.))
    def test_zero_clears_only_the_named_native_deadline(self):
        a=actor();policy.schedule(a,0.,'fallback');self.assertEqual(calls[0][4],0.);self.assertEqual(calls[0][3],policy.DEADLINE)
    def test_execute_forwards_original_result_and_payload(self):
        a=actor();self.assertTrue(policy.execute(a,'target','params','python'));self.assertEqual(calls[-1],('original','OnExecute','target','params'))
    def test_release_clears_only_owned_dynamic_splines_and_returns_to_manager(self):
        a=actor();owned=types.SimpleNamespace(call_function=lambda name,*args:a if name=='GetOwner' else calls.append(('owned',name,*args)));foreign=types.SimpleNamespace(call_function=lambda name,*args:'other' if name=='GetOwner' else calls.append(('foreign',name,*args)));components.extend([owned,foreign]);policy.release(a,'python');self.assertTrue(any(c[:2]==('owned','K2_DestroyComponent') for c in calls));self.assertFalse(any(c[0]=='foreign' for c in calls));self.assertEqual(calls[-1],('native','K2_EndGameplayCue'))
    def test_three_lifecycle_methods_in_both_profiles(self):
        for name in ('Python','BlueprintFallback'):self.assertEqual(sum(callable(v) for v in vars(getattr(policy,'LyraCollectCueLifecycle'+name+'Profile')).values()),3)
