import unittest
from uep_lyra_characters.explorer_shells_contract import FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,actors=[],prompt_cases=[],original_assets_hashes_unchanged=True,owned_actors_widgets_descriptors_and_roots_closed=True,primary_player_inventory_and_health_unchanged=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for kind in ('simple','big'):r['actors'].append(dict(kind=kind,exact_original_class_spawned=True,original_native_method_shapes_preserved=True,components_config_and_location_stable=True,native_parent_routes_retained=True))
    for name in ('actor','nonactor','null-data'):r['prompt_cases'].append(dict(name=name,native_bind_call_completed=True,text_style_visibility_and_tree_unchanged=True,descriptor_and_actor_state_unchanged=True))
    return r
class ExplorerShellsContractTests(unittest.TestCase):
    def test_complete_native_retained_asset_matrix(self):self.assertEqual(validate(report())['native_prompt_cases'],3)
    def test_parent_migration_overclaim_rejected(self):
        r=report();r['inherited_parent_business_migrated']=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_big_actor_or_null_indicator_data_rejected(self):
        for key in ('actors','prompt_cases'):
            r=report();r[key].pop()
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_modified_original_config_or_text_rejected(self):
        for key,index,field in (('actors',0,'components_config_and_location_stable'),('prompt_cases',0,'text_style_visibility_and_tree_unchanged')):
            r=report();r[key][index][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_production_asset_edit_or_full_claim_rejected(self):
        for key in ('production_assets_modified','full_acceptance'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
