"""Native Timeline time/curves, mesh filtering, material/Niagara state and finish."""
import argparse
from collections import Counter
import json
from pathlib import Path


def require(value,text):
    if not value:raise RuntimeError(text)


def close(a,b):
    if isinstance(a,dict):return a.keys()==b.keys() and all(close(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return abs(a-b)<.0001
    return a==b


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','native hero burst run failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','native_timer_properties_written','health_properties_written','identical_particle_lifetimes_claimed'):
        require(report[key] is False,'hero burst scope overclaim: '+key)
    for key in ('owned_actors_destroyed','owned_effects_removed','production_profiles_restored','original_health_unchanged'):
        require(report[key] is True,'hero burst cleanup absent: '+key)
    rows=report['pairs'];require(len(rows)==10,'hero burst paired matrix incomplete')
    require(Counter(r['kind'] for r in rows)==Counter(dash=5,death=5),'both hero burst classes required')
    for row in rows:
        require(row['initial_burst_entries']==[1,1] and row['spawn_counts']==[2,2],'root/child/ignored mesh source filter or burst dispatch differs')
        require(row['native_start_values_match'] and row['native_system_configuration_matches'],'actual native initialized state differs')
        require(row['natural_samples']>=2 and row['all_sample_pairs_match'] and row['all_samples_match_native_curve_parameters'],'native material/Niagara Timeline state differs')
        require(row['finished_entries']==[1,1] and row['effect_arrays_cleared'] and row['all_effects_deactivated'],'native finish callback or source array cleanup differs')
        require(row['native_playback_positions_match'] and row['completed_after_configured_duration'],'native Timeline clock/rate/duration differs')
        if row['switch']:require(row['profile_switch_observed'] and row['finish_profiles']==['Python','BlueprintFallback'],'live Timeline callback failed to follow Profile switch')
        if row['kind']=='death':require(row['root_decals_destroyed_child_decals_retained'] and row['final_edge_glow_zero'],'source death decal scope/finish glow differs')
    require(Counter(r['kind'] for r in report['manager_cases'])==Counter(('dash','death')),'real native hero burst Cue children missing')
    for row in report['manager_cases']:require(row['default_python_burst_entry'] and row['native_timeline_playing'] and row['effects_started'],'real manager did not execute migrated burst business')
    return dict(status='passed',paired_native_cases=10,actual_native_timelines=20,live_profile_switch_pairs=2,real_manager_cases=2,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
