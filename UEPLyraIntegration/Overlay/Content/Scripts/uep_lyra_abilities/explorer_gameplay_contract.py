"""Actual original level actor interaction, native effects and reset semantics."""
import argparse,hashlib,json
from pathlib import Path
MAP='/ShooterExplorer/Maps/L_InteractionTestMap'
TARGETS={k:'/ShooterExplorer/Items/'+n+'.'+n+'_C' for k,n in (('collect','B_InteractableRock'),('sit','B_InteractableChair'))}
PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_input_tested','cpp_compile_executed','cook_package_executed','callbacks_replayed','inventory_or_health_written','abilities_granted_by_fixture','fixture_actors_spawned')
def require(value,message):
    if not value:raise ValueError(message)
def total(delta,name):return sum(delta.get(p+'_'+name,0) for p in ('python','fallback'))
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'actual Explorer gameplay failed')
    require(all(r[k] is False for k in FALSE_FIELDS),'Explorer gameplay scope overclaim')
    profile=r['selected_profile'];require(profile in PROFILES,'unsupported original/Python profile');prefix='python' if profile=='Python' else 'fallback';other='fallback' if profile=='Python' else 'python'
    require(r['world']==MAP+'.L_InteractionTestMap' and r['experience']=='/ShooterExplorer/System/Experiences/B_TestInventoryExperience.Default__B_TestInventoryExperience_C' and r['pawn_class']=='/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer_C' and r['native_role']==3,'original Explorer level/Experience/authority hero missing')
    require(r['native_level_open_requests']==2 and r['fixture_position_movement_and_aim'],'fresh profile map and native cleanup travel required')
    for key in ('selectors_restored','actual_exit_finalizer','pawn_pose_restored','level_targets_destroyed_after_travel','native_inventory_restored_after_travel','original_target_counts_restored','old_profile_pawns_and_controllers_destroyed','old_ability_instances_destroyed_after_travel','action_observers_restored'):require(r[key] is True,'native gameplay cleanup missing: '+key)
    require(r['actual_interactor_count']>=1 and all(r['initial_target_counts'][k]>0 for k in TARGETS),'placed original targets/natural interactors missing')
    require(r['native_input_asset_injections']==['IA_Interact','IA_Interact','IA_ToggleMarkerInWorld'],'actual native input sequence incomplete')
    require([a['kind'] for a in r['actions']]==['collect','sit'],'native collect/sit sequence incomplete')
    for a in r['actions']:
        require(a['target_class']==TARGETS[a['kind']] and a['actual_event_target_and_instigator'] and a['native_montage_seen'] and a['native_tasks_closed'],'original target/payload/montage/task chain incomplete')
        require(len(a['interactor_press_deltas'])==r['actual_interactor_count'] and all(d[prefix+'_press']==1 and d[other+'_press']==0 for d in a['interactor_press_deltas']),'real native input did not traverse selected Interact profile exactly once')
        require(a['action_deltas'] and all(d[prefix+'_activate']==1 and d[other+'_activate']==0 and d[prefix+'_end']==1 and d[other+'_end']==0 for d in a['action_deltas']),'collect/sit native activation/end did not use selected profile once')
        if a['kind']=='sit':require(a['inventory_after']==a['inventory_before'] and a['target_collision_after'] and a['target_lifespan_after']==0.,'native sit changed inventory or target lifetime')
        else:
            expected=dict(a['inventory_before'])
            for template in a['pickup_templates']:expected[template['definition']]=expected.get(template['definition'],0)+template['count']*len(a['action_deltas'])
            require(a['pickup_templates'] and expected==a['inventory_after'] and not a['target_collision_after'] and a['native_target_expired_after_three_seconds'],'native pickup amount/collision/three-second actor expiry differs from original template')
    require(r['recycled_collect_cues'] and all(c['alive'] and c['hidden'] and c['owner_cleared'] and c['splines']==0 and c['lifespan']==0. and total(c['counters'],'release')>=1 for c in r['recycled_collect_cues']),'original collect Cue did not recycle cleanly')
    require(r['marker'],'native marker target data missing')
    for m in r['marker']:
        require(m['has_actor'] and m['hit_actor_classes'] and m['native_tasks_closed'] and m['draw_center'] is not None and all(abs(a-b)<.01 for a,b in zip(m['endpoint'],m['draw_center'])),'native marker actor/draw endpoint or cleanup missing')
        require(all(m['deltas'][prefix+'_'+name]==1 and m['deltas'][other+'_'+name]==0 for name in ('activate','data','draw')),'marker profile activation/data/draw differs')
    require([i['kind'] for i in r['images']]==['collect','sit','marker'],'rendered native gameplay frames missing')
    for image in r['images']:
        data=Path(image['path']).read_bytes();require(data.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(data).hexdigest()==image['sha256'],'native PNG hash/header differs')
    return r
def validate_pair(reports):
    require(len(reports)==2 and tuple(r['selected_profile'] for r in reports)==PROFILES,'isolated Original/Python reports required')
    for r in reports:validate(r)
    first,second=reports
    for key in ('initial_inventory','initial_target_counts','actual_interactor_count','selected_class_paths'):require(first[key]==second[key],'original/Python native setup differs: '+key)
    for a,b in zip(first['actions'],second['actions']):
        for key in ('inventory_before','inventory_after','target_class'):require(a[key]==b[key],'original/Python gameplay outcome differs: '+key)
        require(len(a['action_deltas'])==len(b['action_deltas']),'original/Python accepted action counts differ')
    require(len(first['marker'])==len(second['marker']),'original/Python marker activation counts differ')
    return reports
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report');p.add_argument('--reports',nargs=2);a=p.parse_args()
    if a.reports:validate_pair([json.loads(Path(v).read_text(encoding='utf-8-sig')) for v in a.reports])
    elif a.report:validate(json.loads(Path(a.report).read_text(encoding='utf-8-sig')))
    else:p.error('--report or --reports required')
    print('UEP_EXPLORER_GAMEPLAY_GATE_PASSED')
