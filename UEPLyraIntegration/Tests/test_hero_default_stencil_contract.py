import unittest
from uep_lyra_characters.hero_default_stencil_contract import KINDS,TEAMS,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,cases=[],primary_player_inventory_health_and_stencil_unchanged=True,existing_shooter_child_router_owner_preserved=True,owned_contexts_primitives_profiles_roots_and_selectors_restored=True,original_descendant_file_hashes_unchanged=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for profile in ('BlueprintFallback','Python'):
        for kind in KINDS:r['cases'].append(dict(profile=profile,kind=kind,target_function_is_parent_router=True,recursive_child_primitives_present=True,native_locally_and_player_controlled=kind=='local-parent',values=[dict(team=t,all_components_match_source=True,render_custom_depth_enable_flags_unchanged=True,parent_route_delta=1) for t in TEAMS]))
    return r
class HeroDefaultStencilContractTests(unittest.TestCase):
    def test_complete_native_family_matrix(self):self.assertEqual(validate(report())['native_parent_stencil_family_cases'],14)
    def test_missing_explorer_or_local_case_rejected(self):
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_route_or_recursive_mismatch_rejected(self):
        for key in ('target_function_is_parent_router','recursive_child_primitives_present'):
            r=report();r['cases'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_stencil_write_or_enable_side_effect_rejected(self):
        for key in ('all_components_match_source','render_custom_depth_enable_flags_unchanged'):
            r=report();r['cases'][0]['values'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_existing_child_router_or_file_change_rejected(self):
        for key in ('existing_shooter_child_router_owner_preserved','original_descendant_file_hashes_unchanged'):
            r=report();r[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_whole_parent_or_full_acceptance_overclaim_rejected(self):
        for key in ('whole_parent_business_migrated','full_acceptance'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
