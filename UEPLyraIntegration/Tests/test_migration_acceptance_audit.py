import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('migration_acceptance_audit', Path(__file__).resolve().parents[1]/'Tools/audit_migration_acceptance.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixture():
    rows = [dict(path=f'/{version}/Candidate{index}.Candidate{index}', version=version, status='bounded', scope_review=None)
            for version, count in audit.VERSIONS.items() for index in range(count)]
    data = dict(runtime_candidates=246, configuration_only=182, retained=63, scope_review_candidates=11,
                migration_complete=False, assets=rows)
    roadmap = '\n'.join(f'## {version} scope\n- [x] Existing historical claim.\n- [ ] Current acceptance criterion.' for version in audit.VERSIONS)
    return data, copy.deepcopy(data), roadmap


class MigrationAcceptanceAuditTests(unittest.TestCase):
    def run_audit(self, data, original, roadmap):
        with tempfile.TemporaryDirectory() as directory:
            return audit.inspect(data, original, roadmap, acceptance_directory=Path(directory))

    def test_zero_unaccepted_and_checked_boxes_never_prove_completion(self):
        result = self.run_audit(*fixture())
        self.assertEqual(result['candidate_rows_not_accepted'], 0)
        self.assertFalse(result['full_migration_acceptance_proven'])
        self.assertTrue(any(row['original_checked'] for row in result['requirements']))
        self.assertTrue(all(not row['completion_proven'] for row in result['requirements']))

    def test_changed_paths_or_original_order_are_rejected(self):
        data, original, roadmap = fixture()
        data['assets'][0], data['assets'][1] = data['assets'][1], data['assets'][0]
        with self.assertRaises(ValueError):
            self.run_audit(data, original, roadmap)

    def test_static_scope_or_version_reassignment_is_rejected(self):
        for changed in ('counts', 'version'):
            data, original, roadmap = fixture()
            if changed == 'counts':
                data['retained'] = 62
            else:
                data['assets'][0]['version'] = '0.14.0'
            with self.assertRaises(ValueError):
                self.run_audit(data, original, roadmap)

    def test_missing_original_version_checklist_is_rejected(self):
        data, original, roadmap = fixture()
        roadmap = roadmap.replace('## 0.14.0 scope', '## Removed scope')
        with self.assertRaises(ValueError):
            self.run_audit(data, original, roadmap)

    def test_prohibited_behavior_false_is_not_a_missing_capability(self):
        self.assertEqual(audit.unverified(dict(callbacks_replayed=False, health_properties_written=False,
            cpp_compile_executed=False, assets_modified=False)), [])
        self.assertEqual(audit.unverified(dict(natural_animation_dispatch_tested=False))[0]['state'], 'explicitly_unverified')

    def test_missing_declared_ledger_stays_an_unverified_reference(self):
        data, original, roadmap = fixture()
        data['assets'][0]['evidence_ledger'] = 'missing.json'
        result = self.run_audit(data, original, roadmap)
        self.assertFalse(result['candidate_rows'][0]['declared_ledger_exists'])
        self.assertFalse(result['candidate_rows'][0]['evidence_semantics_verified_by_this_audit'])

    def test_forged_manifest_completion_is_rejected(self):
        data, original, roadmap = fixture()
        data['migration_complete'] = True
        with self.assertRaises(ValueError):
            self.run_audit(data, original, roadmap)

    def test_recorded_animation_updates_next_work_without_proving_migration(self):
        data, original, roadmap = fixture()
        data['footstep_pilot'] = dict(natural_animation_dispatch_tested=True)
        result = self.run_audit(data, original, roadmap)
        self.assertIn('already recorded', result['next_evidence_task'])
        self.assertFalse(result['full_migration_acceptance_proven'])

    def test_recorded_actual_locomotion_does_not_remain_the_next_task(self):
        data, original, roadmap = fixture()
        data['footstep_pilot'] = dict(natural_animation_dispatch_tested=True, normal_locomotion_input_state_machine_tested=True)
        result = self.run_audit(data, original, roadmap)
        self.assertIn('actual-player Enhanced Input/AnimBP locomotion are already recorded', result['next_evidence_task'])
        self.assertFalse(result['full_migration_acceptance_proven'])

    def test_requirement_continuations_and_source_lines_are_retained(self):
        rows = audit.requirements('## 0.12.0 Effects\n- [ ] Multi-client phase state\n  and native cleanup agree.\n\n## 1.0.0 Release\n- [ ] Publish tags.\n')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['text'], 'Multi-client phase state and native cleanup agree.')
        self.assertEqual(rows[0]['roadmap_line'], 2)
