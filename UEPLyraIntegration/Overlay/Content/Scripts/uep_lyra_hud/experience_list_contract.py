"""Native async catalog, source cache lifetime, opaque labels/focus and caller delivery."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested','native_callbacks_replayed','primary_asset_catalog_or_definition_flags_written','host_quickplay_or_session_travel_executed','health_properties_written')
COMMON_TRUE=('owned_roots_profiles_and_show_all_restored','original_gameplay_health_unchanged','fixture_collapsed_content_visibility_restored')
ROW_TRUE=('actual_native_async_catalog_order_and_filter','actual_native_text_histories_and_art_preserved','actual_entry_click_native_delegate_and_parent_assignment','actual_native_first_selection_uses_cached_old_entry','actual_native_random_selection_from_accumulated_cache','actual_native_remount_rebuild_and_accumulating_cache','actual_native_removed_entry_keeps_original_click_binding','actual_native_focus_replies_preserve_original_request_and_outcome')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native experience list/entry failed')
    for field in FALSE_FIELDS:require(r[field] is False,'experience list scope overclaim: '+field)
    for field in COMMON_TRUE:require(r[field] is True,'experience list cleanup missing: '+field)
    require([(row['profile'],row['show_all']) for row in r['trials']]==[(p,s) for p in PROFILES for s in (False,True)],'experience Profile/show-all matrix incomplete')
    for row in r['trials']:
        for field in ROW_TRUE:require(row[field] is True,'native experience list evidence missing: '+field)
        n=row['visible_entries'];require(n>0 and row['native_completed_loads']==2 and row['native_async_actions_observed']==2 and row['initial_cache_size']==n and row['remount_cache_size']==2*n,'source native construct/cache counts differ')
        require(row['native_selection_events']==4,'native click/first/removed-click/random selection count differs')
        require(row['fixture_collapsed_content_original_visibility']==1 and row['fixture_temporarily_expanded_for_focus'] is True,'focus fixture must preserve the source hidden caller layout')
    require(r['source_python_state_pairs_match'] is True,'native experience list Profile states differ')
    return dict(status='passed',native_profile_show_all_trials=4,native_asset_load_completions=8,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
