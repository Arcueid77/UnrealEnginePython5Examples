import unittest
from uep_lyra_abilities.explorer_marker_contract import CASES,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,cases=[],primary_player_inventory_and_health_unchanged=True,owned_contexts_target_actors_roots_and_selectors_restored=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for profile in ('BlueprintFallback','Python'):
        for name in CASES:
            hit=name in ('hit','switched-reactivation-hit');retry=name=='retry-while-miss-active';c=dict(profile=profile,name=name,native_activation_succeeded=True,activation_delta=0 if retry else 1,data_delta=0 if retry else 1,draw_delta=int(hit),has_actor=hit,has_endpoint=True,expected_box_in_target_data=hit,ability_still_active=not hit,draw_center_matches_target_endpoint=hit,current_profile_used=True,native_target_actors_and_tasks_closed=True,native_reactivation_rejected=True);r['cases'].append(c)
    return r
class ExplorerMarkerContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_marker_cases'],8)
    def test_missing_retry_case_rejected(self):
        r=report();r['cases'].pop(2)
        with self.assertRaises(RuntimeError):validate(r)
    def test_miss_ending_or_drawing_rejected(self):
        for key,value in (('draw_delta',1),('ability_still_active',False)):
            r=report();r['cases'][1][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_hit_wrong_actor_or_center_rejected(self):
        for key in ('expected_box_in_target_data','draw_center_matches_target_endpoint'):
            r=report();r['cases'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_retrigger_after_miss_must_stay_rejected(self):
        r=report();r['cases'][2]['native_reactivation_rejected']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_target_leak_or_replay_claim_rejected(self):
        r=report();r['cases'][0]['native_target_actors_and_tasks_closed']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['target_data_callbacks_replayed']=True
        with self.assertRaises(RuntimeError):validate(r)
