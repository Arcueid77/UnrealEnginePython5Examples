"""Real server RPCs, peer wire identity, owner filtering and both Profiles."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PEERS=('A','B0')
PLAN=(('kill','A','ps','BlueprintFallback'),('award','A','ps','BlueprintFallback'),('award','B0','pawn','BlueprintFallback'),('award','A','controller','BlueprintFallback'),('kill','B0','ps','Python'),('award','B0','ps','Python'),('award','A','pawn','Python'),('award','B0','controller','Python'),('award-null',None,None,'Python'),('parent',None,None,'Python'))
FALSE=('full_acceptance','packaged_runtime','pixels_tested','packet_loss_emulated','travel_rejoin_tested','callbacks_replayed','begin_play_replayed','player_health_or_movement_written','client_fixture_broadcasts','native_rpc_implementation_replaced')


def selected(command,peer):return command['kind']=='kill' or command['kind']=='award' and command['source_peer']==peer


def wire_key(value):
    require(isinstance(value,list) and len(value)==2 and value[0]=='Legacy' and isinstance(value[1],str) and value[1].isdecimal() and int(value[1])>0,'existing lossless native wire identity required')
    return tuple(value)


def validate_case(command,row,peer):
    require(row['index']==command['index'] and row['profile']==command['profile'],'foreign relay phase/profile')
    if peer=='server':
        matched=command['kind']!='parent';kind='kill' if command['kind']=='kill' else 'award'
        require(row['entries']==dict(kill=int(matched and kind=='kill'),award=int(matched and kind=='award')),'dedicated source callback count differs')
        require(row['receipts']==([command['expected_payload']] if matched else []),'dedicated source native payload differs')
        require(row['kill_notifications']==[] and row['award_notifications']==[],'dedicated server executed cosmetic notification')
        if command['profile']=='Python':
            require(row['side_effects']['multicast_requests']==int(command['kind']=='kill') and row['side_effects']['client_requests']==int(command['kind']=='award') and row['side_effects']['cosmetic_broadcasts']==0,'dedicated Python RPC/cosmetic sequence differs')
    else:
        delivery=selected(command,peer);kind='kill' if command['kind']=='kill' else 'award';entries=dict(kill=int(delivery and kind=='kill'),award=int(delivery and kind=='award'))
        require(row['entries']==entries,'actual RPC/owner or negative-window delivery differs')
        require(len(row['receipts'])==int(delivery),'one actual client native GMS payload required')
        if delivery:require(row['receipts'][0]==command['expected_payload'],'native RPC payload or wire actor identity changed')
        expected=command.get('expected_kill') if kind=='kill' else command.get('expected_award')
        require(row['kill_notifications']==([expected] if delivery and kind=='kill' else []) and row['award_notifications']==([expected] if delivery and kind=='award' else []),'actual typed cosmetic notification or owner filtering differs')
        if command['profile']=='Python':require(row['side_effects']['multicast_requests']==row['side_effects']['client_requests']==0 and row['side_effects']['cosmetic_broadcasts']==int(delivery),'remote client sent a server RPC or duplicated notification')
        require(row['observation_seconds']>=1.,'negative/nonowner RPC window too short')
    require(row['health_unchanged'] and row['diagnostic_fallbacks']==0,'relay changed Health or used diagnostic fallback')


def common(r,mode):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']==mode and r['network_acceptance'] is True,'native relay peer failed')
    for k in FALSE:require(r[k] is False,'network relay overclaim: '+k)
    require(r['observer_scopes_closed'] and r['profile_overrides_cleared'] and r['profile_classes_restored'] and r['probe_roots_removed'] and r['original_scores_restored'] and r['target_score_restored'],'network relay cleanup missing')
    require(r['native_relay_counts']==dict(kill=1,award=1) and r['callbacks_bound_once_native'],'natural production relay pair absent')
    require(len(r['cases'])==len(PLAN),'native relay matrix incomplete')


def validate(server,clients):
    common(server,'DedicatedServer');require(set(clients)==set(PEERS) and server['server_waited_for_client_process_exit'],'two clients/process-exit barrier missing')
    for peer in PEERS:
        common(clients[peer],'Client');require(clients[peer]['run_id']==server['run_id'] and clients[peer]['player_id']==server['roster'][peer]['player_id'],'wrong peer identity')
    require(wire_key(server['roster']['A']['state_wire'])!=wire_key(server['roster']['B0']['state_wire']),'same PlayerState reused for both clients')
    for index,plan in enumerate(PLAN):
        command=server['cases'][index]['command'];require((command['kind'],command['source_peer'],command['source_type'],command['profile'])==plan,'network relay plan changed')
        validate_case(command,server['cases'][index],'server')
        for peer in PEERS:validate_case(command,clients[peer]['cases'][index],peer)
    return dict(status='passed',native_server_cases=10,client_observation_cases=20,reliable_multicast_cases=2,unreliable_owner_delivery_cases=6,negative_server_cases=2,native_transport='Legacy',packet_loss_guarantee=False,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);root=Path(p.parse_args().directory)
    def read(peer):return json.loads((root/(peer+'.json')).read_text(encoding='utf-8-sig'))
    print(json.dumps(validate(read('server'),{peer:read(peer) for peer in PEERS})))
