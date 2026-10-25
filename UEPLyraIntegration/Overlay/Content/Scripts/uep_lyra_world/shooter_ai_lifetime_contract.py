"""Live native BT cancellation must release destroyed Pawn/World ownership."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
FORBIDDEN=('health_properties_written','native_bt_scheduler_replaced','native_wait_time_written','bt_callbacks_replayed','stop_logic_called_as_cancellation','full_acceptance','network_acceptance','packaged_runtime')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('BlueprintFallback','Python') and r['mode'] in ('tdm','cp') and r['native_mode']=='Standalone','AI lifetime runtime failed')
    for k in FORBIDDEN:require(r[k] is False,'AI lifetime shortcut: '+k)
    for case in r['running_cases']:
        require(case['native_brain_running'] and case['task_class']=='BTTask_Wait' and case['wait_seconds']>case['elapsed']>0,'Actual still-running native Wait required')
        require(case['native_ammo_ticks']>=3 and len(case['intervals'])>=2 and all(.35<=v<=.75 for v in case['intervals'][-2:]),'Original native service schedule missing')
    require(len(r['running_cases'])==2 and [v['purpose'] for v in r['running_cases']]==['pawn-destroy','world-travel'],'Both lifetime boundaries required')
    for k in ('pawn_endplay_observed','native_unpossess_stopped_brain','native_unpossess_cleared_enemy','pawn_destroy_callbacks_quiet','native_world_replaced','world_owner_endplay_observed','world_callbacks_quiet','owned_endplay_scopes_closed','python_object_references_released','old_world_and_ai_objects_collected','profiles_and_class_roots_restored','player_health_unchanged_before_travel'):
        require(r[k] is True,'AI lifetime cleanup missing: '+k)
    require(r['gc_requested'] and r['quiet_seconds_after_destroy']>=.8 and r['quiet_seconds_after_world_endplay']>=.8,'Native cleanup/quiet evidence missing')
    require(r['retained_old_objects']==[],'Collected native objects must be absent')
    require(r['pawn_destroy_callbacks_before'] and r['pawn_destroy_callbacks_before']==r['pawn_destroy_callbacks_after'],'Destroyed Pawn service callbacks continued')
    require(r['player_health_before']==r['player_health_before_travel'] and r['player_health_before']['health']>0,'Actual local-player health observations differ')
    return dict(status='passed',profile=r['profile'],mode=r['mode'],native_lifetime_boundaries=2,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
