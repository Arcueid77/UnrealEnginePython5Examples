import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_weapons.spawning_destroyed_target_contract import PLAN,FORBIDDEN,validate
from uep_lyra_hud.startup import validation_module

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',expected_cue_class='retained-native-class',pairs=[])
    r.update(dict.fromkeys(FORBIDDEN,False));r.update(dict.fromkeys(('owned_actors_destroyed','owned_effects_removed','owned_watchers_cancelled','production_profiles_restored','original_health_unchanged'),True))
    for i,p in enumerate(PLAN):
        r['pairs'].append(dict(name=p[0],profiles=['BlueprintFallback','Python'],actual_cue_classes=[r['expected_cue_class']]*2,initial_application_entries=[1,1],initial_team_entries=[1,1],initial_fx_counts=[2,2],watchers_native_active=True,initial_system_configuration=True,natural_samples=3,paired_native_state_matches=True,native_clocks_match=True,
            native_target_destroyed=[True,True],invalid_cached_target_reproduced=[True,True],cached_target_identity_retained=[True,True],removal_target_argument_null=True,removal_entries=[1,1],removal_cleared_caches=True,removal_cancelled_watchers=True,removal_retained_source_handles=True,native_clock_playing_at_destroy=[i==0]*2,native_clock_flags_after_removal=[i==0]*2,quiet_seconds=.9,effects_stayed_empty=True,diagnostic_fallbacks=[0,0],post_destroy_updates=[30,30] if i==0 else [0,0],final_spawn_times=[1.,1.]))
    return r
class SpawningDestroyedTargetContractTests(unittest.TestCase):
    def test_existing_startup_routes_only_explicit_non_commandlet_flag(self):
        self.assertEqual(validation_module(['-UEPSpawningDestroyedResult=r']),'uep_lyra_weapons.spawning_destroyed_target_validation')
        self.assertIsNone(validation_module([]));self.assertIsNone(validation_module(['-run=foo','-UEPSpawningDestroyedResult=r']))
    def test_complete_live_and_finished_native_pairs(self):self.assertEqual(validate(report())['native_target_destructions'],4)
    def test_real_destroyed_cached_reference_cannot_be_skipped(self):
        for field in ('native_target_destroyed','invalid_cached_target_reproduced','cached_target_identity_retained'):
            r=report();r['pairs'][0][field]=[True,False]
            with self.assertRaises(RuntimeError):validate(r)
    def test_null_input_does_not_replace_destroyed_cache_or_original_class(self):
        for field,value in (('actual_cue_classes',['retained-native-class','mock']),('profiles',['Python','Python']),('removal_target_argument_null',False)):
            r=report();r['pairs'][0][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_clear_cache_cancel_and_source_handles_all_required(self):
        for field in ('removal_cleared_caches','removal_cancelled_watchers','removal_retained_source_handles','effects_stayed_empty'):
            r=report();r['pairs'][1][field]=False
            with self.assertRaises(RuntimeError):validate(r)
    def test_post_removal_native_clock_cannot_be_stopped_or_replayed(self):
        for index,field,value in ((0,'native_clock_flags_after_removal',[False,False]),(0,'post_destroy_updates',[0,0]),(1,'post_destroy_updates',[1,1]),(0,'final_spawn_times',[.5,.5])):
            r=report();r['pairs'][index][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_shortcuts_and_missing_pair_rejected(self):
        for field in FORBIDDEN:
            r=report();r[field]=True
            with self.assertRaises(RuntimeError):validate(r)
        r=report();r['pairs'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_failed_native_states_or_fixture_cleanup_rejected(self):
        for field,value in (('status','failed'),('original_health_unchanged',False),('production_profiles_restored',False)):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
