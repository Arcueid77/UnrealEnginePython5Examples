"""Native identity/role evidence must fail on type, source and scope drift."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BASE / 'Tools'), str(BASE / 'Overlay/Content/Scripts')]
import audit_ability_identity_acceptance as audit
from audit_migration_acceptance import attach_ability_identity_review


def identities():
    assets = [dict(path=f'/Game/A{i}.A{i}', version='0.11.0') for i in range(37)]
    rows = [dict(asset=r['path'], original_class=r['path'] + '_C', class_identity_preserved=True,
                 ancestry=[r['path'] + '_C', '/Script/Engine.Actor'], native_router_class=r['path'] + '_C',
                 retained_forwarder=False, profiles=dict(Python=dict(python_class='example.policy.Profile')))
            for r in assets]
    dispositions = {r['path']: dict(disposition='native-python-router', original_entry_dispositions={'python-routed': 1}) for r in assets}
    return dict(assets=assets), dict(assets=rows), dispositions


def summary():
    return dict(status='passed', error=None, cpp_compile_executed=False, cook_package_executed=False,
                processes={peer: dict(pid=index + 1, exit_code=0) for index, peer in enumerate(('server', 'A', 'B0'))},
                external_gate=dict(exit_code=0, arguments=['-B', '-m', 'uep_example_contract', '--directory', 'run']))


def allocation_sources():
    old = '''import uuid
from . import inventory_ready_mixin as ready
def wait(actor,values):
    if not actor.has_authority():return
    if values["uuids"] is None:
        ids=set()
        while len(ids)<3:ids.add((uuid.uuid4().int & 0x7fffffff) or 1)
        values["uuids"]=list(ids)
    actor.call_function("DelayUntilNextTick",values["uuids"])
'''
    new = '''from . import inventory_ready_mixin as ready
from .latent_keys import allocate
def wait(actor,values):
    if not actor.has_authority():return
    if values["uuids"] is None:
        values["uuids"]=allocate(actor,"inventory-readiness",3)
    actor.call_function("DelayUntilNextTick",values["uuids"])
'''
    return old, new


class AbilityIdentityAcceptanceTests(unittest.TestCase):
    def test_every_original_native_identity_and_router_hierarchy_is_required(self):
        self.assertEqual(len(audit.class_rows(*identities())), 37)
        for change in ('class', 'identity', 'ancestor', 'router'):
            initial, coverage, dispositions = identities()
            row = coverage['assets'][0]
            if change == 'class': row['original_class'] = '/Game/Replacement.Replacement_C'
            if change == 'identity': row['class_identity_preserved'] = False
            if change == 'ancestor': row['ancestry'][0] = '/Script/Engine.Actor'
            if change == 'router': row['native_router_class'] = '/Game/Foreign.Foreign_C'
            with self.subTest(change=change), self.assertRaises(ValueError): audit.class_rows(initial, coverage, dispositions)

    def test_missing_or_duplicated_original_candidates_cannot_be_accepted(self):
        for change in ('missing', 'duplicate'):
            initial, coverage, dispositions = identities()
            if change == 'missing': initial['assets'].pop()
            else: initial['assets'][-1] = copy.deepcopy(initial['assets'][0])
            with self.assertRaises(ValueError): audit.class_rows(initial, coverage, dispositions)

    def test_retention_requires_reviewed_empty_or_parent_forwarder_entries(self):
        initial, coverage, dispositions = identities()
        dispositions[initial['assets'][0]['path']] = dict(disposition='retained-empty-native-parent-shell',
            original_entry_dispositions={'direct-parent-forwarder-review': 1, 'no-connected-execution-business': 1})
        self.assertTrue(audit.class_rows(initial, coverage, dispositions)[0]['source_reviewed_retention'])
        dispositions[initial['assets'][0]['path']]['original_entry_dispositions']['python-routed'] = 1
        with self.assertRaises(ValueError): audit.class_rows(initial, coverage, dispositions)

    def test_native_processes_and_original_independent_gate_must_all_pass(self):
        self.assertEqual(len(audit.process_rows(summary())[0]), 3)
        for change in ('exit', 'pid', 'gate', 'client', 'build'):
            row = summary()
            if change == 'exit': row['processes']['A']['exit_code'] = 1
            if change == 'pid': row['processes']['A']['pid'] = row['processes']['server']['pid']
            if change == 'gate': row['external_gate']['exit_code'] = 1
            if change == 'client': row['processes'].pop('B0')
            if change == 'build': row['cpp_compile_executed'] = True
            with self.subTest(change=change), self.assertRaises(ValueError): audit.process_rows(row)

    def test_only_recorded_pure_contract_entrypoints_may_execute(self):
        for arguments in (['-B', '-m', 'uep_probe_validation'], ['-B', 'launch_game.py'], ['-B', '-m', 'subprocess_contract']):
            with self.assertRaises(ValueError): audit.execute_gate(arguments)

    def test_raw_gate_failure_cannot_be_replaced_by_a_completion_flag(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'validate_fixture_reports.py'
            before = list(sys.argv)
            path.write_text("import json\nprint(json.dumps(dict(status='passed',full_acceptance=False)))\n")
            self.assertEqual(audit.execute_gate(['-B', str(path)])['status'], 'passed')
            path.write_text("raise RuntimeError('owner authority differs')\n")
            with self.assertRaises(RuntimeError): audit.execute_gate(['-B', str(path)])
            self.assertEqual(sys.argv, before)
            path.write_text("import json\nprint(json.dumps(dict(status='passed',full_acceptance=True)))\n")
            with self.assertRaises(ValueError): audit.execute_gate(['-B', str(path)])

    def test_native_type_and_execution_policy_writes_are_rejected(self):
        for source in ('actor.NetExecutionPolicy=0', 'actor.set_property("bReplicates",False)',
                       'actor.call_function("SetReplicateMovement",False)', 'actor.SetReplicates(False)',
                       'ue.new_blueprint("Replacement")', 'ue.register_class(Profile)'):
            with self.subTest(source=source), self.assertRaises(ValueError): audit.native_boundary_writes('policy', source)
        review = audit.native_boundary_writes('policy', 'actor.set_property("Health",75)\nactor.set_property(name,value)')
        self.assertEqual(review['dynamic_property_write_lines'], [2])
        self.assertFalse(review['formal_dynamic_assignment_analysis'])

    def test_private_key_extraction_preserves_every_native_call_and_role_branch(self):
        before, after = allocation_sources()
        self.assertIn('only-private-three-key', audit.latent_key_extraction(before, after))
        for changed in (after.replace('if not actor.has_authority():return', 'if False:return'),
                        after.replace('"inventory-readiness",3', '"inventory-readiness",2'),
                        after.replace('DelayUntilNextTick', 'Delay'), after + 'actor.set_property("Role",3)\n'):
            with self.subTest(changed=changed), self.assertRaises(ValueError): audit.latent_key_extraction(before, changed)

    def test_post_exit_contract_change_never_becomes_runtime_source_equivalence(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'contract.py'
            path.write_text('def validate(report):return True\n')
            rows = [dict(path=str(path), sha256='0' * 64)]
            result = audit.report_dependency_guard('uep_demo.sample_contract', path, rows)
            self.assertTrue(result['current_post_exit_contract_reexecuted'])
            self.assertFalse(result['production_runtime_source_equivalence_claimed'])
            with self.assertRaises(ValueError): audit.report_dependency_guard('uep_demo.policy_mixin', path, rows)
            with self.assertRaises(ValueError): audit.report_dependency_guard('uep_demo.sample_contract', path, [])

    def test_exact_original_identity_criterion_is_the_only_promoted_requirement(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'review.json'
            path.write_text('{}')
            rows = [dict(version='0.11.0', text=audit.REQUIREMENT, completion_proven=False),
                    dict(version='0.11.0', text='All fire/death/respawn gameplay', completion_proven=False)]
            report = dict(requirements=rows, inputs=[])
            with patch.object(audit, 'verify_documentation', return_value=dict(status='passed')):
                attach_ability_identity_review(report, {}, {}, temporary, path)
            self.assertTrue(rows[0]['completion_proven'])
            self.assertFalse(rows[0]['full_migration_acceptance_proven'])
            self.assertFalse(rows[1]['completion_proven'])
            rows[0]['version'] = '0.10.0'
            with patch.object(audit, 'verify_documentation', return_value=dict(status='passed')), self.assertRaises(ValueError):
                attach_ability_identity_review(report, {}, {}, temporary, path)

    def test_metadata_alone_does_not_prove_native_identity_or_authority(self):
        for document in (dict(criterion='partial', completion_proven=True), dict(criterion=audit.REQUIREMENT, completion_proven=False)):
            with self.assertRaises(ValueError): audit.verify_documentation(document, {}, {}, '.')
        document = dict(criterion=audit.REQUIREMENT, completion_proven=True, review=dict(native_execution_runs_revalidated=1))
        with patch.object(audit, 'inspect', return_value=dict(native_execution_runs_revalidated=55)), self.assertRaises(ValueError):
            audit.verify_documentation(document, {}, {}, '.')
