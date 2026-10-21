"""HasActor decision, never HasEndPoint, and original native draw/end ordering."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
queries=[];helper=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin')
def call(name,data,index):
    queries.append(name)
    if name=='TargetDataHasActor':return data.actor
    if name=='GetTargetDataEndPoint':return data.point
    raise AssertionError('source must not use endpoint existence as its decision')
helper.lib=lambda name:types.SimpleNamespace(call_function=call);spec=importlib.util.spec_from_file_location('_explorer_marker_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_abilities/explorer_marker_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_weapons.hero_burst_cue_mixin':helper}):spec.loader.exec_module(policy)
def ability():
    calls=[];a=types.SimpleNamespace(call_function=lambda name,*args:calls.append((name,*args)),call_mixin_original=lambda name,*args:calls.append(('original',name,*args)));return a,calls
class ExplorerMarkerPolicyTests(unittest.TestCase):
    def setUp(self):queries.clear()
    def test_activation_only_starts_original_native_instant_target_task(self):
        a,calls=ability();policy.activate(a);self.assertEqual(calls,[(policy.START,)])
    def test_no_actor_does_not_draw_end_or_query_endpoint(self):
        a,calls=ability();data=types.SimpleNamespace(actor=False,point='valid-endpoint',clone=lambda:'owned-copy');self.assertFalse(policy.data(a,data));self.assertEqual(calls,[]);self.assertEqual(queries,['TargetDataHasActor']);self.assertEqual(policy.evidence(a)['last_data'],'owned-copy')
    def test_actor_hit_gets_endpoint_draws_then_ends(self):
        a,calls=ability();data=types.SimpleNamespace(actor=True,point='end',clone=lambda:'owned-copy');self.assertFalse(policy.data(a,data));self.assertEqual(queries,['TargetDataHasActor','GetTargetDataEndPoint']);self.assertEqual(calls,[(policy.DRAW,'end'),('K2_EndAbility',)])
    def test_draw_executes_original_node_with_exact_center(self):
        a,calls=ability();center=types.SimpleNamespace(x=1.,y=2.,z=3.);policy.draw(a,center,'python');self.assertEqual(calls,[('original',policy.DRAW,center)]);self.assertEqual(policy.evidence(a)['last_center'],[1.,2.,3.])
    def test_fallback_retains_original_activation_and_payload_branch(self):
        a,calls=ability();cls=policy.LyraExplorerMarkerBlueprintFallbackProfile;cls.K2_ActivateAbility(a);data=types.SimpleNamespace(clone=lambda:'owned-copy');self.assertTrue(cls.ValidTargetData(a,data));self.assertEqual(policy.evidence(a)['last_data'],'owned-copy');self.assertEqual(calls,[('original','K2_ActivateAbility')])
    def test_three_methods_and_no_empty_end_override(self):
        for cls in (policy.LyraExplorerMarkerPythonProfile,policy.LyraExplorerMarkerBlueprintFallbackProfile):self.assertEqual(sum(callable(v) for v in vars(cls).values()),3);self.assertNotIn('K2_OnEndAbility',vars(cls))
