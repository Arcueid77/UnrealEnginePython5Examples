"""Native typed messages, Slate list entries and original six-second expiry."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native elimination widgets failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_or_list_subscription_replaced','timer_callbacks_replayed','list_item_callbacks_replayed','localized_text_roundtripped','health_properties_written','split_screen_filter_added'):require(r[k] is False,'feed widget overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'source/Python feed pair incomplete')
    for p in r['profiles']:
        require(len(p['style_cases'])==3 and all(s['native_material_values_match'] for s in p['style_cases']),'native fixed team highlight differs')
        require(len(p['icon_cases'])>=8 and all(s['native_text_matches'] and s['native_icon_matches'] for s in p['icon_cases']),'native opaque name/icon priority differs')
        require(p['initial_collapsed'] and p['two_items_visible'] and p['items_outer_matches_feed'] and p['all_native_entry_fields_match'] and p['animation_started'],'native list population/outer/presentation differs')
        require(p['expiry_entries']==2 and p['removed_entries']==2 and p['collapsed_after_expiry'] and p['native_expiry_durations_match'],'six-second native timer/current item expiry differs')
        require(p['removed_widget_still_received_native_message'] and p['remount_has_one_entry'] and p['remount_single_listener_entry'] and p['remount_expired'],'original rooted OnInitialized listener/remount behavior differs')
        require(p['diagnostic_fallbacks']==0,'defined feed cases used diagnostic fallback')
    for k in ('widget_roots_removed','original_cdo_profiles_restored','production_profile_families_restored','original_health_unchanged'):require(r[k] is True,'feed cleanup missing: '+k)
    return dict(status='passed',native_style_cases=6,native_icon_cases=sum(len(p['icon_cases']) for p in r['profiles']),native_list_scenarios=4,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
