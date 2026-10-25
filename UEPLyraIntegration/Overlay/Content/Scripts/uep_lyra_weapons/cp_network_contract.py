"""One natural control-point capture, replicated score/victory and local feedback."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
PEERS=('server','A','B0')
SOUNDS={p:'/Game/Audio/Sounds/SFX/Lyra_ControlPoint_CapturedBy'+n+'_01.Lyra_ControlPoint_CapturedBy'+n+'_01' for p,n in (('A','Friendly'),('B0','Enemy'))}
FALSE=('full_acceptance','packaged_runtime','pixels_tested','physical_keyboard_input_tested','health_properties_written','asc_or_avatar_repaired','overlap_or_timeline_callbacks_replayed','capture_or_scoring_called_by_fixture','score_or_owner_arrays_written_as_stimulus','phase_or_victory_called_by_fixture','native_rpc_replaced','travel_rejoin_tested')

def validate_result(row,peer):
    require(row['team_scores']==[1,0] and row['capture_stats']==[1,0] and row['point_owner']==row['roster']['A']['team'] and row['target_score']==1,'Native replicated capture/score state differs')
    require(row['healths']==[100.,100.] and row['damage_immunity']==[True,True],'Healthy native postgame owner state missing')
    require(row['capture_audio_owner_teams']==[row['roster']['A']['team']],'One native capture multicast receipt required')
    if peer=='server':
        require(row['native_postgame'] and not row['native_playing'] and row['selected_capture_calls']==row['selected_victory_calls']==1,'Natural authority capture/victory phase path missing')
        require(row['real_overlap_observed'] and row['capture_audio_playing']==[False] and row['native_score_widgets']==0,'Authority overlap or zero-cosmetic behavior differs')
    else:
        require(row['capture_audio_sounds']==[SOUNDS[peer]] and row['capture_audio_playing']==[True],'Actual client capture sound/owner filtering differs')
        require(row['match_decided_cue_actors']>=1 and row['native_score_widgets']==1,'Actual local winner Cue/HUD absent')
        require(row['hud']==dict(ally='1' if peer=='A' else '0',enemy='0' if peer=='A' else '1',target='1'),'Replicated team score and actual local HUD disagree')

def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['peer'] in PEERS and report['requested_profile'] in ('BlueprintFallback','Python'),'CP network peer failed')
    for name in FALSE:require(report[name] is False,'CP network shortcut: '+name)
    for name in ('profiles_selected_before_component_creation','initial_canonical_healthy_owners','native_scores_and_capture_stats_restored','target_score_restored','observer_profiles_restored','boot_selectors_restored','observer_class_roots_restored','observer_references_released'):
        require(report[name] is True,'CP network cleanup/readiness missing: '+name)
    if report['peer']=='server':require(report['server_waited_for_client_process_exit'],'Authority exited before real clients')
    validate_result(report['result'],report['peer'])
    expected=('scoring','point') if report['peer']=='server' else ('scoring','point','score_widget')
    require(report['result']['effective_profiles']==dict.fromkeys(expected,report['requested_profile']),'Actual CP instances used another profile')
    return dict(status='passed',peer=report['peer'],profile=report['requested_profile'],real_native_capture_cases=1,full_acceptance=False)

def validate_all(directory):
    root=Path(directory);reports={p:json.loads((root/(p+'.json')).read_text(encoding='utf-8-sig')) for p in PEERS}
    for report in reports.values():validate(report)
    ref=reports['server']
    require(len({r['run_id'] for r in reports.values()})==1 and len({r['requested_profile'] for r in reports.values()})==1,'Mixed CP network processes')
    for peer in ('A','B0'):
        for key in ('roster','point_wire','team_scores','capture_stats','point_owner','target_score','healths','damage_immunity'):require(reports[peer]['result'][key]==ref['result'][key],'CP native peer state differs: '+key)
    require(ref['result']['roster']['A']['team']!=ref['result']['roster']['B0']['team'] and ref['result']['roster']['A']['state_wire']!=ref['result']['roster']['B0']['state_wire'],'Distinct native teams/wire owners required')
    return dict(status='passed',profile=ref['requested_profile'],native_peers=3,real_clients=2,native_capture_cases=1,full_acceptance=False)

def compare_profiles(original,python):
    require(set(original)==set(python)==set(PEERS),'Two complete three-peer CP runs required')
    for reports,profile in ((original,'BlueprintFallback'),(python,'Python')):
        for report in reports.values():
            validate(report);require(report['requested_profile']==profile,'Original/Python comparison profile differs')
    require(original['server']['run_id']!=python['server']['run_id'],'Independent native groups required')
    for peer in PEERS:
        for key in ('team_scores','capture_stats','target_score','healths','damage_immunity','capture_audio_playing','native_score_widgets','hud','native_postgame','native_playing'):
            require(original[peer]['result'][key]==python[peer]['result'][key],'Original/Python CP checkpoint differs: '+peer+'/'+key)
    return dict(status='passed',native_processes=6,actual_clients=4,natural_capture_cases=2,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);print(json.dumps(validate_all(p.parse_args().directory)))
