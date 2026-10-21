import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
def load():
    unreal=types.ModuleType('unreal_engine');unreal.FLinearColor=lambda *v:v;unreal.load_class=lambda v:v;structs=types.ModuleType('unreal_engine.structs')
    class Tag:
        def __init__(self,TagName=''):self.TagName=TagName
        def clone(self):return Tag(self.TagName)
    structs.GameplayTag=Tag;structs.GameplayCueParameters=lambda **kw:types.SimpleNamespace(**kw)
    spec=importlib.util.spec_from_file_location('arena_phase_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/arena_phases_mixin.py');p=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'unreal_engine':unreal,'unreal_engine.structs':structs}):spec.loader.exec_module(p)
    return p
class ArenaPhasePolicyTests(unittest.TestCase):
    def test_original_true_skip_branch_does_nothing(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:True);p.subsystem=lambda *a:None;w=types.SimpleNamespace(call_function=lambda *a:calls.append(a));p.LyraArenaWarmupPythonProfile.K2_ActivateAbility(w);self.assertEqual(calls,[]);self.assertEqual(p.evidence(w)['skip_noops'],1)
    def test_regular_activation_applies_effect_then_cue_then_original_native_wait(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:False);p.subsystem=lambda *a:types.SimpleNamespace(call_function=lambda *a:calls.append(a));w=types.SimpleNamespace(get_property=lambda n:3.,call_function=lambda *a:calls.append(a));p.LyraArenaWarmupPythonProfile.K2_ActivateAbility(w);self.assertEqual([v[0] for v in calls],['ApplyEffectToAll','ActivateUserFacingCue',p.WARM_WAIT]);self.assertEqual(calls[1][1].TagName,p.CUE);self.assertEqual(calls[1][2].RawMagnitude,3.);self.assertEqual(calls[1][2].GameplayEffectLevel,1)
    def test_clear_valid_tag_removes_native_cue_then_clears_property(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda method,*a:True if method=='IsGameplayTagValid' else 'GS' if method=='GetGameState' else calls.append((method,*a)));w=types.SimpleNamespace(get_property=lambda n:p.GameplayTag(TagName=p.CUE),set_property=lambda *a:calls.append(a));p.LyraArenaWarmupPythonProfile.ClearUserFacingCue(w);self.assertEqual(calls[0][0],'RemoveGameplayCueOnActor');self.assertEqual(calls[0][-1].RawMagnitude,0.);self.assertEqual(calls[-1][0],'Active User Facing Cue');self.assertEqual(calls[-1][1].TagName,'')
    def test_invalid_cue_does_not_remove_or_clear(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:False);w=types.SimpleNamespace(get_property=lambda n:p.GameplayTag(),set_property=lambda *a:calls.append(a));p.LyraArenaWarmupPythonProfile.ClearUserFacingCue(w);self.assertEqual(calls,[])
    def test_cue_activation_keeps_clear_store_add_order(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda method,*a:'GS' if method=='GetGameState' else calls.append((method,*a)));w=types.SimpleNamespace(call_function=lambda *a:calls.append(a),set_property=lambda *a:calls.append(a));tag=p.GameplayTag(TagName=p.CUE);p.LyraArenaWarmupPythonProfile.ActivateUserFacingCue(w,tag,p.params(3));self.assertEqual([v[0] for v in calls],['ClearUserFacingCue','Active User Facing Cue','AddGameplayCueOnActor'])
    def test_warmup_completion_clears_removes_and_starts_playing_once(self):
        p=load();calls=[];p.subsystem=lambda *a:types.SimpleNamespace(call_function=lambda *a:calls.append(a));w=types.SimpleNamespace(call_function=lambda *a:calls.append(a));self.assertIs(p.LyraArenaWarmupPythonProfile.AfterWait(w),False);self.assertEqual([v[0] for v in calls],['ClearUserFacingCue','RemoveEffectFromAll',p.PLAY])
    def test_postgame_uses_native_wait_then_travel_and_keeps_empty_end_native(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:calls.append(a[0]));w=types.SimpleNamespace(call_function=lambda *a:calls.append(a[0]));p.LyraArenaPostgamePythonProfile.K2_ActivateAbility(w);self.assertEqual(calls,[p.POST_WAIT]);self.assertIs(p.LyraArenaPostgamePythonProfile.AfterWait(w),False);self.assertEqual(calls[-1],'PlayNextGame');self.assertNotIn('K2_OnEndAbility',vars(p.LyraArenaPostgamePythonProfile))
    def test_fallback_end_payload_and_native_continuation_boolean(self):
        p=load();calls=[];w=types.SimpleNamespace(call_mixin_original=lambda *a:calls.append(a));p.LyraArenaWarmupBlueprintFallbackProfile.K2_OnEndAbility(w,True);self.assertEqual(calls,[('K2_OnEndAbility',True)]);self.assertIs(p.LyraArenaWarmupBlueprintFallbackProfile.AfterWait(w),True);self.assertIs(p.LyraArenaPostgameBlueprintFallbackProfile.AfterWait(w),True)
