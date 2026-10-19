"""Native Spawn Timeline, team observation and parts/delegate lifetime contract."""
import argparse
import json
from pathlib import Path
from .hero_burst_cue_contract import require,close

PLAN=(('short-unassigned',.35,True,-1,False,False),('long-switch',.8,True,0,True,False),('delayed-parts',.55,False,1,False,False),('late-parts-after-removal',.55,False,0,False,True))


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','native spawning run failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','parts_delegate_broadcast_by_fixture','team_properties_written','health_properties_written'):require(report[key] is False,'spawning scope overclaim: '+key)
    for key in ('owned_actors_destroyed','owned_effects_removed','owned_watchers_cancelled','production_profiles_restored','original_health_unchanged'):require(report[key] is True,'spawning cleanup absent: '+key)
    rows=report['pairs'];require([r['name'] for r in rows]==[p[0] for p in PLAN],'spawning paired matrix incomplete')
    for row,plan in zip(rows,PLAN):
        require(row['initial_application_entries']==[1,1] and row['initial_team_entries']==[1,1] and row['initial_fx_counts']==[2,2] and row['watchers_native_active'],'native application/initial team callback/mesh filter differs')
        require(row['initial_system_configuration'],'actual source Niagara attachment/template/duration differs')
        require(row['natural_samples']>=2 and row['all_samples_match'] and row['clocks_match'],'natural native Timeline/material/Niagara state differs')
        require(row['part_add_callback_deltas']==[2,2] and row['repeat_discovery_does_not_duplicate_effects'],'source AddUnique delegate or mesh cache differs')
        require(row['native_part_callback_entries_match']==[2,2] and row['native_team_callback_entries_match'][0]==row['native_team_callback_entries_match'][1],'native callback delivery differs')
        for key in ('removal_cleared_caches','removal_cancelled_watchers','removal_retained_source_handles','removal_did_not_stop_native_clock','native_parts_unbound_after_removal','native_team_unbound_after_removal','source_arrays_and_map_empty'):require(row[key],'source removal differs: '+key)
        require(len(row['removal_observations'])==(2 if plan[5] else 1) and all(all(observation.values()) for observation in row['removal_observations']),'each native removal, including the early removal, must retain source behavior')
        require(row['switched']==plan[4] and row['late_retry_rebound_after_removal']==plan[5],'native Profile switch or retained post-removal latent retry differs')
        require(row['team_change_callback_deltas']==([0,0] if plan[5] else [1,1]),'real team notification/cancellation differs')
        states=row['before_final_removal'];require(len(states)==2 and close(states[0],states[1]),'final paired native state differs')
        for state in states:
            require(abs(state['time']-1.)<.0001 and state['fx_count']==3 and state['map_count']==3,'native Timeline final value or new-part mesh discovery differs')
            require(all(abs(effect['duration']-plan[1])<.0001 and close(effect['body'],state['team'][:3]) and abs(effect['timeline']-state['time'])<.0001 for effect in state['fx']),'source duration/team/raw track Niagara parameters differ')
            require(any(m['slots']==0 for m in state['materials']) and all(abs(m['age']-state['time'])<.0001 for m in state['materials'] if m['slots']>0),'native parts mesh replacement/material-slot setter scope differs')
    require(len(report['manager_cases'])==1,'real spawning manager absent');row=report['manager_cases'][0]
    require(row['default_profile']=='Python' and row['application_entries']==1 and row['python_application'] and row['native_watcher_active'] and row['watcher_cancelled'] and row['cache_empty'],'real manager default dispatch/lifetime differs')
    return dict(status='passed',paired_native_cases=4,native_timelines=8,real_manager_cases=1,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
