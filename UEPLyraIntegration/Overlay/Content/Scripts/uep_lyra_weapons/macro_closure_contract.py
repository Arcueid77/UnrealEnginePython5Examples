"""Original macro expansion versus shared Python helper acceptance."""
import argparse
import json
from pathlib import Path
from .hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','health_properties_written','original_macro_assets_modified')
TRUE_FIELDS=('exact_native_weapon_macro_matches','exact_native_ammo_completion_and_values_match','exact_native_tag_macro_matches','exact_native_specific_mesh_macro_matches','original_equipment_spawn_array_and_magazine_restored','all_probe_actors_and_roots_removed','original_live_health_unchanged')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native macro closure failed')
    for k in FALSE_FIELDS:require(r[k] is False,'macro scope overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'macro evidence missing: '+k)
    require(len(r['weapon_cases'])>=7 and len(r['ammo_cases'])>=5 and len(r['tag_cases'])>=4 and len(r['specific_cases'])>=3,'native macro edge matrix incomplete')
    return dict(status='passed',weapon_cases=len(r['weapon_cases']),ammo_cases=len(r['ammo_cases']),tag_cases=len(r['tag_cases']),specific_cases=len(r['specific_cases']),full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
