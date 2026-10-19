"""Native feedback state, physical clock completion and offline audio evidence."""
import argparse
import json
from pathlib import Path
from .control_point_state_contract import PROFILES,STAGES,require


def close(a,b):
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    return abs(float(a)-float(b))<.0002


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native feedback run failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','overlap_callbacks_replayed','timeline_callbacks_replayed','pawn_arrays_written_by_fixture','health_properties_written','audio_energy_measured'):
        require(r[k] is False,'feedback scope overclaim: '+k)
    require(r['timeline_update_finish_rpc_vfx_audio_business_migrated'] is True,'feedback migration absent')
    require(r['natural_map_volumes']>0 and r['natural_map_python_ready']==r['natural_map_volumes'],'natural map ready initialization missing')
    require([c['profile'] for c in r['cases']]==list(PROFILES),'feedback source/Python pairs incomplete')
    for c in r['cases']:
        require(c['ready_entries']==1 and close(c['native_rate'],1.),'native ready/rate differs')
        require([s['name'] for s in c['stages']]==list(STAGES),'physical scenarios incomplete')
        a,b,d,e,f,g=c['stages']
        require(a['teams']==[1] and a['playing'] and set(b['teams'])=={1,2} and not b['playing'] and close(b['position'],0.),'physical contest did not reach natural reverse completion')
        require(d['owner']==d['point_owner']==1 and f['owner']==f['point_owner']==2 and not e['pawns'] and not g['pawns'],'natural captures/empty ownership differ')
        require(c['samples']>=5 and c['all_native_feedback_matches'] and c['sampled_intermediate_curve'],'actual interpolated native feedback missing')
        require(c['native_reverse_finishes']>=1 and c['native_forward_finishes']>=2,'native forward/reverse completion missing')
        require(c['mesh_list_unique_and_existing_preserved'] and c['light_native_srgb_reference'],'BeginPlay mesh collection/native light reference differs')
        require(c['audio']['locally_viewed'] and c['audio']['entered'] and c['audio']['exit_parameter_false'] and c['audio']['stopped_after_delay'],'native local progress audio differs')
        require(c['audio']['friendly_sound'] and c['audio']['enemy_sound'] and c['audio']['capture_playing'],'native capture audio selection differs')
        require(c['audio']['remote_and_invalid_noop'],'remote/invalid audio must remain a no-op')
        require(c['music_local_overlap'] and c['local_transform_restored'],'physical local music branch/restoration missing')
        for n in ('Meshes','TimelineUpdate','TimelineFinished','EnterAudio','ExitAudio','CaptureAudio','Music','ActivateVFX','CleanVFX'):
            require(c['entries'][n]>0,'missing native gate: '+n)
        require(c['diagnostic_fallbacks']==0,'Python feedback returned to diagnostics')
    for k in ('owned_actors_destroyed','source_scoring_arrays_restored','original_health_unchanged','production_profiles_restored','local_movement_tick_restored'):require(r[k] is True,'feedback cleanup absent: '+k)
    return dict(status='passed',physical_profile_scenarios=2,native_feedback_samples=sum(c['samples'] for c in r['cases']),offline_audio_pairs=2,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
