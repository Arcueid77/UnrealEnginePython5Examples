"""Actor-specific async resolution and original native factory/wait ordering."""
import importlib.util
from pathlib import Path
import sys,types,unittest
from unittest.mock import patch

helpers=types.ModuleType('uep_lyra_characters.explorer_helpers_mixin');helpers.CLASSES={'hero':'HeroClass','pawn':'PawnClass'}
previous=types.ModuleType('uep_lyra_characters.explorer_callbacks_mixin')
for name in ('LyraExplorerCallbacksPythonProfile','LyraExplorerCallbacksBlueprintFallbackProfile'):
    setattr(previous,name,type(name,(),{'Method'+str(i):lambda self:None for i in range(12)}))
waiting=types.ModuleType('uep_lyra_characters.inventory_wait_mixin');waiting.RESUME='UEPInventoryWaitResume';waiting.advance=lambda a,s:None;waiting.resume=lambda a,s:None;waiting.evidence=lambda a:dict(pending=[True]*3,fallback_resumes=0)
ready=types.ModuleType('uep_lyra_characters.inventory_ready_mixin');ready.evidence=lambda a:dict(python_calls=0,fallback_calls=0,immediate_grants=0,missing_controller=0,missing_inventory=0,missing_quickbar=0)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
native=types.ModuleType('unreal_engine')
classes={k:types.SimpleNamespace(functions=lambda k=k:['OnTeamChanged_'+k,'OnReady_'+k],get_path_name=lambda k=k:k) for k in helpers.CLASSES.values()}
native.find_class=lambda n:classes[n];native.describe_function=lambda c,n:dict(owner=c.get_path_name())
spec=importlib.util.spec_from_file_location('uep_lyra_characters._explorer_init_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/explorer_init_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_characters.explorer_helpers_mixin':helpers,'uep_lyra_characters.explorer_callbacks_mixin':previous,'uep_lyra_characters.inventory_wait_mixin':waiting,'uep_lyra_characters.inventory_ready_mixin':ready}):spec.loader.exec_module(policy)

class ExplorerInitPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.proxy=types.SimpleNamespace(call_function=lambda f:self.calls.append(('proxy',f)))
        self.actor=types.SimpleNamespace(call_function=self.call,get_class=lambda:classes['HeroClass'],call_mixin_original=lambda f,*a:self.calls.append(('original',f,*a)))
        policy.ue=native;native.find_class=lambda n:classes[n] if n in classes else types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.factory));native.describe_function=lambda c,n:dict(owner=c.get_path_name())
    def call(self,f,*args):self.calls.append(('actor',f,*args));return True if f=='HasAuthority' else None
    def factory(self,f,*args):self.calls.append(('factory',f,*args));return self.proxy
    def test_each_actor_resolves_its_original_symbols(self):
        hero=vars(policy.LyraExplorerInitHeroPythonProfile)['PythonObservedTeamChanged'];pawn=vars(policy.LyraExplorerInitPawnPythonProfile)['PythonObservedTeamChanged'];self.assertEqual(hero.override,'OnTeamChanged_HeroClass');self.assertEqual(pawn.override,'OnTeamChanged_PawnClass')
    def test_ambiguous_or_missing_original_callback_rejected(self):
        for names in ([],['OnReady_1','OnReady_2']):
            with self.assertRaises(RuntimeError):policy.resolve(types.SimpleNamespace(functions=lambda:names,get_path_name=lambda:'Own'),'experience')
    def test_listener_factory_bind_then_activate_and_no_proxy_root(self):
        policy.listen(self.actor);self.assertEqual([x[:2] for x in self.calls],[('factory','ObserveTeamColors'),('actor',policy.TEAM_BIND),('proxy','Activate')])
    def test_each_listener_call_creates_a_fresh_factory_request(self):
        policy.listen(self.actor);policy.listen(self.actor);self.assertEqual(sum(c[0]=='factory' for c in self.calls),2)
    def test_no_team_result_does_not_forward(self):policy.observed(self.actor,False,-1,None);self.assertEqual(self.calls,[])
    def test_assigned_team_result_forwards_exact_payload(self):
        display=types.SimpleNamespace(get_path_name=lambda:'display');policy.observed(self.actor,True,7,display);self.assertEqual(self.calls,[('actor','OnTeamOrCosmeticsChanged',7,display)])
    def test_fallback_uses_current_actor_generated_name(self):policy.observed_fallback(self.actor,False,-1,None);self.assertEqual(self.calls,[('original','OnTeamChanged_HeroClass',False,-1,None)])
    def test_possession_ignores_null_controller_payload_but_requires_authority(self):
        policy.possessed(self.actor,None);self.assertEqual([x[1] for x in self.calls],['HasAuthority','WaitForExperienceReady',policy.EXPERIENCE_BIND,'Activate'])
    def test_readiness_calls_native_wait_policy_from_first_checkpoint(self):
        calls=[];waiting.advance=lambda a,s:calls.append((a,s));policy.experience(self.actor);self.assertEqual(calls,[(self.actor,0)])
    def test_fallback_resume_checks_linkage_and_resolves_own_callback(self):
        policy.resume_fallback(self.actor,2);self.assertEqual(self.calls,[('original','OnReady_HeroClass')])
        with self.assertRaises(ValueError):policy.resume_fallback(self.actor,3)
    def test_complete_local_profile_family(self):
        for cls in (policy.LyraExplorerInitHeroPythonProfile,policy.LyraExplorerInitHeroBlueprintFallbackProfile,policy.LyraExplorerInitPawnPythonProfile,policy.LyraExplorerInitPawnBlueprintFallbackProfile):self.assertEqual(sum(callable(f) for n,f in vars(cls).items() if not n.startswith('__')),17)
