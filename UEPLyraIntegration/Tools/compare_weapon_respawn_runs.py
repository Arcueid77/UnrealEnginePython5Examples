"""Independently compare original/Python real-player natural respawn captures."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_weapons.weapon_respawn_network_contract import validate_all

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def require(value,message):
    if not value:raise ValueError(message)

def semantic_result(report):
    row=report['result'];victim=report['victim_peer'];attacker=report['attacker_peer']
    return dict(authored_target_score=row['authored_target_score'],score_delta=row['score_delta'],
        phase_still_playing=row['playing_active'] and not row['postgame_active'],old_pawn_ended=row['old_pawn_end_play_observed'],
        native_class=row['old_victim_class'],
        final_players={role:{key:row['after_new_life_fire'][peer][key] for key in ('native_class','health','attribute_health','death_state','asc_bound')} for role,peer in [('attacker',attacker),('victim',victim)]},
        new_life_ammo={key:row['new_life_fire'][key] for key in ('definition_is_pistol','ammo_before','ammo_after','activation_entries','target_data_entries')})

def compare(directories,*,verify_frozen=True):
    cases={};hashes=[];timings=[]
    for directory in directories:
        root=Path(directory);summary=read(root/'summary.json')
        require(summary['status']=='passed' and summary['external_gate']['exit_code']==0,'Respawn native/independent gate failed')
        require(set(summary['processes'])=={'server','A','B0'} and all(p['exit_code']==0 for p in summary['processes'].values()),'Three actual clean process exits required')
        validate_all(root);server=read(root/'server.json');key=(server['requested_profile'],server['attacker_peer'])
        require(summary['profile']==key[0] and summary['attacker_peer']==key[1] and summary['run_id']==server['run_id'],'Native driver/report profile,owner or run differs')
        require(key not in cases,'Duplicate profile/input owner respawn capture');cases[key]=server
        if verify_frozen:
            for record in summary['hashes']:
                require(hashlib.sha256(Path(record['path']).read_bytes()).hexdigest().upper()==record['sha256'].upper(),'Frozen natural respawn input changed: '+record['path'])
        hashes.append(dict(directory=str(root.resolve()),summary_sha256=hashlib.sha256((root/'summary.json').read_bytes()).hexdigest().upper(),
            reports={p:hashlib.sha256((root/(p+'.json')).read_bytes()).hexdigest().upper() for p in ('server','A','B0')}))
        timings.append(dict(profile=key[0],attacker=key[1],respawn_seconds=server['result']['respawn_seconds']))
    require(set(cases)=={(p,o) for p in ('BlueprintFallback','Python') for o in ('A','B0')},'Both profiles and both actual human input owners required')
    require(len({report['run_id'] for report in cases.values()})==4,'Distinct actual profile/owner runs required')
    pairs=[]
    for owner in ('A','B0'):
        original=semantic_result(cases[('BlueprintFallback',owner)]);python=semantic_result(cases[('Python',owner)])
        require(original==python,'Original/Python natural respawn outcome differs for '+owner)
        pairs.append(dict(attacker=owner,original_python_outcomes_equal=True,outcome=original))
    return dict(schema_version=1,status='passed',natural_human_deaths=4,natural_human_respawns=4,new_life_native_owner_fire_cases=4,actual_clean_native_processes=12,
        profile_owner_pairs=pairs,timings=timings,input_hashes=hashes,original_life_shot_count_or_timing_parity_claimed=False,
        standalone_tested=False,pixels_tested=False,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directories',nargs=4,required=True);parser.add_argument('--result',required=True);args=parser.parse_args()
    report=compare(args.directories);Path(args.result).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('profile_owner_pairs','timings','input_hashes')}))
