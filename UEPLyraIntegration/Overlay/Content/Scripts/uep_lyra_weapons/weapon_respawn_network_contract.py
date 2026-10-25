"""Real owner fire -> other human death -> native respawn -> new-life input."""
import argparse,json
from pathlib import Path
from .hero_burst_cue_contract import require

PEERS=('server','A','B0')
FORBIDDEN=('direct_health_writes','fixture_damage_spec_applied','death_events_replayed',
    'restart_called_by_fixture','pawn_spawned_by_fixture','ability_granted_by_fixture',
    'asc_initialized_by_fixture','native_rpc_replaced','full_acceptance')

def validate(report):
    require(report['status']=='passed' and report['error'] is None,'Natural respawn peer failed')
    peer=report['peer'];require(peer in PEERS,'Unknown respawn peer')
    require(report['requested_profile'] in ('Python','BlueprintFallback'),'Unknown respawn profile')
    for key in FORBIDDEN:require(report[key] is False,'Respawn fixture overclaim: '+key)
    for key in ('observer_scopes_closed','profile_classes_restored','probe_roots_removed',
        'boot_selectors_restored','weapon_input_released','weapon_profile_classes_restored','respawn_scope_closed'):
        require(report[key] is True,'Natural respawn cleanup missing: '+key)
    attacker=report['attacker_peer'];victim=report['victim_peer'];require({attacker,victim}=={'A','B0'},'Two actual human owners required')
    row=report['result'];old=row['roster'];new=row['after_respawn'];final=row['after_new_life_fire']
    require(row['authored_target_score']>1 and row['target_score_at_arm']==row['authored_target_score'],'Authored non-winning score condition required')
    require(row['death']['observed'] and row['death']['zero_health_observed'] and row['death']['pawn_wire']==old[victim]['pawn_wire'],'Native old-Pawn death and zero-health transition were not observed')
    if peer=='server':require(row['death']['health']==0.,'Authority death callback did not follow lethal health')
    require(row['old_pawn_end_play_observed'],'Old native Pawn did not end play')
    require(row['phase_state_authoritative']==(peer=='server'),'Phase subsystem authority label differs')
    if peer=='server':require(not row['postgame_active'] and row['playing_active'],'Natural respawn must stay in authoritative Playing')
    require(row['score_delta']==dict(kills=1,deaths=1,team=1,other=0),'Natural kill score differs')
    for phase in (new,final):
        for owner in ('A','B0'):
            value=phase[owner]
            require(value['state_wire']==old[owner]['state_wire'] and value['health']==value['attribute_health']==100.,'State identity/health not restored')
            require(value['asc_bound'] and value['avatar_wire']==value['pawn_wire'] and value['death_state']==0,'New native health/ASC binding incomplete')
            require(value['profile']==report['requested_profile'],'Pawn selected the wrong original/Python profile')
        require(phase[attacker]['pawn_wire']==old[attacker]['pawn_wire'],'Unkilled owner Pawn changed')
        require(phase[victim]['pawn_wire']!=old[victim]['pawn_wire'] and phase[victim]['native_class']==row['old_victim_class'],'Natural replacement must retain native class identity')
    require(new[victim]['pawn_wire']==final[victim]['pawn_wire'],'A second replacement occurred during new-life input')
    require(row['respawn_seconds']>=0.,'Native respawn timing missing')
    if peer in ('server',attacker):
        fire=row['first_kill_fire'];require(report['native_weapon_damage_observed'] and fire['ammo_before']>fire['ammo_after']>=0,'Actual original-life weapon damage/cost missing')
        require(fire['activation_events'] and sum(e['target_hits'] for e in fire['target_data_events'])>=1,'Original-life native target data missing')
        require(all(e['source_wire']==old[attacker]['pawn_wire'] and e['profile']==report['requested_profile'] and e['authority']==(peer=='server') for e in fire['activation_events']+fire['target_data_events']),'Original-life weapon source/authority/profile differs')
        if peer==attacker:require(fire['gestures']==fire['ammo_before']-fire['ammo_after'],'Original-life native input cost differs')
    if peer in ('server',victim):
        fire=row['new_life_fire'];require(fire['definition_is_pistol'] and fire['ammo_before']-fire['ammo_after']==1,'New native inventory/input cost missing')
        require(fire['activation_entries']>=1 and fire['target_data_entries']>=1,'New-life native ability/target-data entry missing')
        require(fire['activation_entries']==sum(e['kind']=='activate' for e in fire['events']) and fire['target_data_entries']==sum(e['kind']=='target-data' for e in fire['events']),'New-life event counts differ')
        require(all(e['source_wire']==new[victim]['pawn_wire'] and e['profile']==report['requested_profile'] and e['authority']==(peer=='server') for e in fire['events']),'New-life input crossed identity/authority/profile')
        if peer==victim:require(fire['gestures']==1 and fire['input_released'],'One real new-life owner gesture required')
    else:require(row['foreign_inventory_sampled'] is False,'Foreign client must not sample another owner inventory')
    if peer=='server':require(report['server_waited_for_client_process_exit'],'Authority exited before clients')
    return dict(status='passed',peer=peer,natural_human_respawns=1,full_acceptance=False)

def validate_all(directory):
    root=Path(directory);reports={peer:json.loads((root/(peer+'.json')).read_text(encoding='utf-8-sig')) for peer in PEERS}
    for report in reports.values():validate(report)
    require(len({r['run_id'] for r in reports.values()})==len({r['requested_profile'] for r in reports.values()})==len({r['attacker_peer'] for r in reports.values()})==1,'Mixed respawn run/profile/owner')
    reference=reports['server']['result'];victim=reports['server']['victim_peer']
    for report in reports.values():
        row=report['result'];require(row['roster']==reference['roster'],'Original roster differs')
        require({p:v['pawn_wire'] for p,v in row['after_respawn'].items()}=={p:v['pawn_wire'] for p,v in reference['after_respawn'].items()},'Replicated new Pawn identities differ')
    require(reports[victim]['result']['new_life_fire']['ammo_before']==reference['new_life_fire']['ammo_before'] and reports[victim]['result']['new_life_fire']['ammo_after']==reference['new_life_fire']['ammo_after'],'New-life owner/authority ammo differs')
    return dict(status='passed',native_peers=3,real_clients=2,natural_human_respawns=1,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    print(json.dumps(validate_all(parser.parse_args().directory)))
