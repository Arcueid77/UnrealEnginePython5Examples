"""Bounded original-shell/prompt runtime evidence; no parent migration claim."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','inherited_parent_business_migrated','python_noop_profiles_added','production_assets_modified')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'retained Explorer shell runtime failed')
    for key in FALSE_FIELDS:require(r[key] is False,'retained Explorer shell overclaim: '+key)
    require([c['kind'] for c in r['actors']]==['simple','big'],'retained actor runtime cases incomplete')
    for c in r['actors']:
        for key in ('exact_original_class_spawned','original_native_method_shapes_preserved','components_config_and_location_stable','native_parent_routes_retained'):require(c[key] is True,'retained original actor observation missing: '+key)
    require([c['name'] for c in r['prompt_cases']]==['actor','nonactor','null-data'],'prompt native data/cast matrix incomplete')
    for c in r['prompt_cases']:require(c['native_bind_call_completed'] and c['text_style_visibility_and_tree_unchanged'] and c['descriptor_and_actor_state_unchanged'],'retained native prompt had new side effects')
    for key in ('original_assets_hashes_unchanged','owned_actors_widgets_descriptors_and_roots_closed','primary_player_inventory_and_health_unchanged'):require(r[key] is True,'retained shell cleanup missing: '+key)
    return dict(status='passed',retained_original_actor_cases=2,native_prompt_cases=3,inherited_parent_business_migrated=False,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
