"""Original inclusive grid, local blocking scope, native trace and world-wide clears."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
DISTANCE=[True,False,False,True,False,True,True,True]
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['mode'] in ('Baseline','Python','BlueprintFallback'),'Arena grid validation failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','global_rng_replaced','native_trace_replaced','actor_assets_saved_by_runtime'):
        require(r[k] is False,'Arena grid overclaim: '+k)
    require(r['cleanup_complete'] and r['selector_restored'] and r['owned_roots_removed'],'grid owned cleanup missing')
    require([v['allowed'] for v in r['distance_cases']]==DISTANCE,'function-local blocking reset/strict distance boundary differs')
    require(r['blocking_append']['first_matches_native_order'] and r['blocking_append']['second_duplicates_preserved'] and r['blocking_append']['all_z_zero'],'PlayerStart/Pickup block append/order/projection differs')
    cases=r['generation_cases'];require([v['name'] for v in cases]==['inclusive-full','trace-obstacle','grid-size-not-spacing','zero-percent','negative-width','zero-size','native-default-percent'],'grid cases missing/reordered')
    require([len(v['positions']) for v in cases[:6]]==[9,8,6,0,0,1],'inclusive grid/visibility trace/loop bounds differ')
    for row in cases:
        require(row['only_original_block_class'] and row['locations_match_expected_grid'] and row['previous_world_blocks_removed'],'original block class/coordinates/global clear differs')
    require(cases[1]['obstacle_cell_absent'] and cases[2]['spacing']==100. and cases[2]['grid_size']==200 and 0<=len(cases[-1]['positions'])<=9,'trace hit or fixed100 spacing/native random subset differs')
    require(r['clear_walls_empty'] and r['blocking_survives_regeneration'],'ClearWalls/Generate must not reset BlockingArea')
    if r['mode']!='Baseline':
        p='python_' if r['mode']=='Python' else 'fallback_';other='fallback_' if r['mode']=='Python' else 'python_';c=r['counts'];require(all(c[p+k]>0 and c[other+k]==0 for k in ('generate','clear','blocking','distance')),'selected grid Profile missing')
    return dict(status='passed',mode=r['mode'],native_generation_cases=len(cases),native_distance_cases=len(DISTANCE),full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
