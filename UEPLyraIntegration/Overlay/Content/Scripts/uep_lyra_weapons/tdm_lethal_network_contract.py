"""Native lethal GAS -> scoring -> postgame -> two real client notifications."""
import argparse, json
from pathlib import Path
from .hero_burst_cue_contract import require

PEERS = ('server', 'A', 'B0')
FALSE_FIELDS = ('full_acceptance', 'packaged_runtime', 'pixels_tested', 'physical_weapon_input_tested',
    'direct_health_writes', 'death_events_replayed', 'elimination_messages_broadcast_by_fixture',
    'phase_start_or_victory_callbacks_called_by_fixture', 'native_rpc_replaced', 'travel_rejoin_tested')


def player_roles(attacker='A'):
    require(attacker in ('A', 'B0'), 'native lethal attacker must be an actual client')
    return attacker, 'B0' if attacker == 'A' else 'A'


def validate(report, *, producer='gas'):
    require(report['status'] == 'passed' and report['error'] is None and report['peer'] in PEERS, 'native lethal network peer failed')
    require(report['requested_profile'] in ('BlueprintFallback', 'Python') and report['profiles_selected_before_component_creation'], 'early original/Python scoring/phase selection required')
    for key in FALSE_FIELDS:
        require(report[key] is False, 'native lethal network overclaim: '+key)
    for key in ('observer_scopes_closed', 'profile_classes_restored', 'probe_roots_removed', 'target_score_restored', 'original_scores_restored', 'boot_selectors_restored'):
        require(report[key], 'lethal pipeline cleanup missing: '+key)
    row = report['result']
    attacker, victim = player_roles(report.get('attacker_peer', 'A'))
    require(report.get('victim_peer', victim) == victim, 'native lethal victim must be the other client')
    require(row['attacker_health'] == 100. and row['victim_health'] == 0., 'native targeted lethal damage/foreign invariance differs')
    require(row['attacker_kills_delta'] == row['victim_deaths_delta'] == row['attacker_team_score_delta'] == 1 and row['other_team_score_delta'] == 0, 'native score replication differs')
    require(row['target_score'] == 1 and row['postgame_damage_immunity'], 'configured victory/postgame native immunity missing')
    if report['peer'] == 'server':
        require(report['server_waited_for_client_process_exit'], 'authority exited before actual client processes')
        produced = report['actual_native_damage_spec_applied'] if producer == 'gas' else report.get('native_weapon_damage_observed', False)
        require(row['native_postgame_phase_active'] and row['native_playing_phase_inactive'] and produced, 'natural authoritative phase transition missing')
        require(row['relay_entries']['kill'] == 1 and not row['kill_notifications'], 'dedicated relay or zero cosmetic branch differs')
        require(row['selected_tdm_elimination_calls'] == row['selected_tdm_victory_calls'] == 1, 'requested scoring Profile never handled native victory')
    else:
        require(len(row['kill_notifications']) == 1 and row['relay_entries']['kill'] == 1 and row['native_match_decided_cue_actors'] >= 1, 'actual client RPC/cosmetic notification or winner cue missing')
    return dict(status='passed', peer=report['peer'], profile=report['requested_profile'], native_lethal_cases=1, full_acceptance=False)


def validate_all(directory):
    root = Path(directory)
    reports = {peer: json.loads((root/(peer+'.json')).read_text(encoding='utf-8-sig')) for peer in PEERS}
    for report in reports.values():
        validate(report)
    reference = reports['server']['result']
    for peer in ('A', 'B0'):
        row = reports[peer]['result']
        require(row['roster'] == reference['roster'], 'native player wire identity or team mapping differs')
        require(row['relay_receipts'] == reference['relay_receipts'], 'actual native reliable RPC payload changed')
    require(reports['A']['result']['kill_notifications'] == reports['B0']['result']['kill_notifications'], 'two clients received different native kill feed content')
    return dict(status='passed', native_peers=3, real_clients=2, profile=reports['server']['requested_profile'], full_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--directory', required=True)
    print(json.dumps(validate_all(parser.parse_args().directory)))
