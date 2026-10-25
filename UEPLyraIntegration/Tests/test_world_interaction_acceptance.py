"""Reject fabricated ownership, process completion and widened acceptance."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BASE / 'Tools'), str(BASE / 'Overlay/Content/Scripts')]
import audit_world_interaction_acceptance as audit
from audit_migration_acceptance import attach_world_interaction_review


def native_processes(folder):
    peers = []
    for index, peer in enumerate(('server', 'A', 'B0')):
        args = ['Lyra.uproject', '-UEPLyraNetPeer=' + peer, '-abslog=' + str(folder / (peer + '.log'))]
        if peer == 'server':
            args.append('-server')
        peers.append(dict(name=peer, pid=index + 1, exit_code=0, arguments=args))
    return dict(status='passed', error=None, cpp_compile_executed=False, cook_package_executed=False,
                processes=peers, validation=dict(exit_code=0))


def native_owners():
    roster = {peer: dict(player_id=index, controller_path='controller-' + peer, pawn_path='pawn-' + peer,
                         net_mode='DedicatedServer', server_authority=True)
              for index, peer in enumerate(('A', 'B0'))}
    return dict(server=dict(hud=dict(construct_count=0), cases=[dict(roster=roster, client_worlds=dict(A='world-A', B0='world-B0'))]),
                A={}, B0={})


class WorldInteractionAcceptanceTests(unittest.TestCase):
    def test_distinct_native_authority_and_two_clients_must_all_exit_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.assertEqual(set(audit.processes(native_processes(folder), folder)), {'server', 'A', 'B0'})
            for change in ('exit', 'pid', 'name', 'authority', 'log'):
                row = native_processes(folder)
                if change == 'exit': row['processes'][1]['exit_code'] = 1
                if change == 'pid': row['processes'][1]['pid'] = row['processes'][0]['pid']
                if change == 'name': row['processes'][1]['name'] = 'server'
                if change == 'authority': row['processes'][1]['arguments'].append('-server')
                if change == 'log': row['processes'][1]['arguments'][-1] = '-abslog=' + str(folder / 'server.log')
                with self.subTest(change=change), self.assertRaises(ValueError): audit.processes(row, folder)

    def test_failed_independent_gate_or_build_claim_cannot_be_hidden(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for field in ('status', 'validation', 'cpp_compile_executed', 'cook_package_executed'):
                row = native_processes(folder)
                if field == 'status': row[field] = 'failed'
                elif field == 'validation': row[field]['exit_code'] = 1
                else: row[field] = True
                with self.subTest(field=field), self.assertRaises(ValueError): audit.processes(row, folder)

    def test_report_peer_and_process_peer_must_agree(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            row = native_processes(folder)
            row['processes'][1]['arguments'][1] = '-UEPLyraNetPeer=B0'
            with self.assertRaises(ValueError): audit.processes(row, folder)

    def test_native_shutdown_requires_completion_before_python_exit_and_close(self):
        log = 'UEP_PICKUP_PASSED\nGoodbye Python\nUEP_LYRA_HUD_SHUTDOWN_PASSED\nLog file closed'
        audit.network_log(log, 'UEP_PICKUP')
        for changed in (log.replace('Goodbye Python', ''), log.replace('UEP_PICKUP_PASSED', ''),
                        log.replace('Goodbye Python', 'Log file closed'),
                        'Goodbye Python\n' + log.replace('Goodbye Python', '')):
            with self.assertRaises(ValueError): audit.network_log(changed, 'UEP_PICKUP')

    def test_clean_exit_markers_do_not_override_native_diagnostics(self):
        log = 'UEP_PICKUP_PASSED\nGoodbye Python\nUEP_LYRA_HUD_SHUTDOWN_PASSED\nLog file closed'
        for failure in ('Traceback', 'Ensure condition failed', 'Fatal error', 'LogPython: Error: broken'):
            with self.subTest(failure=failure), self.assertRaises(ValueError): audit.network_log(log + '\n' + failure, 'UEP_PICKUP')

    def test_independent_native_owner_controller_pawn_and_world_are_required(self):
        audit.owner_identity(native_owners())
        for field in ('player_id', 'controller_path', 'pawn_path'):
            rows = native_owners()
            roster = rows['server']['cases'][0]['roster']
            roster['B0'][field] = roster['A'][field]
            with self.subTest(field=field), self.assertRaises(ValueError): audit.owner_identity(rows)
        rows = native_owners()
        rows['server']['cases'][0]['client_worlds']['B0'] = 'world-A'
        with self.assertRaises(ValueError): audit.owner_identity(rows)

    def test_claim_roster_requires_real_authority_and_server_zero_ui(self):
        for change in ('authority', 'mode', 'ui'):
            rows = native_owners()
            if change == 'authority': rows['server']['cases'][0]['roster']['A']['server_authority'] = False
            if change == 'mode': rows['server']['cases'][0]['roster']['A']['net_mode'] = 'Client'
            if change == 'ui': rows['server']['hud']['construct_count'] = 1
            with self.subTest(change=change), self.assertRaises(ValueError): audit.owner_identity(rows)

    def test_gate_reexecutes_raw_report_logic_and_restores_arguments_on_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            path = folder / 'gate.py'
            path.write_text("import json\nprint(json.dumps(dict(status='passed',clients=2,full_acceptance=False)))\n")
            before = list(sys.argv)
            self.assertEqual(audit.execute_network_gate(path, folder)['status'], 'passed')
            self.assertEqual(sys.argv, before)
            path.write_text("raise RuntimeError('raw owner mismatch')\n")
            with self.assertRaises(RuntimeError): audit.execute_network_gate(path, folder)
            self.assertEqual(sys.argv, before)

    def test_current_gate_cannot_promote_legacy_rows_to_full_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            path = folder / 'gate.py'
            path.write_text("import json\nprint(json.dumps(dict(status='passed',clients=2,full_acceptance=True)))\n")
            with self.assertRaises(ValueError): audit.execute_network_gate(path, folder)

    def test_attachment_only_accepts_the_exact_original_interaction_requirement(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'review.json'
            path.write_text('{}')
            rows = [dict(version='0.10.0', text=audit.REQUIREMENT, completion_proven=False),
                    dict(version='0.10.0', text='Each small batch passes original-BP/Python comparison without BP fallthrough.', completion_proven=False)]
            report = dict(requirements=rows, inputs=[])
            with patch.object(audit, 'verify_documentation', return_value=dict(status='passed')):
                attach_world_interaction_review(report, {}, {}, temporary, path)
            self.assertTrue(rows[0]['completion_proven'])
            self.assertFalse(rows[0]['full_migration_acceptance_proven'])
            self.assertFalse(rows[1]['completion_proven'])
            for field, value in (('version', '0.11.0'), ('text', 'partial substitute')):
                changed = copy.deepcopy(rows)
                changed[0][field] = value
                with patch.object(audit, 'verify_documentation', return_value=dict(status='passed')), self.assertRaises(ValueError):
                    attach_world_interaction_review(dict(requirements=changed, inputs=[]), {}, {}, temporary, path)

    def test_checked_metadata_cannot_replace_the_native_source_review(self):
        for document in (dict(criterion='partial', completion_proven=True), dict(criterion=audit.REQUIREMENT, completion_proven=False)):
            with self.assertRaises(ValueError): audit.verify_documentation(document, {}, {}, '.')
        document = dict(criterion=audit.REQUIREMENT, completion_proven=True, review=dict(status='passed', network_case_rows=1))
        with patch.object(audit, 'inspect', return_value=dict(status='passed', network_case_rows=108)), self.assertRaises(ValueError):
            audit.verify_documentation(document, {}, {}, '.')
