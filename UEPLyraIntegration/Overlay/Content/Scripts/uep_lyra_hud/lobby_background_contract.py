"""Real lobby asset/level streaming events and original delayed task release."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_async_callbacks_replayed','health_properties_written','python_latency_clock_added','native_skip_empty_or_failed_level_variants_tested','default_editor_list_and_portal_migrated')
ROW_TRUE=('native_construction_box_extents_preserved','native_catalog_selected_registered_primary_id','native_loading_process_task_identity_and_reason','native_primary_async_loaded_correct_data_asset','native_level_instance_actor_location_rotation','native_actual_loaded_and_shown_weak_delegate_callbacks','native_half_second_delay_before_unregister','native_loading_reason_released','native_owned_level_unloaded_and_removed','native_actor_destroyed')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native lobby background failed')
    for f in FALSE_FIELDS:require(r[f] is False,'lobby scope overclaim: '+f)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'native lobby Profiles incomplete')
    for p in r['profiles']:
        for f in ROW_TRUE:require(p[f] is True,'native lobby observation missing: '+f)
        require(p['loaded_callbacks']==p['shown_callbacks']==p['release_callbacks']==1 and p['release_delay_game_seconds']>=.48,'native lobby callback/delay differs')
    require(r['owned_roots_cdo_profile_and_original_health_restored'] is True,'lobby owned cleanup failed')
    return dict(status='passed',native_lobby_streaming_profiles=2,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
