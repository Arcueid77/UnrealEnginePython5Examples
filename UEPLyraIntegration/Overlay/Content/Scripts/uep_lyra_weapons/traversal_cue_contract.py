"""Native launcher curve/raw-time distinction and teleporter state/coordinates."""
import argparse
import json
from pathlib import Path


def require(value,text):
    if not value:raise RuntimeError(text)


def close(a,b):
    if isinstance(a,dict):return a.keys()==b.keys() and all(close(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return abs(a-b)<.001
    return a==b


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','native traversal run failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','health_properties_written'):
        require(report[key] is False,'traversal scope overclaim: '+key)
    for key in ('owned_targets_and_devices_destroyed','owned_effects_removed','original_health_unchanged','production_profiles_restored'):
        require(report[key] is True,'traversal cleanup absent: '+key)
    launch=report['launcher_pairs'];require(len(launch)==4,'launcher native paired matrix incomplete')
    for row in launch:
        require(row['burst_entries']==[1,1] and row['spawn_counts']==[2,2] and row['initial_configuration_match'],'actual launch causer/mesh/parameter initialization differs')
        require(row['natural_samples']>=2 and row['all_material_and_raw_niagara_values_match'] and row['paired_clock_and_state_match'],'native external curve versus raw Timeline parameter differs')
        require(row['source_curve_distinction_observed'] and row['arrays_cleared'] and row['all_effects_naturally_inactive'] and row['finish_glow_zero'],'launcher finish/curve distinction missing')
        if row['destroy_target']:require(row['timeline_stopped_after_target_destroy'],'invalid target did not clear and stop original Timeline')
        else:require(row['clear_entries']==[1,1],'natural clear callback count differs')
    rows=report['teleport_pairs'];require(len(rows)==6,'native portal/destination/counter matrix incomplete')
    for row in rows:
        require(close(row['original'],row['python']) and row['burst_entries']==[row['bursts'],row['bursts']],'native teleport state/coordinate parity differs')
        require(row['all_native_parameters_match_source'] and row['native_exit_particle_count']==2*row['bursts'],'actual native portal mesh/particle parameters missing')
        require(row['entry_count_matches_native_int32'] and row['destination_count_and_direction_match'],'source int32/remainder/direction semantics differ')
    require(report['wrong_causer_preserves_partial_assignment'] and report['real_default_python_manager_tags']==2,'source causer guard or real manager path missing')
    return dict(status='passed',native_launcher_pairs=4,native_teleporter_pairs=6,real_manager_tags=2,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
