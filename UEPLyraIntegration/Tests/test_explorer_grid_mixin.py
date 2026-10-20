"""Snapshot/listen sequence and exact original inventory-message branch order."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('_explorer_grid_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/explorer_grid_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':types.SimpleNamespace(find_class=lambda name:name)}):spec.loader.exec_module(policy)
def widget():
    calls=[];inventory=types.SimpleNamespace(call_function=lambda name:calls.append((name,)) or ['one','two']);controller=types.SimpleNamespace(call_function=lambda name,cls:calls.append((name,cls)) or inventory);tiles=types.SimpleNamespace(call_function=lambda name,*args:calls.append((name,*args)));props={'TileViewWidget':tiles};w=types.SimpleNamespace(get_property=props.get,set_property=lambda n,v:(props.__setitem__(n,v),calls.append(('store',n,v))),call_function=lambda name:calls.append((name,)) or (controller if name=='GetOwningPlayer' else None),call_mixin_original=lambda name:calls.append(('original',name)));return w,calls,props,inventory
class ExplorerGridPolicyTests(unittest.TestCase):
    def test_natural_construct_uses_owning_controller_and_snapshots_before_listen(self):
        w,calls,props,inventory=widget();policy.construct(w);self.assertEqual(props['NewVar_0'],inventory);self.assertEqual([c[0] for c in calls],['GetOwningPlayer','GetComponentByClass','store','ClearListItems','GetAllItems','AddItem','AddItem',policy.LISTEN]);self.assertEqual(calls[1],('GetComponentByClass','LyraInventoryManagerComponent'));self.assertEqual(calls[5:7],[('AddItem','one'),('AddItem','two')])
    def test_new_stack_adds_exact_instance(self):
        w,calls,_,_=widget();self.assertFalse(policy.message(w,'foreign-instance',3,3));self.assertEqual(calls,[('AddItem','foreign-instance')])
    def test_zero_equality_adds_before_zero_removal(self):
        w,calls,_,_=widget();policy.message(w,'zero',0,0);self.assertEqual(calls,[('AddItem','zero')])
    def test_negative_equality_adds(self):
        w,calls,_,_=widget();policy.message(w,'negative',-2,-2);self.assertEqual(calls,[('AddItem','negative')])
    def test_zero_with_negative_delta_removes(self):
        w,calls,_,_=widget();policy.message(w,'removed',0,-3);self.assertEqual(calls,[('RemoveItem','removed')])
    def test_existing_stack_changes_do_not_rebuild_list(self):
        for new,delta in ((5,2),(2,-3)):
            w,calls,_,_=widget();policy.message(w,'existing',new,delta);self.assertEqual(calls,[])
    def test_null_instance_is_left_to_native_list_api(self):
        w,calls,_,_=widget();policy.message(w,None,1,1);self.assertEqual(calls,[('AddItem',None)])
    def test_fallback_construct_keeps_original(self):
        w,calls,_,_=widget();policy.LyraExplorerGridBlueprintFallbackProfile.Construct(w);self.assertEqual(calls,[('original','Construct')])
    def test_fallback_callback_runs_original_branch(self):
        w,calls,_,_=widget();self.assertTrue(policy.LyraExplorerGridBlueprintFallbackProfile.InventoryChanged(w,'item',0,0));self.assertEqual(calls,[]);self.assertEqual(policy.evidence(w)['payloads'],[[0,0]])
    def test_complete_two_method_profile_families(self):
        for cls in (policy.LyraExplorerGridPythonProfile,policy.LyraExplorerGridBlueprintFallbackProfile):self.assertEqual([n for n,v in vars(cls).items() if callable(v)],['Construct','InventoryChanged'])
