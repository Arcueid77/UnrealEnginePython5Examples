"""Real local-owner bomb,opponent death and native elimination score."""
import argparse,hashlib,json,math
from pathlib import Path

FORBIDDEN=('direct_ability_activation','callbacks_replayed','manual_bomb_spawn','attributes_written',
    'damage_applied_by_fixture','explosion_called_by_fixture','death_called_by_fixture',
    'scores_written_by_fixture','fuse_written_by_fixture','physical_input_tested','packaged_runtime','full_acceptance','network_acceptance')
def require(value,message):
    if not value:raise ValueError(message)

def validate(report):
    require(report['status']=='passed' and report['error'] is None,'Arena opponent lane failed')
    require(report['profile'] in ('Python','BlueprintFallback'),'Unknown Arena profile')
    require(report['map']=='L_TopDown_LocalMultiplayer' and report['native_mode']=='Standalone','Original local Arena map required')
    require(report['local_players']==2 and report['distinct_player_owners'],'Two real local owners required')
    require(report['ability_granted_by_original_experience'] and report['input_action_from_original_pawn_data'],'Original ability/input data required')
    for key in FORBIDDEN:require(report[key] is False,'Arena fixture overclaim: '+key)
    require(report['pawn_position_written'] and report['bounded_pose_fixture_used'],'Declared native pose fixture required')
    for key in ('cleanup_complete','native_local_player_removed','death_observer_closed','message_observer_closed','input_released'):
        require(report[key] is True,'Arena cleanup incomplete: '+key)
    row=report['result'];fire=row['drop']
    require(row['health_before']==[100.,100.] and row['health_after']==[100.,0.],'Bomb must kill only the opponent')
    require(row['opponent_death']['observed'] and row['opponent_death']['health']==0. and row['opponent_death']['player_state']==report['owners'][1]['player_state'],'Actual opponent native death required')
    require(fire['owner']==0 and fire['new_bombs']==1 and fire['instigator_matches_owner'] and fire['saved_state_matches_owner'],'Native bomb source ownership differs')
    require(fire['remaining_before']==[1.,1.] and fire['remaining_after']==[0.,1.] and fire['foreign_owner_unchanged'],'Native owner-only cost differs')
    require(fire['bomb_profiles_match'] and row['selected_input_callbacks']>0 and row['other_input_callbacks']==0,'Selected original/Python input path differs')
    require(isinstance(row['original_explosion_radius'],int) and row['original_explosion_radius']>0,'Authored blast radius required')
    require(row['native_bomb_callbacks']==dict(trigger=1,increment=row['original_explosion_radius'],destroyed=1),'Natural fuse/each authored expansion/destruction required')
    require(row['remaining_after_refund']==[1.,1.] and row['bombs_destroyed_by_cleanup']==0,'Native refund must precede cleanup')
    messages=report['native_elimination_messages'];require(len(messages)==1,'One real native elimination receipt required')
    receipt=messages[0]
    require(receipt['channel']=='Lyra.Elimination.Message' and receipt['target_is_opponent'] and receipt['target']==report['owners'][1]['player_state'],'Native elimination has wrong victim')
    if receipt['team_comparison']=='DifferentTeams':
        require(receipt['source_owner']==0 and not receipt['instigator_is_null'],'Native credit requires the actual bomb owner')
        scores,teams=[[1,0,0],[0,1,0]],[1,0]
    else:
        # Original Arena bomb applies a self effect without a supplied source
        # context. Keep its actual null/self attribution visible, rather than
        # inventing a credited enemy kill for the Python implementation.
        require((receipt['team_comparison']=='InvalidArgument' and receipt['instigator_is_null'] and receipt['source_owner'] is None) or
            (receipt['team_comparison']=='OnSameTeam' and receipt['source_owner']==1 and not receipt['instigator_is_null']),'Unexplained native elimination attribution')
        scores,teams=[[0,0,0],[0,0,0]],[0,0]
    require(row['score_delta']==scores and row['team_score_delta']==teams,'Scores must follow actual native elimination attribution')
    require(row['different_native_teams'] and row['selected_elimination_callbacks']==1 and row['other_elimination_callbacks']==0,'Real selected scoring path required')
    require(row['original_fuse_seconds']>0. and row['fixed_timestep_used'] is False,'Authored fuse and variable-frame execution required')
    elapsed=row['opponent_death']['seconds_after_bomb_creation'];fuse=row['original_fuse_seconds']
    require(math.isfinite(elapsed) and math.isfinite(fuse) and fuse-.1<=elapsed<=fuse+2.,'Native opponent death must follow the authored fuse')
    return dict(status='passed',native_opponent_eliminations=1,native_local_players=2,full_acceptance=False)

def outcome(report):
    validate(report);row=report['result']
    value={k:row[k] for k in ('health_before','health_after','score_delta','team_score_delta','remaining_after_refund','native_bomb_callbacks','original_fuse_seconds','original_explosion_radius')}
    value['elimination_attribution']={k:report['native_elimination_messages'][0][k] for k in ('instigator_is_null','source_owner','team_comparison','target_is_opponent')}
    return value

def compare(directories,*,verify_frozen=True):
    cases={};inputs=[]
    for directory in directories:
        root=Path(directory);read=lambda n:json.loads((root/n).read_text(encoding='utf-8-sig'))
        summary=read('summary.json');report=read('result.json');validate(report)
        require(summary['status']=='passed' and summary['process']['exit_code']==summary['external_gate']['exit_code']==0,'Arena native process/gate failed')
        require(summary['cpp_compile_executed'] is False and summary['cook_package_executed'] is False,'Arena lane must reuse the existing build')
        require(summary['profile']==report['profile'] and report['profile'] not in cases,'Mixed/duplicate Arena profile')
        if verify_frozen:
            require(summary['hashes'],'Frozen Arena inputs missing')
            for item in summary['hashes']:require(hashlib.sha256(Path(item['path']).read_bytes()).hexdigest().upper()==item['sha256'].upper(),'Frozen Arena input changed: '+item['path'])
        cases[report['profile']]=outcome(report)
        inputs.append(dict(directory=str(root.resolve()),summary_sha256=hashlib.sha256((root/'summary.json').read_bytes()).hexdigest().upper(),report_sha256=hashlib.sha256((root/'result.json').read_bytes()).hexdigest().upper()))
    require(set(cases)=={'Python','BlueprintFallback'},'Both Arena profiles required')
    require(cases['Python']==cases['BlueprintFallback'],'Original/Python opponent outcome differs')
    return dict(status='passed',native_opponent_eliminations=2,actual_clean_native_processes=2,outcome=cases['Python'],input_hashes=inputs,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--report');group.add_argument('--directories',nargs=2);parser.add_argument('--result');args=parser.parse_args()
    if args.report:print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding='utf-8-sig')))))
    else:
        require(args.result,'Arena comparison result required');result=compare(args.directories)
        Path(args.result).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('outcome','input_hashes')}))
