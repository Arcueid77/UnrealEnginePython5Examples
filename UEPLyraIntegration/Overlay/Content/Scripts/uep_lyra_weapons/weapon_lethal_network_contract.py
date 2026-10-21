"""Actual equipped-weapon input must produce the native lethal scoring chain."""
import argparse, json
from pathlib import Path
from .tdm_lethal_network_contract import validate as pipeline, PEERS, require


def validate(report):
    pipeline(report, producer='weapon')
    require(report['actual_native_damage_spec_applied'] is False and report['fixture_damage_spec_applied'] is False, 'weapon gate must not manufacture damage')
    require(report['weapon_input_released'] and report['weapon_profile_classes_restored'], 'weapon input/observers not restored')
    if report['peer'] in ('server', 'A'):
        row = report['result']['weapon']
        require(row['native_pistol_definition'] and 1 <= row['ammo_before']-row['ammo_after'] <= row['ammo_before'] and row['ammo_after'] >= 0, 'actual equipped pistol cost missing')
        require(row['activation_entries'] >= 1 and row['target_data_entries'] >= 1 and row['target_hits'] >= 1 and row['only_requested_weapon_profile'], 'native input/target-data producer missing')
        if report['peer'] == 'A':
            require(row['input_entry'] == 'PlayerController.inject_enhanced_input_for_action' and row['input_gestures'] == row['ammo_before']-row['ammo_after'] and row['native_clear_line_of_sight'], 'real owner weapon input and native trace required')
    return dict(status='passed', peer=report['peer'], profile=report['requested_profile'], native_weapon_lethal_cases=1, full_acceptance=False)


def validate_all(directory):
    root = Path(directory);reports = {peer:json.loads((root/(peer+'.json')).read_text(encoding='utf-8-sig')) for peer in PEERS}
    for peer, report in reports.items():
        validate(report);require(report['peer'] == peer, 'native weapon peer label differs')
    require(len({r['run_id'] for r in reports.values()}) == 1 and len({r['requested_profile'] for r in reports.values()}) == 1, 'mixed native weapon run/Profile')
    for peer in ('A','B0'):
        require(reports[peer]['result']['roster'] == reports['server']['result']['roster'] and reports[peer]['result']['relay_receipts'] == reports['server']['result']['relay_receipts'], 'native weapon relay identity/payload differs')
    require(reports['A']['result']['kill_notifications'] == reports['B0']['result']['kill_notifications'], 'native weapon kill-feed content differs')
    require(reports['A']['result']['weapon']['ammo_before'] == reports['server']['result']['weapon']['ammo_before'] and reports['A']['result']['weapon']['ammo_after'] == reports['server']['result']['weapon']['ammo_after'], 'owner/authority ammo replication differs')
    return dict(status='passed', native_peers=3, actual_weapon_owner='A', real_clients=2, full_acceptance=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    print(json.dumps(validate_all(parser.parse_args().directory)))
