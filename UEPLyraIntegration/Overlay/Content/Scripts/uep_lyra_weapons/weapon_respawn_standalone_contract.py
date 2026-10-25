"""Standalone native KillZ death, authored respawn and renewed owner input."""
import argparse,hashlib,json,math
from pathlib import Path
from .hero_burst_cue_contract import require

FORBIDDEN=('direct_health_writes','fixture_damage_spec_applied','death_events_replayed',
    'restart_called_by_fixture','pawn_spawned_by_fixture','ability_granted_by_fixture',
    'asc_initialized_by_fixture','world_settings_written','full_acceptance','network_acceptance')

def validate(report):
    require(report['status']=='passed' and report['error'] is None,'Standalone respawn failed')
    require(report['profile'] in ('Python','BlueprintFallback') and report['native_mode']=='Standalone','Actual Standalone profile required')
    require(report['native_bot_controllers']==0,'Unexpected combat producer in isolated KillZ case')
    for key in FORBIDDEN:require(report[key] is False,'Standalone respawn overclaim: '+key)
    for key in ('observer_scope_closed','profile_classes_restored','boot_selectors_restored','probe_roots_removed','input_released'):
        require(report[key] is True,'Standalone cleanup incomplete: '+key)
    row=report['result'];hazard=row['hazard'];old=row['before_death'];new=row['after_respawn'];final=row['after_new_life_fire']
    require(hazard['world_bounds_enabled'] and math.isfinite(hazard['kill_z']),'Authored world bounds required')
    require(hazard['kill_z']==hazard['kill_z_after'] and hazard['world_bounds_enabled_after'],'World bounds changed')
    require(hazard['placement_accepted'] and hazard['placed_z']<hazard['kill_z'],'Native Pawn was not placed below authored KillZ')
    require(row['death']['observed'] and row['death']['health']==0. and row['death']['pawn']==old['pawn'],'Actual native authority death required')
    require(row['old_pawn_end_play_observed'] and 0.<=row['respawn_seconds']<45.,'Natural Pawn retirement/respawn missing')
    require(old['pawn']!=new['pawn'] and new['pawn']==final['pawn'],'Fresh stable respawn Pawn required')
    for state in (old,new,final):
        require(state['player_state']==old['player_state'] and state['native_class']==old['native_class'],'Native class/PlayerState identity changed')
        require(state['health']==state['attribute_health']==100. and state['death_state']==0,'Living native health not restored')
        require(state['asc_bound'] and state['avatar']==state['pawn'],'Native health/ASC/avatar binding incomplete')
        require(state['profile']==report['profile'] and state['native_role']==3,'Standalone profile/authority differs')
    for fire,state in zip(row['fires'],(old,new)):
        require(fire['pawn']==state['pawn'] and fire['definition_is_pistol'],'Native life/inventory changed')
        require(fire['ammo_before']-fire['ammo_after']==1 and fire['gestures']==1 and fire['input_released'],'One real owner gesture/cost required per life')
        require({e['kind'] for e in fire['events']}=={'activate','target-data'},'Native ability/target-data entries missing')
        require(all(e['source']==state['pawn'] and e['profile']==report['profile'] and e['authority'] for e in fire['events']),'Fire crossed life/profile/authority')
    require(len(row['fires'])==2,'Both original and new-life owner input required')
    return dict(status='passed',standalone_natural_deaths=1,standalone_natural_respawns=1,native_owner_fire_cases=2,full_acceptance=False)

def semantic_result(report):
    validate(report);row=report['result']
    return dict(native_class=row['after_respawn']['native_class'],kill_z=row['hazard']['kill_z'],
        living={k:row['after_new_life_fire'][k] for k in ('health','attribute_health','death_state','asc_bound')},
        fires=[{k:f[k] for k in ('definition_is_pistol','ammo_before','ammo_after','gestures','input_released')} for f in row['fires']])

def compare_runs(directories,*,verify_frozen=True):
    cases={};inputs=[]
    for directory in directories:
        root=Path(directory);read=lambda name:json.loads((root/name).read_text(encoding='utf-8-sig'))
        summary=read('summary.json');report=read('respawn.json');validate(report)
        require(summary['status']=='passed' and summary['process']['exit_code']==summary['external_gate']['exit_code']==0,'Standalone native process/gate failed')
        require(summary['profile']==report['profile'] and report['profile'] not in cases,'Mixed or duplicate standalone profiles')
        require(not summary['cpp_compile_executed'] and not summary['cook_package_executed'],'Unexpected build/package in incremental standalone lane')
        if verify_frozen:
            require(summary['hashes'],'Frozen native inputs missing')
            for item in summary['hashes']:
                require(hashlib.sha256(Path(item['path']).read_bytes()).hexdigest().upper()==item['sha256'].upper(),'Frozen standalone input changed: '+item['path'])
        cases[report['profile']]=semantic_result(report)
        inputs.append(dict(directory=str(root.resolve()),summary_sha256=hashlib.sha256((root/'summary.json').read_bytes()).hexdigest().upper(),
            report_sha256=hashlib.sha256((root/'respawn.json').read_bytes()).hexdigest().upper()))
    require(set(cases)=={'Python','BlueprintFallback'},'Both standalone profiles required')
    require(cases['Python']==cases['BlueprintFallback'],'Standalone original/Python outcome differs')
    return dict(status='passed',standalone_natural_deaths=2,standalone_natural_respawns=2,native_owner_fire_cases=4,
        actual_clean_native_processes=2,outcome=cases['Python'],input_hashes=inputs,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--report');group.add_argument('--directories',nargs=2);parser.add_argument('--result')
    args=parser.parse_args()
    if args.report:print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding='utf-8-sig')))))
    else:
        require(args.result,'Standalone comparison result path required');result=compare_runs(args.directories)
        Path(args.result).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ('outcome','input_hashes')}))
