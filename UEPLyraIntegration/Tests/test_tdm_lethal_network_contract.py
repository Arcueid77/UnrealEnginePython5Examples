import copy
import json
from pathlib import Path
import tempfile
import unittest
from uep_lyra_weapons.tdm_lethal_network_contract import FALSE_FIELDS, PEERS, validate, validate_all


def report(peer='server'):
    row = dict(attacker_health=100., victim_health=0., attacker_kills_delta=1, victim_deaths_delta=1,
        attacker_team_score_delta=1, other_team_score_delta=0, target_score=1, ability_input_blocked=False, postgame_damage_immunity=True,
        native_postgame_phase_active=True, native_playing_phase_inactive=True,
        relay_entries=dict(kill=1, award=0), kill_notifications=[] if peer == 'server' else [dict(attacker='A', attackee='B0')],
        selected_tdm_elimination_calls=1, selected_tdm_victory_calls=1, native_match_decided_cue_actors=1,
        roster=dict(A=dict(player_id=1), B0=dict(player_id=2)), relay_receipts=[dict(verb='Lyra.Elimination.Message')])
    result = dict(status='passed', error=None, peer=peer, requested_profile='Python',
        profiles_selected_before_component_creation=True, result=row, actual_native_damage_spec_applied=peer == 'server',
        server_waited_for_client_process_exit=peer == 'server',
        observer_scopes_closed=True, profile_classes_restored=True, probe_roots_removed=True,
        target_score_restored=True, original_scores_restored=True, boot_selectors_restored=True)
    result.update(dict.fromkeys(FALSE_FIELDS, False))
    return result


class TDMLethalNetworkContractTests(unittest.TestCase):
    def test_all_three_actual_peer_reports(self):
        for peer in PEERS:
            self.assertEqual(validate(report(peer))['native_lethal_cases'], 1)

    def test_synthetic_death_or_score_without_native_health_is_rejected(self):
        for key, value in (('victim_health', 100.), ('attacker_health', 0.), ('attacker_team_score_delta', 0), ('victim_deaths_delta', 0)):
            result = report();result['result'][key] = value
            with self.assertRaises(RuntimeError):
                validate(result)

    def test_phase_and_input_block_are_actual_natural_outputs(self):
        for key in ('native_postgame_phase_active', 'native_playing_phase_inactive', 'postgame_damage_immunity'):
            result = report();result['result'][key] = False
            with self.assertRaises(RuntimeError):
                validate(result)

    def test_requested_scoring_profile_must_handle_elimination_and_victory(self):
        result = report();result['result']['selected_tdm_victory_calls'] = 0
        with self.assertRaises(RuntimeError):
            validate(result)

    def test_client_reliable_feed_and_natural_winner_cue_required(self):
        result = report('A');result['result']['kill_notifications'] = []
        with self.assertRaises(RuntimeError):
            validate(result)
        result = report('B0');result['result']['native_match_decided_cue_actors'] = 0
        with self.assertRaises(RuntimeError):
            validate(result)

    def test_cross_peer_identity_and_payload_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for peer in PEERS:
                (root/(peer+'.json')).write_text(json.dumps(report(peer)), encoding='utf-8')
            self.assertEqual(validate_all(root)['real_clients'], 2)
            bad = report('A');bad['result']['relay_receipts'] = [dict(verb='wrong')]
            (root/'A.json').write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(RuntimeError):
                validate_all(root)

    def test_direct_health_writes_and_replayed_callbacks_rejected(self):
        for key in FALSE_FIELDS:
            result = report();result[key] = True
            with self.assertRaises(RuntimeError):
                validate(result)
