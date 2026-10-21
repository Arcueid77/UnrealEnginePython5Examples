import unittest
from uep_lyra_world.arena_level_contract import DISTANCE,validate
def report(mode='Python'):
    counts={p+k:0 for p in ('python_','fallback_') for k in ('generate','clear','blocking','distance')}
    if mode!='Baseline':
        for k in ('generate','clear','blocking','distance'):counts[('python_' if mode=='Python' else 'fallback_')+k]=1
    names=['inclusive-full','trace-obstacle','grid-size-not-spacing','zero-percent','negative-width','zero-size','native-default-percent'];cases=[dict(name=n,positions=[[i,0,0] for i in range(count)],grid_size=200 if n=='grid-size-not-spacing' else 100,spacing=100.,only_original_block_class=True,locations_match_expected_grid=True,previous_world_blocks_removed=True,obstacle_cell_absent=True) for n,count in zip(names,(9,8,6,0,0,1,4))]
    return dict(status='passed',error=None,mode=mode,full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,callbacks_replayed=False,global_rng_replaced=False,native_trace_replaced=False,actor_assets_saved_by_runtime=False,cleanup_complete=True,selector_restored=True,owned_roots_removed=True,distance_cases=[dict(allowed=v) for v in DISTANCE],blocking_append=dict(first_matches_native_order=True,second_duplicates_preserved=True,all_z_zero=True),generation_cases=cases,clear_walls_empty=True,blocking_survives_regeneration=True,counts=counts)
class ArenaLevelContractTests(unittest.TestCase):
    def test_original_and_both_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertEqual(validate(report(mode))['native_generation_cases'],7)
    def test_strict_distance_and_per_call_local_reset_required(self):
        r=report();r['distance_cases'][5]['allowed']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_inclusive_final_row_and_native_trace_required(self):
        r=report();r['generation_cases'][0]['positions'].pop()
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['generation_cases'][1]['obstacle_cell_absent']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_grid_size_must_not_replace_fixed_spacing(self):
        r=report();r['generation_cases'][2]['spacing']=200.
        with self.assertRaises(RuntimeError):validate(r)
    def test_persistent_block_array_or_global_rng_replacement_rejected(self):
        r=report();r['blocking_append']['second_duplicates_preserved']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['global_rng_replaced']=True
        with self.assertRaises(RuntimeError):validate(r)
