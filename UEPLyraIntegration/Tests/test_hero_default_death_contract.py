import copy,unittest
from uep_lyra_characters.hero_default_death_contract import KINDS,SCENARIOS,FALSE_FIELDS,TRUE_FIELDS,validate

def report():
    r=dict(status='passed',error=None,cases=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in ('BlueprintFallback','Python'):
        for k in KINDS:
            for n in (SCENARIOS if k=='parent' else ('default',)):
                py=p=='Python';gone=n=='destroy-pending';counts=dict(python_calls=int(py),fallback_calls=int(not py),delay_requests=int(py),montage_calls=int(py),unregister_calls=int(py),missing_sense_noops=0,resumes=int(py and not gone),death_forwards=int(py and not gone),hide_forwards=int(py and not gone),ragdoll_forwards=int(py and not gone),last_start=dict(duration=.2,owning_actor='Owned',game_seconds=0.),last_resume=dict(game_seconds=.2),trace=[dict(event=e) for e in (['montage','sight','delay']+([] if gone else ['resume','ragdoll','hide','death']) if py else ['fallback'])]);montages=[] if n=='empty-montages' else ['Montage']
                r['cases'].append(dict(profile=p,kind=k,name=n,counts=counts,native_lethal_gas_producer=True,native_health_after=0,native_delegate_callbacks=1,native_delegate_payload_matches_actor=True,target_function_is_parent_router=True,original_montages_restored=True,owned_context_destroyed=True,owned_actor_not_rooted=True,source_sight_removed=True,other_senses_unchanged=True,prefix_current_montage=montages[0] if montages else None,configured_montages=montages,actor_path='Owned',observed_after_destroy_game_seconds=.8,no_late_work_after_destroy=True,ragdoll_calls=0 if gone else 1,hide_calls=0 if gone else 1,all_owned_weapon_actors_hidden=True,native_ragdoll_collision_and_simulation=True,endpoint_game_seconds=.2,entry_game_seconds=0.,maximum_world_delta=.017,profile_before_resume=('Python' if p=='BlueprintFallback' else 'BlueprintFallback') if n=='switch-pending' else p,endpoint_profile_matches_switch=True))
    return r

class HeroDefaultDeathContractTests(unittest.TestCase):
    def test_complete_native_health_matrix(self):self.assertEqual(validate(report())['native_parent_death_cases'],20)
    def test_replayed_event_or_direct_health_write_rejected(self):
        for key in ('death_delegate_manually_replayed','health_properties_written'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_destroyed_native_delay_callback_rejected(self):
        r=report();r['cases'][13]['no_late_work_after_destroy']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_delay_boundary_and_profile_switch_rejected(self):
        r=report();r['cases'][14]['endpoint_profile_matches_switch']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['cases'][10]['counts']['last_resume']['game_seconds']=2.
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_derived_case_or_extra_sense_removal_rejected(self):
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['cases'][0]['other_senses_unchanged']=False
        with self.assertRaises(RuntimeError):validate(r)
