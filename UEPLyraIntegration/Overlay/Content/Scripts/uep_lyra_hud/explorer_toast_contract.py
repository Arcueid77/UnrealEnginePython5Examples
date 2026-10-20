"""Native toast list delivery, localized text, timer replacement and expiry."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
SCENARIOS=('positive','zero','negative','replace','invalid','switch','removed','gc')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','timer_callback_replayed','python_timer_clock_added','localized_text_roundtripped_through_python','native_timer_private_properties_written')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Explorer toast native fixture failed')
    for k in FALSE_FIELDS:require(r[k] is False,'Explorer toast overclaim: '+k)
    for k in ('native_list_view_delivered_valid_entries','native_list_expiry_removed_original_items','localized_text_namespace_keys_preserved','icon_texture_visibility_and_unmatched_size_pairs_preserved','owned_timers_widgets_roots_and_selectors_restored','primary_player_inventory_and_health_unchanged'):require(r[k] is True,'Explorer toast missing observation: '+k)
    require([(c['name'],c['profile']) for c in r['cases']]==[(s,p) for s in SCENARIOS for p in ('BlueprintFallback','Python')],'native toast timer matrix incomplete')
    for c in r['cases']:
        expected=0 if c['name'] in ('zero','negative','gc') else 1;require(c['expiry_count']==expected and c['expected_item_payload'] and c['native_timer_state_matches'] and c['current_callback_profile_matches'],'native toast timer/payload/Profile differs: '+c['name'])
        if expected:require(c['elapsed_after_last_valid_set']>=c['configured_last_duration']-.04,'native toast expired before replacement duration')
        if c['name']=='gc':require(c['row_native_object_collected'] and c['no_timer_callback_after_gc'],'dead native row timer still called')
    return dict(status='passed',native_toast_timer_cases=16,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
