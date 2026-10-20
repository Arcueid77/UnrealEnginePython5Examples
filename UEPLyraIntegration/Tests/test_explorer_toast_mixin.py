"""Source cast/store/icon/FText/timer order and actual multicast payload."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('_explorer_toast_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/explorer_toast_mixin.py');policy=importlib.util.module_from_spec(spec);validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None and getattr(obj,'alive',True)
with patch.dict(sys.modules,{'unreal_engine':types.SimpleNamespace(load_class=lambda name:name),'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)
def widget():
    calls=[];props={};image=types.SimpleNamespace(call_function=lambda name,*args:calls.append((name,*args)));props['ItemIconWidget']=image;w=types.SimpleNamespace(get_property=props.get,set_property=lambda name,value:(props.__setitem__(name,value),calls.append(('store',name,value))),call_function=lambda name,*args:calls.append((name,*args)),broadcast=lambda name,*args:calls.append(('broadcast',name,*args)),call_mixin_original=lambda name,*args:calls.append(('original',name,*args)));return w,calls,props
def entry(texture='icon'):
    def get(name):
        if name!='IconToShow':raise AssertionError('Python must not read native FText or timer duration')
        return texture
    return types.SimpleNamespace(is_a=lambda cls:cls==policy.ENTRY,get_property=get)
class ExplorerToastPolicyTests(unittest.TestCase):
    def test_valid_item_order_and_native_opaque_payload(self):
        w,calls,props=widget();item=entry();policy.item(w,item);self.assertEqual(calls,[('store','ItemPtr',item),('SetIcon','icon'),(policy.WRITE,item),(policy.START,item)]);self.assertIs(props['ItemPtr'],item)
    def test_invalid_cast_retains_current_item_and_timer(self):
        for value in (None,types.SimpleNamespace(is_a=lambda cls:False)):
            w,calls,props=widget();props['ItemPtr']='old';policy.item(w,value);self.assertEqual(calls,[]);self.assertEqual(props['ItemPtr'],'old')
    def test_valid_icon_does_not_match_size_and_is_visible(self):
        w,calls,_=widget();policy.icon(w,'texture');self.assertEqual(calls,[('SetBrushFromTexture','texture',False),('SetVisibility',0)])
    def test_invalid_icon_is_hidden(self):
        w,calls,_=widget();policy.icon(w,None);self.assertEqual(calls,[('SetBrushFromTexture',None,False),('SetVisibility',2)])
    def test_expiry_broadcasts_current_item(self):
        w,calls,props=widget();props['ItemPtr']='newest';policy.expired(w);self.assertEqual(calls,[('broadcast','OnToastExpired','newest')])
    def test_expiry_keeps_native_null_payload(self):
        w,calls,_=widget();policy.expired(w);self.assertEqual(calls,[('broadcast','OnToastExpired',None)])
    def test_fallback_methods_use_exact_originals(self):
        w,calls,_=widget();cls=policy.LyraExplorerToastBlueprintFallbackProfile;cls.OnListItemObjectSet(w,'entry');cls.SetIcon(w,None);cls.OnTimerElapsed(w);self.assertEqual(calls,[('original','OnListItemObjectSet','entry'),('original','SetIcon',None),('original','OnTimerElapsed')])
    def test_complete_three_method_families(self):
        for cls in (policy.LyraExplorerToastPythonProfile,policy.LyraExplorerToastBlueprintFallbackProfile):self.assertEqual([n for n,v in vars(cls).items() if callable(v)],['OnListItemObjectSet','SetIcon','OnTimerElapsed'])
