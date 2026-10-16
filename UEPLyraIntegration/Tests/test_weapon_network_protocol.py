"""Negative evidence contracts; synthetic data is never gameplay acceptance."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Overlay' / 'Content' / 'Scripts'))
from uep_lyra_weapon_protocol import PHASES, validate_reports


def fixture():
    values = {p: {'magazine': 12, 'maximum': 12, 'spare': 48, 'slot': 0, 'definition': 'Pistol', 'item': p + '-item'}
              for p in ('A', 'B0', 'B1')}
    players = {p: {'controller_path': p + '-controller', 'player_id': i + 1,
                   'world_token': p + '-world', 'pawn_path': p + '-pawn'} for i, p in enumerate(values)}
    observers = {p: {'source': 'read-only-frame-sampler', 'unsubscribed': 0, 'errors': [], 'native_signals': 0,
                     'active_scopes': 1, 'message_source': 'native-QuickBar-and-possession-signals'} for p in values}
    frames = dict.fromkeys(values, 0)
    rows = []
    for index, phase in enumerate(PHASES):
        peers = ['A'] if phase in ('join_a', 'fire_a_solo') else ['A', 'B1' if index >= 16 else 'B0']
        target = ('B0' if phase in ('fire_b', 'empty_b', 'reload_b', 'fire_travel_b') else
                  'B1' if phase == 'fire_b1' else
                  'A' if phase.startswith(('fire_', 'reload_', 'switch_', 'respawn_')) else None)
        statuses = {p: {'player': copy.deepcopy(players[p]), 'weapon_observer': copy.deepcopy(observers[p]),
                        'input_frames': frames[p]} for p in peers}
        if phase.startswith('travel_'):
            for p in peers:
                players[p]['world_token'] += '-next'
                observers[p]['unsubscribed'] += 2
        if phase == 'respawn_a':
            players['A']['pawn_path'] += '-next'
        roster = {p: {**copy.deepcopy(players[p]), 'weapon': copy.deepcopy(values[p])} for p in peers}
        if target:
            value = values[target]
            if phase.startswith('fire_') or phase == 'empty_b':
                value['magazine'] = 0 if phase == 'empty_b' else value['magazine'] - 3
                frames[target] += 10
            elif phase.startswith('reload_'):
                value['spare'] -= value['maximum'] - value['magazine']
                value['magazine'] = value['maximum']
            elif phase == 'switch_a':
                value['slot'] = 1
                value['definition'] = 'Rifle'
                observers[target]['native_signals'] += 1
        packet = {'run_id': 'run', 'phase_index': index, 'phase': phase, 'participants': peers,
                  'target': target, 'roster': roster, 'statuses_before': statuses}
        acks = {}
        for peer in peers:
            value = values[peer]
            visible = {'magazine': str(value['magazine']), 'spare': str(value['spare']), 'visibility': 0}
            acks[peer] = {'run_id': 'run', 'peer': peer, 'phase_index': index, 'phase': phase,
                          'player': copy.deepcopy(players[peer]), 'weapon': copy.deepcopy(value),
                          'input_frames': frames[peer], 'weapon_observer': copy.deepcopy(observers[peer]),
                          'aim_rotation': {'pitch': 80.0, 'roll': 0.0, 'yaw': 0.0},
                          'weapon_hud': {'profile': 'Python', 'class': 'W_WeaponAmmoAndName_C',
                                         'controller': players[peer]['controller_path'],
                                         'python': copy.deepcopy(visible), 'blueprint': copy.deepcopy(visible),
                                         'native': copy.deepcopy(visible)}}
        server = {p: {**copy.deepcopy(players[p]), 'weapon': copy.deepcopy(values[p])}
                  for p in peers if not (phase == 'exit_b' and p == 'B0')}
        rows.append({'phase': phase, 'packet': packet, 'acks': acks, 'server_after': server})
    reports = {}
    for peer in ('server', 'A', 'B0', 'B1'):
        reports[peer] = {'run_id': 'run', 'peer': peer, 'network_schema_version': 4, 'status': 'passed',
                         'shutdown': {'status': 'passed', 'weapon_observer': {'active_count': 0, 'ticker_active': False,
                         'errors': [], 'subscribed': 6, 'unsubscribed': 6, 'active_scopes': 0, 'scope_created': 3, 'scope_closed': 3}},
                         'phases': copy.deepcopy(rows if peer == 'server' else [row for row in rows if peer in row['acks']])}
    return reports


class WeaponNetworkContracts(unittest.TestCase):
    def setUp(self):
        self.reports = fixture()

    def test_complete_synthetic_contract(self):
        self.assertEqual(validate_reports(self.reports, 'run')['phase_count'], 19)

    def test_reject_missing_rejoined_client(self):
        del self.reports['B1']
        with self.assertRaises(RuntimeError):
            validate_reports(self.reports, 'run')

    def test_reject_observer_ticker_leak(self):
        self.reports['A']['shutdown']['weapon_observer']['ticker_active'] = True
        with self.assertRaisesRegex(RuntimeError, 'leak'):
            validate_reports(self.reports, 'run')

    def test_reject_observer_subscription_leak(self):
        self.reports['A']['shutdown']['weapon_observer']['unsubscribed'] = 5
        with self.assertRaisesRegex(RuntimeError, 'leak'):
            validate_reports(self.reports, 'run')

    def test_reject_missing_phase(self):
        self.reports['server']['phases'].pop(5)
        with self.assertRaisesRegex(RuntimeError, 'Missing'):
            validate_reports(self.reports, 'run')

    def test_reject_wrong_local_player(self):
        self.reports['server']['phases'][2]['acks']['A']['weapon_hud']['controller'] = 'B0-controller'
        with self.assertRaisesRegex(RuntimeError, 'ownership'):
            validate_reports(self.reports, 'run')

    def test_reject_stale_hud(self):
        self.reports['server']['phases'][2]['acks']['A']['weapon_hud']['python']['magazine'] = '12'
        with self.assertRaisesRegex(RuntimeError, 'HUD mismatch'):
            validate_reports(self.reports, 'run')

    def test_reject_server_ammo_divergence(self):
        self.reports['server']['phases'][2]['server_after']['A']['weapon']['magazine'] = 10
        with self.assertRaisesRegex(RuntimeError, 'Replication'):
            validate_reports(self.reports, 'run')

    def test_reject_fire_without_real_input(self):
        self.reports['server']['phases'][2]['acks']['A']['input_frames'] = 0
        with self.assertRaisesRegex(RuntimeError, 'native firing'):
            validate_reports(self.reports, 'run')

    def test_reject_rolled_camera_instead_of_upward_aim(self):
        self.reports['server']['phases'][2]['acks']['A']['aim_rotation'] = {'pitch': 0.0, 'roll': 80.0, 'yaw': 0.0}
        with self.assertRaisesRegex(RuntimeError, 'point up'):
            validate_reports(self.reports, 'run')

    def test_reject_missing_travel_cleanup(self):
        row = self.reports['server']['phases'][11]
        row['acks']['A']['weapon_observer']['unsubscribed'] = 0
        with self.assertRaisesRegex(RuntimeError, 'detach'):
            validate_reports(self.reports, 'run')

    def test_reject_missing_pawn_replacement(self):
        row = self.reports['server']['phases'][9]
        row['acks']['A']['player']['pawn_path'] = row['packet']['statuses_before']['A']['player']['pawn_path']
        with self.assertRaisesRegex(RuntimeError, 'Pawn'):
            validate_reports(self.reports, 'run')
