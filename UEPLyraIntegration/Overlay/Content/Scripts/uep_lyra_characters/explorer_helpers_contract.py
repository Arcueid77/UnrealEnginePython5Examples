"""Require owned native character/controller/ASC and typed Blueprint call cases."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','whole_characters_migrated','health_properties_written','native_async_callbacks_replayed','inventory_properties_written','physical_input_tested','unrelated_shooter_evidence_refreshed')
TRUE_FIELDS=('native_gamemode_spawned_exact_explorer_classes','scoped_pawnclass_override_restored','native_owned_controller_inventory_quickbar_and_asc_ready','native_blueprint_callers_used','native_empty_loadout_links_actual_unarmed_layer','native_audio_null_and_instance_roundtrip','native_slot_events_match_valid_occupied_indexes','native_clear_removes_owned_items_and_slots','native_missing_components_and_unpossessed_noops','original_player_inventory_and_health_unchanged','owned_objects_profiles_roots_and_tasks_restored')
CASES=('empty','one','duplicates','over-capacity','occupied')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'Explorer helpers runtime failed')
    for name in FALSE_FIELDS:require(r[name] is False,'Explorer helper scope overclaim: '+name)
    for name in TRUE_FIELDS:require(r[name] is True,'Explorer helper native observation missing: '+name)
    require([row['kind'] for row in r['characters']]==['hero','pawn'],'both original Explorer classes required')
    for row in r['characters']:
        require(row['natural_grant_calls']>=1 and row['native_asc_ready'],'native natural startup/ASC missing')
        require([c['name'] for c in row['cases']]==list(CASES),'native loadout matrix incomplete')
        for case in row['cases']:require(case['expected_shape_matches'] and case['clear_verified'] and case['slot_events_match'],'native loadout/clear/event case differs')
        require(row['unarmed_unlinked_before_and_relinked_after'] and row['audio_roundtrip'] and row['missing_component_cases'] and row['unpossessed_noops'],'native helper edge matrix incomplete')
    return dict(status='passed',profile=r['profile'],characters=2,cases=10,whole_characters_migrated=False,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
