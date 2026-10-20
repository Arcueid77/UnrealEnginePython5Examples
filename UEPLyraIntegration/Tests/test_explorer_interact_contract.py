import unittest
from uep_lyra_abilities.explorer_interact_contract import FALSE_FIELDS,TRUE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,cases=[],primary_player_inventory_and_health_unchanged=True,class_selectors_roots_and_owned_contexts_restored=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for profile in ('BlueprintFallback','Python'):
        c=dict(profile=profile,active_task_counts=dict(scan=1,wait=1,nearby=1,release=0),native_target_trigger_count=2,target_event_tag='Ability.Interaction.Activate',target_event_instigator_and_target_match=True,end_cancelled_values=[True,False]);c.update(dict.fromkeys(TRUE_FIELDS,True));r['cases'].append(c)
    return r
class ExplorerInteractContractTests(unittest.TestCase):
    def test_complete_native_profile_pair(self):self.assertEqual(validate(report())['native_interact_profiles'],2)
    def test_missing_profile_rejected(self):
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_scan_or_dead_release_task_rejected(self):
        for field,value in (('scan',2),('release',1)):
            r=report();r['cases'][0]['active_task_counts'][field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_incorrect_native_target_count_or_payload_rejected(self):
        for field,value in (('native_target_trigger_count',3),('target_event_instigator_and_target_match',False)):
            r=report();r['cases'][0][field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_cancelled_values_rejected(self):
        r=report();r['cases'][0]['end_cancelled_values']=[True,True]
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_native_lifecycle_observation_rejected(self):
        for key in TRUE_FIELDS:
            r=report();r['cases'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_callback_replay_or_full_claim_rejected(self):
        for key in ('task_callbacks_replayed','full_acceptance'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
