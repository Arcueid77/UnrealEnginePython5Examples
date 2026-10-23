"""Require placed original AI to navigate, cancel/restart and release old World."""
import argparse,json
from pathlib import Path
MAP='/ShooterExplorer/Maps/L_StateTree_FollowTest'
RESET_MAP='/ShooterExplorer/Maps/L_InventoryTestMap'
TREE='/ShooterExplorer/AI/StateTrees/Trees/L_STT_FollowPlayer.L_STT_FollowPlayer'
PAWN='/ShooterExplorer/Blueprint/B_Pawn_Explorer.B_Pawn_Explorer_C'
PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_input_tested','cpp_compile_executed','cook_package_executed','callbacks_replayed','inventory_or_health_written','abilities_granted_by_fixture','fixture_actors_spawned','fixture_ai_or_task_spawned','tree_asset_or_bindings_edited','task_events_or_callbacks_replayed','unused_evaluator_or_delay_claimed_as_map_execution')
def require(value,message):
    if not value:raise ValueError(message)
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'actual follow-map validation failed')
    require(all(r[k] is False for k in FALSE_FIELDS),'follow-map scope overclaim')
    require(r['selected_profile'] in PROFILES and r['original_tree']==TREE and r['native_level_open_requests']==2,'original tree/profile/fresh map and cleanup travel required')
    require(len(r['placed_pawns'])==3 and all(p['cls']==PAWN for p in r['placed_pawns']),'all three original placed Explorer Pawns required')
    for key in ('selectors_restored','templates_and_observers_restored','player_pose_restored','actual_exit_finalizer','original_placed_ai_destroyed_after_travel','original_runtime_nodes_destroyed_after_travel','old_profile_pawns_and_controllers_destroyed','inventory_preserved_after_travel'):require(r[key] is True,'native follow-map cleanup missing: '+key)
    require(r['late_callbacks_after_travel']==0,'old tree callbacks continued after World teardown')
    require(r['garbage_collection_checked_frame']>r['garbage_collection_requested_frame'],'node cleanup was checked before deferred native GC could run')
    require(len(r['waypoints'])==2,'two complete native navigation waypoints required')
    for row in r['waypoints']:
        require(row['arrived'] and row['native_success_delta']>=1 and row['plans'] and all(not p['partial'] and p['points']>=2 and p['length']>1000. for p in row['plans']),'native full route or actual AI arrival/completion missing')
        require(len(row['ai_start'])==len(row['ai_end']) and all(sum((a-b)**2 for a,b in zip(start,end))>500.**2 for start,end in zip(row['ai_start'],row['ai_end'])),'placed AI did not actually move along original navigation')
    totals=r['totals'];require(totals['location_tick']>=3 and totals['goto_enter']>=1 and totals['follow_enter']>=1 and totals['goto_success']>=1 and totals['follow_success']>=1,'original location/GoTo/Follow successful navigation callbacks incomplete')
    require(r['node_observations'] and all(n['profile']==r['selected_profile'] and n['location_mismatches']==0 for n in r['node_observations']),'wrong task profile or native player-zero location')
    locations=[n for n in r['node_observations'] if n['kind']=='location']
    require(locations and all(n['location_samples']>=3 and n['last_location'] is not None and n['last_player_location'] is not None for n in locations),'actual completed global location updates were not sampled')
    require(r['cancel']['moving_before']>=1 and r['cancel']['stopped'] and r['cancel']['quiet_after_drain'],'active original AI cancel/quiet missing')
    require(r['restart']['running'] and r['restart']['moving']>=1 and r['restart']['native_callbacks_resumed'] and r['restart']['travel_while_move_active'],'native original tree restart and in-flight travel missing')
    return r
def validate_pair(reports):
    require(len(reports)==2 and tuple(r['selected_profile'] for r in reports)==PROFILES,'isolated original/Python follow-map reports required')
    for r in reports:validate(r)
    first,second=reports
    require(first['selected_class_paths']==second['selected_class_paths'] and first['template_count']==second['template_count'],'original/Python class/template selection scope differs')
    require([p['use_behavior_tree'] for p in first['placed_pawns']]==[p['use_behavior_tree'] for p in second['placed_pawns']],'placed original AI modes differ')
    require(first['initial_inventory']==second['initial_inventory'],'original/Python player inventory differs')
    return reports
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report');p.add_argument('--reports',nargs=2);a=p.parse_args()
    if a.reports:validate_pair([json.loads(Path(v).read_text(encoding='utf-8-sig')) for v in a.reports])
    elif a.report:validate(json.loads(Path(a.report).read_text(encoding='utf-8-sig')))
    else:p.error('--report or --reports required')
    print('UEP_EXPLORER_FOLLOW_GATE_PASSED')
