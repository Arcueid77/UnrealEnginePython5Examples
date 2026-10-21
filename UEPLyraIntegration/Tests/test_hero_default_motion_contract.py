import unittest
from uep_lyra_characters.hero_default_motion_contract import KINDS,FALSE_FIELDS,TRUE_FIELDS,validate

def report(role='client'):
    r=dict(status='passed',error=None,role=role,native_is_server=role=='server',native_mode='ListenServer' if role=='server' else 'Client',cases=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in ('BlueprintFallback','Python'):
        for k in KINDS:
            empty=k=='explorer-hero';client=role=='client' and not empty;calls=4 if client else 2;py=p=='Python';counts=dict(python_calls=calls if py and not empty else 0,fallback_calls=calls if not py and not empty else 0,server_noops=2 if py and not empty and role=='server' else 0,spawns=2 if py and client else 0,reuses=2 if py and client else 0,attachments=2 if py and client else 0,forwards=4 if py and client else 0)
            r['cases'].append(dict(profile=p,kind=k,counts=counts,typed_second_blueprint_caller=True,actual_function_owner_preserved=True,native_exposed_properties_match_source=True,native_keep_relative_attachment_matches=True,same_footstep_reused=True,native_retrigger_preserved_actor_before_deadline=True,native_destroyed_after_delay=True,replacement_is_new_actor=True,replacement_naturally_destroyed=True,all_twelve_payloads_match=True,native_downstream_no_footprint_component=True,downstream_calls=4,native_original_delay_seconds=3.,native_destruction_elapsed=3.02,maximum_world_delta=.02,no_footstep_spawned_or_forwarded=True))
    return r

class HeroDefaultMotionContractTests(unittest.TestCase):
    def test_real_server_and_client_matrices(self):
        for role in ('server','client'):self.assertEqual(validate(report(role))['native_family_cases'],12)
    def test_standalone_cannot_prove_client_branch(self):
        r=report();r['native_mode']='Standalone'
        with self.assertRaises(RuntimeError):validate(r)
    def test_payload_attachment_or_reuse_mismatch_rejected(self):
        for key in ('all_twelve_payloads_match','native_keep_relative_attachment_matches','same_footstep_reused'):
            r=report();r['cases'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_shortened_or_non_retriggered_native_delay_rejected(self):
        r=report();r['cases'][0]['native_destruction_elapsed']=2.5
        with self.assertRaises(RuntimeError):validate(r)
    def test_server_or_retained_empty_override_side_effect_rejected(self):
        r=report('server');r['cases'][0]['no_footstep_spawned_or_forwarded']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['cases'][4]['counts']['python_calls']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_mislabelled_profile_and_pixel_overclaim_rejected(self):
        r=report();r['cases'][0]['counts']['python_calls']=4;r['cases'][0]['counts']['fallback_calls']=0
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['pixels_tested']=True
        with self.assertRaises(RuntimeError):validate(r)
