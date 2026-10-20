"""Native widget return, opaque FText, queue timers and UMG playback evidence."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native accolade presentation failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_energy_measured','native_registry_or_queue_replaced','timer_or_animation_callbacks_replayed','health_properties_written','localized_text_roundtripped'):
        require(r[k] is False,'accolade widget overclaim: '+k)
    require([p['profile'] for p in r['pairs']]==list(PROFILES),'widget source/Python comparison incomplete')
    for p in r['pairs']:
        require(p['natural_constructs']==2 and p['initial_collapsed'] and p['remount_collapsed'],'natural construct/remount differs')
        require(len(p['direct_cases'])==2 and all(c['returned_owned_toast'] and c['native_text_matches'] and c['icon_matches'] and c['visible'] and c['animation_playing'] for c in p['direct_cases']),'native Create return/text/icon/visibility/animation differs')
        require(p['destroy_ignores_foreign_argument'] and p['repeat_animation_still_playing'],'source destroy/retrigger behavior differs')
        require(p['fifo_create_order']==p['expected_fifo'] and p['fifo_native_allocated_widget_matches'] and p['fifo_duration_checks'],'actual native registry/queue/timer flow differs')
        require(p['cancel_order']==['create','destroy','create','destroy'] and p['cancel_create_order']==p['expected_cancel'],'native tag cancellation order differs')
        require(p['foreign_target_ignored'] and p['unmounted_message_ignored'] and p['single_create_after_remount'],'original native listener filter/lifetime differs')
        require(p['all_queued_native_text_icon_and_allocation_match'] and p['diagnostic_fallbacks']==0,'queue presentation or diagnostic fallback differs')
    require(r['animation_repeat_pairs_match'] and r['widget_profile_families_restored'] and r['owned_widgets_removed_unrooted'] and r['sender_root_removed'] and r['original_health_unchanged'] and r['owned_foreign_player_destroyed'],'widget source parity/cleanup missing')
    return dict(status='passed',native_host_profiles=2,native_direct_create_cases=4,native_registry_queue_scenarios=6,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
