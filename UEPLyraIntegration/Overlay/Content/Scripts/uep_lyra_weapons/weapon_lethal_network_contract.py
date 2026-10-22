"""Actual equipped-weapon input must produce the native lethal scoring chain."""
import argparse, json
from pathlib import Path
from .tdm_lethal_network_contract import validate as pipeline, PEERS, require, player_roles


def validate(report):
    pipeline(report, producer='weapon')
    require(report.get('weapon_owner_schema') == 2, 'explicit native owner evidence required')
    attacker, victim = player_roles(report.get('attacker_peer'))
    require(report.get('victim_peer') == victim, 'weapon victim must be the other actual client')
    roster = report['result']['roster'];source, target = roster[attacker], roster[victim]
    require(source['state_wire'] != target['state_wire'] and source['pawn_wire'] != target['pawn_wire'] and source['team'] != target['team'], 'native weapon owners/teams must be distinct')
    require(report['result']['foreign_weapon_activation_entries'] == 0, 'other owner weapon activated during selected input')
    receipts = [value for value in report['result']['relay_receipts'] if value['kind'] == 'kill']
    require(len(receipts) == 1 and receipts[0]['verb'] == 'Lyra.Elimination.Message' and receipts[0]['instigator'] == source['state_wire'] and receipts[0]['target'] == target['state_wire'], 'native elimination payload has wrong owner or victim')
    if report['peer'] != 'server':
        message, = report['result']['kill_notifications']
        require(message['attacker'] == source['name'] and message['attackee'] == target['name'] and message['attacker_team'] == source['team'] and message['attackee_team'] == target['team'], 'native kill feed owner/victim names or teams differ')
        require(message['channel'] == 'Lyra.AddNotification.KillFeed' and message['slot'] == 'HUD.Slot.EliminationFeed', 'native weapon kill feed channel/slot differs')
    require(report['actual_native_damage_spec_applied'] is False and report['fixture_damage_spec_applied'] is False, 'weapon gate must not manufacture damage')
    require(report['weapon_input_released'] and report['weapon_profile_classes_restored'], 'weapon input/observers not restored')
    if report['peer'] in ('server', victim):
        cost = report['result']['foreign_weapon_ammo']
        require(cost['before'] == cost['after'], 'other owner magazine changed during selected input')
    if report['peer'] in ('server', attacker):
        row = report['result']['weapon']
        require(row['native_pistol_definition'] and 1 <= row['ammo_before']-row['ammo_after'] <= row['ammo_before'] and row['ammo_after'] >= 0, 'actual equipped pistol cost missing')
        require(row['activation_entries'] >= 1 and row['target_data_entries'] >= 1 and row['target_hits'] >= 1 and row['only_requested_weapon_profile'], 'native input/target-data producer missing')
        activations, data = row['native_activation_events'], row['native_target_data_events']
        require(len(activations) == row['activation_entries'] and len(data) == row['target_data_entries'] and sum(event['target_hits'] for event in data) == row['target_hits'], 'native weapon event counts differ')
        require(all(event['source_wire'] == source['pawn_wire'] and event['authority'] == (report['peer'] == 'server') and event['profile'] == report['requested_profile'] for event in activations+data), 'native weapon source identity/authority/Profile differs')
        if report['peer'] == attacker:
            require(row['input_entry'] == 'PlayerController.inject_enhanced_input_for_action' and row['input_gestures'] == row['ammo_before']-row['ammo_after'] and row['native_clear_line_of_sight'], 'real owner weapon input and native trace required')
    return dict(status='passed', peer=report['peer'], profile=report['requested_profile'], native_weapon_lethal_cases=1, full_acceptance=False)


def validate_all(directory):
    root = Path(directory);reports = {peer:json.loads((root/(peer+'.json')).read_text(encoding='utf-8-sig')) for peer in PEERS}
    for peer, report in reports.items():
        validate(report);require(report['peer'] == peer, 'native weapon peer label differs')
    require(len({r['run_id'] for r in reports.values()}) == 1 and len({r['requested_profile'] for r in reports.values()}) == 1, 'mixed native weapon run/Profile')
    require(len({r['attacker_peer'] for r in reports.values()}) == 1 and len({r['victim_peer'] for r in reports.values()}) == 1, 'mixed native weapon owner roles')
    attacker, victim = player_roles(reports['server']['attacker_peer'])
    for peer in ('A','B0'):
        require(reports[peer]['result']['roster'] == reports['server']['result']['roster'] and reports[peer]['result']['relay_receipts'] == reports['server']['result']['relay_receipts'], 'native weapon relay identity/payload differs')
    require(reports['A']['result']['kill_notifications'] == reports['B0']['result']['kill_notifications'], 'native weapon kill-feed content differs')
    require(reports[attacker]['result']['weapon']['ammo_before'] == reports['server']['result']['weapon']['ammo_before'] and reports[attacker]['result']['weapon']['ammo_after'] == reports['server']['result']['weapon']['ammo_after'], 'owner/authority ammo replication differs')
    require(reports[victim]['result']['foreign_weapon_ammo'] == reports['server']['result']['foreign_weapon_ammo'], 'other owner/authority ammo replication differs')
    return dict(status='passed', native_peers=3, actual_weapon_owner=attacker, victim_peer=victim, real_clients=2, full_acceptance=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    print(json.dumps(validate_all(parser.parse_args().directory)))
