"""Paired native spawning Cue removal with a genuinely destroyed cached target."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require,close
PLAN=(('mid-timeline-with-parts',.8,True,0,False,False),('finished-timeline-without-parts',.35,False,0,False,False))
FORBIDDEN=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','parts_delegate_broadcast_by_fixture','team_properties_written','health_properties_written','cached_target_property_cleared_by_probe','python_policy_removal_called_directly','actor_destroy_replaced_by_invalid_mock')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','Native destroyed-target spawning comparison failed')
    for key in FORBIDDEN:require(r[key] is False,'Destroyed-target shortcut: '+key)
    require([c['name'] for c in r['pairs']]==[p[0] for p in PLAN],'Both live and completed native Timeline cases required')
    for index,row in enumerate(r['pairs']):
        require(row['profiles']==['BlueprintFallback','Python'] and row['actual_cue_classes']==[r['expected_cue_class']]*2,'Actual retained native Cue class/profile pair required')
        require(row['initial_application_entries']==[1,1] and row['initial_team_entries']==[1,1] and row['initial_fx_counts']==[2,2] and row['watchers_native_active'] and row['initial_system_configuration'],'Actual native paired application/system/watchers missing')
        require(row['natural_samples']>=2 and row['paired_native_state_matches'] and row['native_clocks_match'],'Native pre-destruction Timeline/material/FX states differ')
        require(row['native_target_destroyed']==[True,True] and row['invalid_cached_target_reproduced']==[True,True] and row['cached_target_identity_retained']==[True,True],'Actual destroyed cached-target stimulus was not reproduced')
        require(row['removal_target_argument_null'] and row['removal_entries']==[1,1] and row['removal_cleared_caches'] and row['removal_cancelled_watchers'] and row['removal_retained_source_handles'],'Source native OnRemoval cleanup differs')
        require(row['native_clock_playing_at_destroy']==[index==0]*2 and row['native_clock_flags_after_removal']==row['native_clock_playing_at_destroy'],'OnRemoval stopped or replaced the original Timeline')
        require(row['quiet_seconds']>=.8 and row['effects_stayed_empty'] and row['diagnostic_fallbacks']==[0,0],'Late native work recreated effects or used a diagnostic fallback')
        require(row['post_destroy_updates'][0]==row['post_destroy_updates'][1] and (all(v>0 for v in row['post_destroy_updates']) if index==0 else row['post_destroy_updates']==[0,0]),'Original post-removal native Timeline behavior differs')
        require(close(row['final_spawn_times'],[1.,1.]),'Native Timeline did not reach its original final value')
    for key in ('owned_actors_destroyed','owned_effects_removed','owned_watchers_cancelled','production_profiles_restored','original_health_unchanged'):require(r[key] is True,'Destroyed-target fixture cleanup missing: '+key)
    return dict(status='passed',paired_native_cases=2,native_target_destructions=4,native_timelines=4,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
