import unittest
from uep_lyra_abilities.explorer_actions_contract import MODES,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,cases=[],native_cue_recycling_enabled=True,native_cue_timer_cleanup_enabled=True,cue_pool_profiles=[dict(profile=p,cues=[dict(alive=True,hidden=True,owner_cleared=True,splines=0,lifespan=0.,release_delta=1,lifecycle=dict(python_release=1,fallback_release=0))]) for p in ('BlueprintFallback','Python')],primary_player_inventory_and_health_unchanged=True,owned_contexts_tasks_roots_and_selectors_restored=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for profile in ('BlueprintFallback','Python'):
        for kind in ('collect','sit'):
            for mode in MODES:
                c=dict(profile=profile,kind=kind,mode=mode,new_item_count=int(kind=='collect'),new_stack_counts=[2] if kind=='collect' else [],native_montage_end_callbacks=1,native_target_expired_after_three_seconds=True);c.update(dict.fromkeys(('native_interact_trace_and_nearby_grant','native_gas_event_activation','original_event_target_and_instigator_received','native_montage_playing_observed','inventory_effect_matches_source','collect_collision_lifespan_or_sit_target_preserved','native_tasks_and_montage_closed','current_completion_profile_matches','no_authority_duration_message','native_duration_transport_half_second_verified'),True));r['cases'].append(c)
    return r
class ExplorerActionsContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_action_cases'],16)
    def test_missing_action_or_mode_rejected(self):
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_pickup_count_or_stack_rejected(self):
        for key,value in (('new_item_count',2),('new_stack_counts',[1])):
            r=report();r['cases'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_missing_montage_callback_or_lifespan_rejected(self):
        for key,value in (('native_montage_end_callbacks',0),('native_target_expired_after_three_seconds',False)):
            r=report();r['cases'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_current_profile_or_native_payload_rejected(self):
        for key in ('current_completion_profile_matches','original_event_target_and_instigator_received'):
            r=report();r['cases'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_authority_false_or_full_acceptance_overclaim_rejected(self):
        for key in ('authority_false_runtime_executed','full_acceptance'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_destroyed_or_unclean_collect_cue_rejected(self):
        for key,value in (('alive',False),('splines',1),('lifespan',3.)):
            r=report();r['cue_pool_profiles'][0]['cues'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_disabling_native_pool_or_timer_cleanup_rejected(self):
        for key in ('native_cue_recycling_enabled','native_cue_timer_cleanup_enabled'):
            r=report();r[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
