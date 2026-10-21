import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
def load():
    unreal=types.ModuleType('unreal_engine');unreal.load_class=lambda path:path;unreal.find_class=lambda name:name;structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw);structs.GameplayEffectContextHandle=lambda:object();native=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');native.native_outputs=lambda c,n,v:v;visibility=types.ModuleType('uep_lyra_characters.visibility_mixin');visibility.REGISTER='NativeRegister';valid=types.ModuleType('uep_lyra_world.effect_pad_mixin');valid.valid=lambda o:o is not None
    spec=importlib.util.spec_from_file_location('uep_lyra_world.arena_actor_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/arena_actor_mixin.py');p=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'unreal_engine':unreal,'unreal_engine.structs':structs,'uep_lyra_abilities.melee_trace_mixin':native,'uep_lyra_characters.visibility_mixin':visibility,'uep_lyra_world.effect_pad_mixin':valid}):spec.loader.exec_module(p)
    return p
class ArenaActorPolicyTests(unittest.TestCase):
    def test_child_begin_preserves_listen_hide_gameplayready_registration_order(self):
        p=load();calls=[];component=object();w=types.SimpleNamespace(call_function=lambda *a:calls.append(a),get_property=lambda n:component);self.assertIs(p.LyraArenaHeroPythonProfile.AfterParentBegin(w),False);self.assertEqual([v[0] for v in calls],['ListenForTeam','SetActorHiddenInGame',p.REGISTER]);self.assertEqual(calls[2][2].TagName,'InitState.GameplayReady');self.assertIs(calls[2][3],True)
    def test_team_listener_factory_bind_activate_without_dedup(self):
        p=load();calls=[];action=types.SimpleNamespace(call_function=lambda n:calls.append(n));p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:action);w=types.SimpleNamespace(call_function=lambda *a:calls.append(a[0]));p.LyraArenaHeroPythonProfile.ListenForTeam(w);p.LyraArenaHeroPythonProfile.ListenForTeam(w);self.assertEqual(calls,[p.TEAM_BIND,'Activate']*2)
    def test_invalid_team_display_noop_and_valid_includes_children(self):
        p=load();calls=[];w=types.SimpleNamespace();asset=types.SimpleNamespace(call_function=lambda *a:calls.append(a));p.LyraArenaHeroPythonProfile.Display(w,1,None);self.assertEqual(calls,[]);p.LyraArenaHeroPythonProfile.Display(w,2,asset);self.assertEqual(calls,[('ApplyToActor',w,True)])
    def test_death_cue_then_native_wait_and_native_end_only_after_callback(self):
        p=load();calls=[];w=types.SimpleNamespace(call_function=lambda *a:calls.append(a));p.LyraArenaDeathPythonProfile.Activate(w);self.assertEqual([a[0] for a in calls],['K2_ExecuteGameplayCue',p.DEATH_WAIT]);p.LyraArenaDeathPythonProfile.AfterWait(w);self.assertEqual(calls[-1],('K2_EndAbility',))
    def test_pickup_authority_change_and_remote_rep_are_opposite(self):
        p=load();calls=[];fx=object();data=types.SimpleNamespace(get_property=lambda n:fx);p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:data);vfx=types.SimpleNamespace(call_function=lambda *a:calls.append(a));w=types.SimpleNamespace(get_property=lambda n:vfx if n=='VFX' else object(),call_function=lambda n:True);p.pickup_vfx(w,False);p.pickup_vfx(w,True);self.assertEqual(calls,[('SetAsset',fx,True)])
    def test_overlap_invalid_asc_noop_and_success_applies_level_zero_before_destroy(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:None);w=types.SimpleNamespace(call_function=lambda *a:calls.append(a[0]));p.LyraArenaPickupPythonProfile.Overlap(w,object());self.assertEqual(calls,[]);asc=types.SimpleNamespace(call_function=lambda *a:calls.append(a));p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:asc);w.call_function=lambda n:True if n=='HasAuthority' else calls.append(n);w.get_property=lambda n:'Effect';p.LyraArenaPickupPythonProfile.Overlap(w,object());self.assertEqual(calls[0][:3],('BP_ApplyGameplayEffectToSelf','Effect',0.));self.assertEqual(calls[-1],'K2_DestroyActor')
