"""Explorer Spawned registration and the original parent/listen/hide order."""
import importlib.util
from pathlib import Path
import sys,types,unittest
from unittest.mock import patch

initialization=types.ModuleType('uep_lyra_characters.explorer_init_mixin');initialization.CLASSES={'hero':'Hero','pawn':'Pawn'}
for kind in initialization.CLASSES:
    for profile in ('Python','BlueprintFallback'):setattr(initialization,'LyraExplorerInit'+kind.title()+profile+'Profile',type('Base',(),{'Existing'+str(i):lambda self:None for i in range(17)}))
visibility=types.ModuleType('uep_lyra_characters.visibility_mixin');visibility.REGISTER='Register';visibility.RESUME='Resume'
visibility.LyraCharacterVisibilityPythonProfile=type('Visibility',(),{'ShowPawnAgainNextFrame':lambda self,p:None,'PythonVisibilityResume':lambda self,i:None});visibility.LyraCharacterVisibilityBlueprintFallbackProfile=type('VisibilityFallback',(),{'ShowPawnAgainNextFrame':lambda self,p:None})
beginning=types.ModuleType('uep_lyra_characters.begin_play_mixin');beginning.PARENT='ExactParent';beginning.evidence=lambda a:a.counts;beginning.LyraCharacterBeginPlayBlueprintFallbackProfile=type('BeginFallback',(),{'ReceiveBeginPlay':lambda self:None})
structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw)
spec=importlib.util.spec_from_file_location('uep_lyra_characters._explorer_begin_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/explorer_beginplay_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine.structs':structs,'uep_lyra_characters.explorer_init_mixin':initialization,'uep_lyra_characters.visibility_mixin':visibility,'uep_lyra_characters.begin_play_mixin':beginning}):spec.loader.exec_module(policy)

class ExplorerBeginPlayPolicyTests(unittest.TestCase):
    def actor(self):
        calls=[];a=types.SimpleNamespace(counts=dict(python_calls=0,fallback_calls=0,parent_calls=0,listen_calls=0,hide_calls=0,register_calls=0,order=[]),call_function=lambda f,*args:calls.append((f,*args)),get_property=lambda name:'pawn-extension' if name=='PawnExtComponent' else None);return a,calls
    def test_exact_parent_listener_hide_then_registration_order(self):
        a,calls=self.actor();policy.begin(a);self.assertEqual([c[0] for c in calls],['ExactParent','ListenForTeam','SetActorHiddenInGame','Register']);self.assertEqual(a.counts['order'],['parent','listen','hide','register'])
    def test_spawned_tag_immediate_registration_and_original_component(self):
        a,calls=self.actor();policy.begin(a);self.assertEqual(calls[-1][1],'pawn-extension');self.assertEqual(calls[-1][2].TagName,'InitState.Spawned');self.assertTrue(calls[-1][3])
    def test_hide_precedes_potential_synchronous_delegate_delivery(self):
        a,calls=self.actor();policy.begin(a);self.assertEqual(calls[2],('SetActorHiddenInGame',True))
    def test_prior_seventeen_local_methods_are_preserved(self):
        for key in initialization.CLASSES:
            for name in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraExplorerBeginPlay'+key.title()+name+'Profile');parent=getattr(initialization,'LyraExplorerInit'+key.title()+name+'Profile');self.assertEqual(sum(callable(fn) for n,fn in vars(cls).items() if not n.startswith('__')),20)
                for method in vars(parent):
                    if not method.startswith('__'):self.assertIs(vars(cls)[method],vars(parent)[method])
    def test_pending_resume_implementation_is_shared_across_profiles(self):self.assertIs(vars(policy.LyraExplorerBeginPlayHeroPythonProfile)['PythonVisibilityResume'],vars(policy.LyraExplorerBeginPlayHeroBlueprintFallbackProfile)['PythonVisibilityResume'])
