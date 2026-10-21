"""Native Arena avatar init/team/parts, lethal GAS task and physical pickup overlap."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['mode'] in ('Baseline','Python','BlueprintFallback'),'Arena actor native validation failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','callbacks_replayed','death_event_sent_by_fixture','health_properties_written','replication_verified','native_tasks_or_delays_replaced'):
        require(r[k] is False,'Arena actor overclaim: '+k)
    require(r['cleanup_complete'] and r['selectors_restored'] and r['owned_roots_removed'],'owned actors/selector cleanup incomplete')
    require(r['natural_arena_avatar'] and r['owned_avatar_class_preserved'] and r['retained_parent_begin_calls']==1,'actual Arena avatar/retained native parent startup missing')
    v=r['visibility'];require(v['initially_hidden'] and v['shown'] and v['shown_frame']>v['created_frame'],'original GameplayReady native next-tick show missing')
    require([v['team'] for v in r['team_cases']]==[1,2,1] and all(v['display_asset'] and v['visible_parts']>=1 for v in r['team_cases']),'native team/cosmetic cases missing')
    require(r['team_visuals_changed'] and r['team_visuals_restored'] and r['native_parts_add_remove'],'native display asset/parts lifecycle differs')
    death=r['death'];require(death['native_lethal_effect'] and death['ability_class_preserved'] and death['activated'] and death['finished'] and 1.95<=death['duration']<=2.25,'original two-second native death task failed')
    require(death['dead_or_removed_avatar'] and death['native_cue_executed'],'native parent death/Cue finish missing')
    pickup=r['pickup'];require(pickup['no_asc_overlap_keeps_actor'] and pickup['successful_overlap_destroys_actor'] and abs(pickup['attribute_after']-pickup['attribute_before']-1.)<.0001,'real native overlap/effect/destroy differs')
    require(pickup['authority_vfx_matches_ui_data'] and pickup['authority_rep_notify_noop'] and pickup['null_effect_noop'],'pickup authority/UI-data branches differ')
    if r['mode']!='Baseline':
        p='python_' if r['mode']=='Python' else 'fallback_';other='fallback_' if r['mode']=='Python' else 'python_'
        require(r['hero_counts'][p+'begin']==1 and r['hero_counts'][p+'listen']>=1 and r['hero_counts'][p+'display']>=1 and r['hero_counts'][p+'parts']>=2 and r['hero_counts'][p+'show']>=1 and r['hero_counts'][other+'begin']==0,'selected Arena avatar policy missing')
        require(death['counts'][p+'death']==1 and death['counts'][p+'finish']==1,'selected death activation/native task continuation missing')
        require(pickup['counts'][p+'overlap']>=1 and pickup['counts'][p+'change']>=1,'selected native pickup policy missing')
    return dict(status='passed',mode=r['mode'],native_team_cases=3,native_death_duration=2.,native_pickup_overlap=True,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
