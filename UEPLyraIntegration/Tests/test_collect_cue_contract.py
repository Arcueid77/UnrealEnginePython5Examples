import unittest
from uep_lyra_weapons.collect_cue_contract import CASES,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,cases=[],primary_player_inventory_health_and_transform_unchanged=True,owned_actor_roots_and_class_selectors_restored=True,native_cue_recycling_and_timer_cleanup_enabled=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for profile in ('BlueprintFallback','Python'):
        for name,*_ in CASES:
            c=dict(profile=profile,name=name,samples=4,actual_native_update_count=4,native_finish_count=1,native_timeline_length=5.);c.update(dict.fromkeys(('native_manager_executed_exact_class','source_target_collision_and_lifespan_set','pool_actor_alive_hidden_ownerless_and_resource_free','original_spline_points_and_world_attachment_match','native_play_rate_matches_source','all_samples_match_native_spline_distance_and_uniform_scale','all_samples_match_original_native_curves','native_finished_hides_then_retains_self_three_seconds','pending_profile_switch_used_current_update_and_finish','zero_rate_preserves_stalled_native_timeline','invalid_pawn_no_timeline','self_lifespan_cleared'),True));r['cases'].append(c)
    return r
class CollectCueContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_collect_cue_cases'],14)
    def test_missing_socket_case_rejected(self):
        r=report();r['cases'].pop(3)
        with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_geometry_or_original_curve_rejected(self):
        for key in ('original_spline_points_and_world_attachment_match','all_samples_match_original_native_curves'):
            r=report();r['cases'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_few_samples_or_duplicate_finish_rejected(self):
        for key,value in (('samples',1),('native_finish_count',2)):
            r=report();r['cases'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_pool_destruction_or_clock_replay_claim_rejected(self):
        r=report();r['cases'][0]['pool_actor_alive_hidden_ownerless_and_resource_free']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['timeline_callbacks_replayed']=True
        with self.assertRaises(RuntimeError):validate(r)
