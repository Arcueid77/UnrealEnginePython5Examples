"""Synthetic adversarial evidence tests; these do not replace real UE runs."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Overlay' / 'Content' / 'Scripts'))
from uep_lyra_network_protocol import (  # noqa: E402
    PHASES, participants, validate_ack, validate_command, validate_hud,
    validate_phase_names, validate_run,
)


def fixture():
    player = dict(world_token='client-world', player_token='local-token', player_id=256,
                  player_name='player-A', net_mode='Client', pawn_local_role='AutonomousProxy',
                  local_player_controller_count=1, controller_path='local-controller',
                  pawn_path='local-pawn', health_component_path='local-health', health=90)
    hud = dict(errors=[], active_widget_count=1, live_widget_reference_count=1,
               active_widgets=['widget'], controller_bind_count=1, controller_unbind_count=0,
               health_bind_count=1, health_unbind_count=0,
               instances={'widget': dict(last_controller='local-controller', last_pawn='local-pawn',
                                         last_health_component='local-health', last_health=90)},
               health_events=[dict(event='health_changed', sequence=2, health=90,
                                   pawn='local-pawn', health_component='local-health')])
    packet = dict(run_id='run', phase_index=3, phase='damage_a', server_world_token='server-world',
                  participants=['A', 'B0'], roster={'A': dict(player, player_token='server-token')},
                  client_worlds={'A': 'client-world'}, expected_health={'A': 90},
                  command_ids=['command-A'], changed_health=['A'], event_floor={'A': 1})
    ack = dict(run_id='run', peer='A', phase_index=3, phase='damage_a', server_world_token='server-world',
               server_player_token='server-token', player=player, hud=hud,
               command_ids=['command-A'], observed_at_ns=10)
    return packet, ack


class NetworkProtocolTests(unittest.TestCase):
    def test_correct_owned_fresh_ack_passes(self):
        packet, ack = fixture()
        validate_ack(packet, ack, 'A')

    def test_all_phase_identity_fields_are_checked(self):
        for key in ('run_id', 'phase_index', 'phase', 'server_world_token',
                    'server_player_token', 'peer', 'command_ids'):
            with self.subTest(key=key):
                packet, ack = fixture()
                ack[key] = 'stale'
                with self.assertRaises(RuntimeError):
                    validate_ack(packet, ack, 'A')

    def test_wrong_client_world_player_role_or_health_fails(self):
        for key in ('world_token', 'player_id', 'player_name', 'net_mode',
                    'pawn_local_role', 'local_player_controller_count', 'health'):
            with self.subTest(key=key):
                packet, ack = fixture()
                ack['player'][key] = 'wrong'
                with self.assertRaises(RuntimeError):
                    validate_ack(packet, ack, 'A')

    def test_hud_cannot_bind_another_players_objects(self):
        for key in ('last_controller', 'last_pawn', 'last_health_component', 'last_health'):
            with self.subTest(key=key):
                packet, ack = fixture()
                ack['hud']['instances']['widget'][key] = 'player-B'
                with self.assertRaises(RuntimeError):
                    validate_ack(packet, ack, 'A')

    def test_polled_health_without_fresh_delegate_event_fails(self):
        packet, ack = fixture()
        ack['hud']['health_events'] = []
        with self.assertRaisesRegex(RuntimeError, 'fresh replicated'):
            validate_ack(packet, ack, 'A')

    def test_stale_or_other_player_event_cannot_satisfy_ack(self):
        for key, value in (('sequence', 1), ('pawn', 'other'), ('health_component', 'other'),
                           ('health', 80), ('event', 'initialized')):
            with self.subTest(key=key):
                packet, ack = fixture()
                ack['hud']['health_events'][0][key] = value
                with self.assertRaisesRegex(RuntimeError, 'fresh replicated'):
                    validate_ack(packet, ack, 'A')

    def test_duplicate_presenter_or_callback_is_rejected(self):
        for key in ('active_widget_count', 'live_widget_reference_count',
                    'controller_bind_count', 'health_bind_count'):
            with self.subTest(key=key):
                packet, ack = fixture()
                ack['hud'][key] = 2
                with self.assertRaises(RuntimeError):
                    validate_ack(packet, ack, 'A')

    def test_server_cannot_create_a_presenter(self):
        _, ack = fixture()
        with self.assertRaises(RuntimeError):
            validate_hud(ack['hud'])

    def test_nonfinite_or_boolean_health_is_rejected(self):
        for value in (float('nan'), float('inf'), True):
            packet, ack = fixture()
            ack['player']['health'] = value
            with self.assertRaises(RuntimeError):
                validate_ack(packet, ack, 'A')

    def test_rejection_must_not_be_accepted_or_applied(self):
        result = dict(status='RejectedNotAuthority', applied=False, accepted=False)
        validate_command(result, 'RejectedNotAuthority', False)
        for key in ('applied', 'accepted'):
            bad = dict(result, **{key: True})
            with self.assertRaises(RuntimeError):
                validate_command(bad, 'RejectedNotAuthority', False)

    def test_all_four_processes_have_exact_phase_contracts(self):
        for peer in ('server', 'A', 'B0', 'B1'):
            records = [{'phase': name} for name in PHASES if peer == 'server' or peer in participants(name)]
            validate_phase_names(records, peer)
            with self.assertRaises(RuntimeError):
                validate_phase_names(records[:-1], peer)
            with self.assertRaises(RuntimeError):
                validate_phase_names(records[::-1], peer)

    def test_one_client_or_missing_rejoin_report_cannot_pass(self):
        reports = dict.fromkeys(('server', 'A', 'B0', 'B1'), {})
        for peer in reports:
            bad = copy.deepcopy(reports)
            del bad[peer]
            with self.assertRaisesRegex(RuntimeError, 'Missing network process'):
                validate_run(bad, 'run')

    def test_pending_shutdown_cannot_pass(self):
        report = dict(run_id='run', peer='server', status='awaiting_shutdown', schema_version=5,
                      network_schema_version=1)
        reports = dict(server=report, A={}, B0={}, B1={})
        with self.assertRaisesRegex(RuntimeError, 'final network report'):
            validate_run(reports, 'run')


if __name__ == '__main__':
    unittest.main()
