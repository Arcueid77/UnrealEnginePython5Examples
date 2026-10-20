"""Native default-map filter/deferred spawn/local overlap/offline travel proof."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_player_movement_tested','native_async_callbacks_replayed','health_properties_written','cross_travel_actor_health_identity_claimed')
TRUE_FIELDS=('native_catalog_async_loaded_real_definitions','native_false_true_filter_additional_order_and_duplicates','native_spawn_definition_exposed_before_beginplay','native_centered_actor_transform_layout','native_original_widget_definition_delay_tick_disabled','native_original_default_color_branch','native_repeated_begin_accumulates_old_portal_cache','native_nonpawn_and_uncontrolled_inputs_do_not_load','native_real_local_pawn_overlap_requests_load','native_spinner_afterpush_current_definition_offline_payload','native_destination_map_experience_and_player_ready','initial_gameplay_health_unchanged_before_travel','owned_roots_profiles_fixture_actors_and_loading_class_restored')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'native editor experience flow failed')
    for f in FALSE_FIELDS:require(r[f] is False,'editor experience overclaim: '+f)
    for f in TRUE_FIELDS:require(r[f] is True,'native editor experience observation missing: '+f)
    require(r['native_filter_cases']==[False,True] and r['request_mode']==0 and r['pushed_handler_calls']==1,'native editor filter/offline request matrix differs')
    require(r['native_destination_level']==r['native_request_map'].rsplit('/',1)[-1] and r['native_destination_experience']==r['native_request_experience'],'native editor destination differs')
    return dict(status='passed',native_editor_experience_profile=r['profile'],full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
