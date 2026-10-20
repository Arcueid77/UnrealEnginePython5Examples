"""Source message order, unfiltered/missing fragment, visibility and native bind."""
import unittest,types
from uep_lyra_hud import explorer_item_list_mixin as policy
def widget(count=0,fragment='fragment'):
    calls=[];view=types.SimpleNamespace(call_function=lambda name,*args:calls.append((name,*args)) or (count if name=='GetNumItems' else None));box=types.SimpleNamespace(call_function=lambda name,*args:calls.append((name,*args)))
    def call(name,*args):calls.append((name,*args));return fragment if name==policy.FIND else 'new-entry' if name==policy.CREATE else None
    w=types.SimpleNamespace(get_property=lambda name:view if name=='ToastListWidget' else box,call_function=call,call_mixin_original=lambda name,*args:calls.append(('original',name,*args)));return w,calls
class ExplorerItemListPolicyTests(unittest.TestCase):
    def test_construct_updates_visibility_before_native_listen(self):
        w,calls=widget();policy.construct(w);self.assertEqual(calls,[('UpdateDisplayVisibility',),(policy.LISTEN,)])
    def test_positive_finds_creates_adds_then_updates(self):
        w,calls=widget();self.assertFalse(policy.message(w,'foreign-inventory-item',3));self.assertEqual(calls,[(policy.FIND,'foreign-inventory-item'),(policy.CREATE,'fragment',3),('AddItem','new-entry'),('UpdateDisplayVisibility',)])
    def test_zero_and_negative_still_find_before_ignoring(self):
        for delta in (0,-3):
            w,calls=widget();policy.message(w,'item',delta);self.assertEqual(calls,[(policy.FIND,'item')])
    def test_missing_fragment_positive_preserves_source_unguarded_create(self):
        w,calls=widget(fragment=None);policy.message(w,'no-icon-item',2);self.assertEqual(calls[1],(policy.CREATE,None,2));self.assertEqual(calls[-1],('UpdateDisplayVisibility',))
    def test_null_item_is_passed_to_original_native_lookup(self):
        w,calls=widget();policy.message(w,None,0);self.assertEqual(calls,[(policy.FIND,None)])
    def test_empty_and_nonempty_visibility(self):
        for count,expected in ((0,1),(-1,1),(1,0),(3,0)):
            w,calls=widget(count);policy.visibility(w);self.assertEqual(calls,[('GetNumItems',),('SetVisibility',expected)])
    def test_removal_always_updates_even_for_null(self):
        w,calls=widget();policy.remove(w,None);self.assertEqual(calls,[('RemoveItem',None),('UpdateDisplayVisibility',)])
    def test_entry_item_is_unused_and_native_binder_receives_widget(self):
        w,calls=widget();policy.bind(w,'unused-item',None);self.assertEqual(calls,[(policy.BIND,None)])
    def test_fallback_preserves_original_functions_and_message_branch(self):
        w,calls=widget();cls=policy.LyraExplorerItemListBlueprintFallbackProfile;cls.Construct(w);cls.UpdateDisplayVisibility(w);cls.RemoveToast(w,'entry');cls.EntryInitialized(w,'item','row');self.assertTrue(cls.InventoryChanged(w,'source',1));self.assertEqual(calls,[('original','Construct'),('original','UpdateDisplayVisibility'),('original','RemoveToast','entry'),('original',policy.BOUND,'item','row')])
    def test_complete_five_method_families(self):
        for cls in (policy.LyraExplorerItemListPythonProfile,policy.LyraExplorerItemListBlueprintFallbackProfile):self.assertEqual(sum(callable(v) for v in vars(cls).values()),5)
