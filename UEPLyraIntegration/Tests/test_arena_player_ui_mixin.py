import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch

class ArenaPlayerUIPolicyTests(unittest.TestCase):
    def setup_policy(self,is_player=True):
        calls=[];handle=object();player_class=object();owner=types.SimpleNamespace(is_a=lambda c:c is player_class and is_player)
        subsystem=types.SimpleNamespace(call_function=lambda *a:(calls.append(('registry',)+a),handle)[1])
        def find(name):
            if name=='LyraPlayerState':return player_class
            return types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda *a:(calls.append((name,)+a),subsystem)[1]))
        unreal=types.ModuleType('unreal_engine');unreal.find_class=find;structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw)
        spec=importlib.util.spec_from_file_location('arena_player_ui_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/arena_player_ui_mixin.py');policy=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'unreal_engine':unreal,'unreal_engine.structs':structs}):spec.loader.exec_module(policy)
        properties={};component=types.SimpleNamespace(call_function=lambda name:owner,get_property=lambda name:properties[name],set_property=lambda name,value:properties.__setitem__(name,value),call_mixin_original=lambda *a:calls.append(('original',)+a))
        return policy,component,calls,handle,owner,properties
    def test_registers_actual_owner_as_global_data_at_original_priority(self):
        p,c,calls,handle,owner,values=self.setup_policy();p.LyraArenaPlayerUIPythonProfile.ReceiveBeginPlay(c)
        call=calls[-1];self.assertEqual(call[:2],('registry','K2_RegisterExtensionAsData'));self.assertEqual(call[2].TagName,p.TAG);self.assertIs(call[3],owner);self.assertEqual(call[4],-1);self.assertIs(values['ExtensionHandle'],handle)
    def test_pure_cast_failure_still_calls_native_registry_with_null_data(self):
        p,c,calls,*_=self.setup_policy(False);p.LyraArenaPlayerUIPythonProfile.ReceiveBeginPlay(c);self.assertIsNone(calls[-1][3])
    def test_unregister_does_not_reset_or_test_handle(self):
        p,c,calls,handle,owner,values=self.setup_policy();values['ExtensionHandle']=handle;p.LyraArenaPlayerUIPythonProfile.ReceiveEndPlay(c,2)
        self.assertEqual(calls,[('UIExtensionHandleFunctions','Unregister',handle)]);self.assertIs(values['ExtensionHandle'],handle)
    def test_fallback_preserves_end_reason_and_only_original_events(self):
        p,c,calls,*_=self.setup_policy();p.LyraArenaPlayerUIBlueprintFallbackProfile.ReceiveBeginPlay(c);p.LyraArenaPlayerUIBlueprintFallbackProfile.ReceiveEndPlay(c,4);self.assertEqual(calls,[('original','ReceiveBeginPlay'),('original','ReceiveEndPlay',4)])
