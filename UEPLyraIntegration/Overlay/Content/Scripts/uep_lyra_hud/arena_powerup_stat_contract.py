"""Require real native retries, GameplayEffects, callbacks, text and animation."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
FORMAT=[[-1.5,'-1'],[-.5,'0'],[.49,'0'],[.5,'1'],[1.49,'1'],[1.5,'2'],[1234.5,'1,235']]
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['mode'] in ('Baseline','Python','BlueprintFallback'),'Arena stat observation failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','delegate_broadcast_by_fixture','python_retry_clock','new_production_cleanup_added','actor_attributes_written_directly'):
        require(r[key] is False,'Arena stat overclaim: '+key)
    require(r['cleanup_complete'] and r['owned_proxies_cancelled'] and r['owned_widgets_removed'] and r['pause_restored'],'owned stat cleanup incomplete')
    require(r['natural_stats'] and {v['attribute'] for v in r['natural_stats']}=={'BombsRemaining','BombRange','MovementSpeed'},'actual Arena HUD stat Configure missing')
    for row in r['natural_stats']:
        require(row['target'] and row['active'] and row['text']==row['expected_text'],'natural stat text/subscription mismatch')
        if r['mode']!='Baseline':
            p='python_' if r['mode']=='Python' else 'fallback_';other='fallback_' if r['mode']=='Python' else 'python_';require(row['counts'][p+'configure']>=1 and row['counts'][p+'listen']>=1 and row['counts'][other+'listen']==0,'actual selected natural stat Profile missing')
    retry=r['retry'];require(retry['initial_attribute_missing'] and retry['two_configures'] and retry['paused_seconds']>=.15 and retry['game_time_paused'] and retry['native_listen_continues_while_paused'] and retry['no_proxy_after_init_while_paused'],'native Slate-clock paused/coalesced retry differs')
    require(retry['attribute_initialized_natively'] and retry['resumed_without_manual_listen'] and retry['resumed_while_world_paused'] and abs(retry['native_resume_game_seconds'])<.0001 and retry['native_resume_frame_delta']>=1 and 0.<=retry['native_resume_real_seconds']<=.2 and retry['active'] and retry['initial_text']=='1','original0.1s UMG retry did not resume on a later native frame while game time was paused')
    require(r['soft_texture_initially_unloaded'] and r['soft_texture_resource']=='/Game/UEPValidation/T_ArenaStatSoftProbe.T_ArenaStatSoftProbe','native unloaded soft-display reference lost')
    first=r['first_change'];require(first['callbacks']==1 and first['new_value']==.5 and first['old_value']==1. and first['text']=='1' and first['native_animation_started'],'coalesced retry created extra listener or real native attribute event missing')
    animation=r['animation'];require(animation['max_position']>.01 and animation['finished'] and animation['end']>0.,'original native animation did not advance/finish')
    pending=r['pending_reconfigure'];require(pending['immediate_active'] and pending['replacement_distinct'] and pending['earlier_proxy_still_active'] and pending['proxies_not_rooted'] and pending['callbacks']==2 and pending['new_value']==.25 and pending['old_value']==.5 and pending['text']=='0','original pending retry duplicate-listener window changed')
    repeated=r['repeat_configure'];require(repeated['stored_previous_cancelled'] and repeated['older_proxy_still_active'] and repeated['callbacks']==2 and repeated['text']=='1','source Configure must cancel only the stored proxy')
    require(r['format_cases']==FORMAT,'native Round64/int64 FText formatting differs')
    require(r['trace_only_forwarding'] and r['native_gameplay_effect_used'] and r['no_manual_animation_completion'],'native callback evidence provenance differs')
    return dict(status='passed',mode=r['mode'],natural_stats=len(r['natural_stats']),format_cases=len(FORMAT),native_delay_seconds=.1,pending_native_duplicate_callbacks=2,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
