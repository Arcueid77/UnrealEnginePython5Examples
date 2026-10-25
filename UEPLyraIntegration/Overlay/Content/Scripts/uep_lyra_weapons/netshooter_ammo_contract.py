"""Independent native last-round and explicit cost-refusal report checks."""
import argparse
import copy
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require
from .netshooter_network_contract import validate as validate_first_network_shots
from .weapon_ability_fire_network_contract import PLAN,PEERS

CLASS='/ShooterCore/Weapons/NetShooter_PROTO/GA_WeaponNetShooter.GA_WeaponNetShooter_C'
COST='Ability.ActivateFail.Cost'
MAGAZINE='Lyra.ShooterGame.Weapon.MagazineAmmo'


def configuration(report):
    require(report['native_cost_configuration']==[dict(native_class='/Script/LyraGame.LyraAbilityCost_ItemTagStack',
            tag=MAGAZINE,failure_tag=COST,quantity=1.)], 'Original one-round native item-tag cost configuration required')
    require(report['failure_observer_restored'],'Temporary inherited native failure observer did not restore')


def failure(events):
    require(events and all(e['native_class']==CLASS and e['native_ability'] and COST in e['tags'] for e in events),
            'Actual native cost-failure callback required; absence of another shot is insufficient')


def validate_standalone(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','Native Standalone ammo run failed')
    configuration(report)
    for flag in ('full_acceptance','network_acceptance','packaged_runtime','ammo_properties_written','health_properties_written',
                 'activation_handler_replayed','target_data_callback_replayed','projectile_spawn_requested_by_fixture'):
        require(report[flag] is False,'Unsupported prototype ammo claim: '+flag)
    for flag in ('production_profiles_restored','original_inventory_restored','original_player_health_unchanged',
                 'original_player_pose_control_movement_restored','original_view_target_restored','all_test_actors_destroyed',
                 'production_cue_binding_preserved','inherited_added_listener_once'):
        require(report[flag] is True,'Native prototype cleanup incomplete: '+flag)
    require([r['profile'] for r in report['cases']]==['BlueprintFallback','Python'],'Both actual native profiles required')
    for row in report['cases']:
        require(row['native_selected_profile']==row['profile'] and row['native_autoreload_grant_count_before']==row['native_autoreload_grant_count']==0,
                'Original prototype profile or zero AutoReload grant changed')
        require(row['input_gestures']==2 and row['input_released'] and row['ammo_before']==1 and
                row['ammo_after_last_round']==row['ammo_after_empty_attempt']==0 and row['ability_ended'],'Native last-round/empty-input outcome differs')
        require(row['first_shot']==dict(activations=1,target_data=1,projectiles=1,callbacks=['OnCompleted']) and
                row['after_empty']==row['first_shot'],'Empty input activated,delivered target data or spawned another projectile')
        require(row['policy_activations']==dict(activations=int(row['profile']=='Python'),fallback_activations=int(row['profile']=='BlueprintFallback')),
                'First native shot bypassed the selected original/Python policy')
        failure(row['native_failure_events'])
    return dict(status='passed',native_mode='Standalone',native_profile_pairs=1,natural_last_rounds=2,native_empty_cost_refusals=2,
                prototype_autoreload_grants=0,full_acceptance=False)


def validate_network(server,clients):
    # The original gate checks the first shot's wire identity/prediction/movement.
    # A projection excludes the separately checked second (empty) input gesture.
    projected_server=copy.deepcopy(server);projected_clients=copy.deepcopy(clients)
    for index,(owner,profile) in enumerate(PLAN):projected_clients[owner]['cases'][index]['input_gestures']=1
    positive=validate_first_network_shots(projected_server,projected_clients)
    for report in [server,*clients.values()]:
        configuration(report);require(report['ammo_exhaustion_only'],'Wrong native NetShooter test mode')
    for index,(owner,profile) in enumerate(PLAN):
        authority=server['cases'][index];client=clients[owner]['cases'][index];probe=client['empty_probe']
        require(authority['ammo_before']==client['ammo_before']==1 and authority['ammo_after']==client['ammo_after']==0,
                'Authority and real owner did not consume the same last native round')
        require(authority['empty_probe']==probe and probe['owner']==owner and probe['profile']==profile and
                probe['ammo_after']==0 and probe['activations']==probe['target_data']==1 and
                probe['input_gestures']==client['input_gestures']==2 and probe['input_released'] and client['input_released'],
                'Native owner empty-input capture differs from independently checked authority acknowledgment')
        require(probe['native_autoreload_grant_count']==authority['native_autoreload_grant_count']==client['native_autoreload_grant_count']==0,
                'Prototype received a synthetic AutoReload grant')
        failure(probe['native_failure_events'])
        for peer in PEERS:
            if peer!=owner:require(clients[peer]['cases'][index]['input_gestures']==0,'Foreign owner fired during empty-input validation')
    return dict(status='passed',owners=2,natural_last_rounds=4,native_empty_cost_refusals=4,
                prototype_autoreload_grants=0,first_shot_native_gate=positive,server_cost_failure_callback_required=False,
                full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--report');group.add_argument('--directory');args=parser.parse_args()
    read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
    if args.report:print(json.dumps(validate_standalone(read(args.report))))
    else:
        root=Path(args.directory);print(json.dumps(validate_network(read(root/'server.json'),{peer:read(root/(peer+'.json')) for peer in PEERS})))
