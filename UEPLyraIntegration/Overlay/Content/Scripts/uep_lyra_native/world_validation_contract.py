"""Independent native frontend/parts/camera runtime acceptance boundaries."""
import argparse
import json
from pathlib import Path


def require(value,message):
    if not value:raise AssertionError(message)


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['selector_restored'] and report['owned_actors_destroyed'],'world policy runtime/cleanup failed')
    require(not report['online_service_tested'] and not report['physical_input_tested'] and not report['network_replication_tested'],'world policy runtime overclaim')
    kind,selected=report['kind'],report['profile'].endswith('Python');metrics=report['world_policy_metrics']
    if kind=='frontend':
        require(report['actual_offline_frontend_completed'] and report['initialization_callback_results_supplied_by_fixture'] and report['callbacks_replayed'],'actual offline flow/native callback fixture missing')
        require(report['native_initialization_callback_results']==[dict(success=s,continued_and_unbound=True) for s in (True,False)],'native callback did not continue or remove its delegate')
        for operation in ('Frontend.Plan','Frontend.Initialize','Frontend.PressStart','Frontend.JoinRequested','Frontend.Main','Frontend.MainWidget'):
            require(metrics['applied'].get(operation,0)>0 if selected else metrics['applied'].get(operation,0)==0,'actual frontend route differs: '+operation)
        require(metrics['applied'].get('Frontend.UserInitialized',0)>=2 if selected else metrics['applied'].get('Frontend.UserInitialized',0)==0,'native callback result route differs')
    elif kind=='parts':
        p=report['parts'];base=[dict(source=s,valid=True) for s in (0,0,2,3)]
        require(report['parts_restored'] and p['pawn_replacement_entry']=='original native Reset request','original controller parts or native Reset entry not preserved')
        require(p['sources_before']==p['unsuppressed']==base and len(p['actors_before'])==4,'original natural/developer/cheat sources differ')
        require(p['suppressed']==[dict(source=s,valid=v) for s,v in ((1,False),(1,False),(2,True),(3,True))] and len(p['actors_suppressed'])==2,'suppression affected developer or cheat parts')
        after=[dict(source=s,valid=True) for s in (0,2,3)]
        require(p['remove_first_equivalent']==p['attached']==p['same_pawn_notification']==after,'first equivalent removal or actual possession rebind differs')
        require(p['detached']==[dict(source=s,valid=False) for s in (0,2,3)] and p['old_actor_count_after_detach']==0 and p['duplicate_notification_preserved_actors'] and p['removed_all'] and p['original_spawn_effect_completed_before_owned_state_cleanup'],'old Pawn or duplicate notification leaked cosmetic actors')
        require(sum(v for k,v in metrics['applied'].items() if k.startswith('Parts.'))>0 if selected else not any(v for k,v in metrics['applied'].items() if k.startswith('Parts.')),'part policy route differs')
    else:
        require(kind=='camera','unknown world runtime kind');camera=report['camera']
        require(camera['default'] and camera['ability_mode'] and camera['ability_priority'] and camera['foreign_handle_preserves'] and camera['actual_ability_end_restores'] and camera['missing_pawn_and_data_return_null']==[True,True] and camera['native_ability_camera_methods'],'native ability/default/missing camera lifecycle differs')
        require(metrics['camera_choices']>0 if selected else metrics['camera_choices']==0,'native camera policy route differs')
    return dict(status='passed',kind=kind,profile=report['profile'],online_service_tested=False,network_replication_tested=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
