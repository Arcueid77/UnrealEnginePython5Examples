import unittest
from uep_lyra_characters.hero_default_equipment_contract import KINDS,SCENARIOS,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,cases=[],primary_player_inventory_health_and_equipment_unchanged=True,existing_shooter_child_router_owner_preserved=True,owned_actors_equipment_instances_profiles_roots_and_selectors_restored=True,original_descendant_file_hashes_unchanged=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for profile in ('BlueprintFallback','Python'):
        for kind in KINDS:r['cases'].append(dict(profile=profile,kind=kind,target_function_is_parent_router=True,native_manager_equipped_real_instances_and_actors=True,native_unequip_destroyed_all_fixture_spawned_actors=True,scenarios=[dict(name=n,calls=2 if n=='repeat' else 1,route_delta=2 if n=='repeat' else 1,all_weapon_actors_hidden=True,nonweapon_actor_visibility_unchanged=True,pawn_visibility_and_equipment_identity_unchanged=True) for n in SCENARIOS]))
    return r
class HeroDefaultEquipmentContractTests(unittest.TestCase):
    def test_complete_native_family_matrix(self):self.assertEqual(validate(report())['native_equipment_scenarios'],72)
    def test_missing_explorer_or_manager_case_rejected(self):
        r=report();r['cases'][0]['scenarios'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_nonweapon_or_pawn_visibility_side_effect_rejected(self):
        for key in ('nonweapon_actor_visibility_unchanged','pawn_visibility_and_equipment_identity_unchanged'):
            r=report();r['cases'][0]['scenarios'][1][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_missing_route_or_actor_cleanup_rejected(self):
        for key in ('target_function_is_parent_router','native_unequip_destroyed_all_fixture_spawned_actors'):
            r=report();r['cases'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_repeat_count_rejected(self):
        r=report();r['cases'][0]['scenarios'][2]['route_delta']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_private_write_or_full_parent_claim_rejected(self):
        for key in ('equipment_private_properties_written','whole_parent_business_migrated'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
