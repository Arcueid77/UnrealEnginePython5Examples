import copy,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_ui_failure_cancellation_acceptance as audit
import audit_migration_acceptance as migration

class UIFailureCancellationAcceptanceTests(unittest.TestCase):
    def summary(self):return dict(status='passed',error=None,process=dict(exit_code=0),external_gate=dict(exit_code=0))
    def log(self,errors=()):
        return '\n'.join([*[f'LogCommonSession: Error: {v}' for v in errors], 'UEP_CASE_DIFFERENTIAL_PASSED','Goodbye Python','UEP_CASE_SHUTDOWN_PASSED','Log file closed'])
    def test_native_zero_exit_needs_passed_summary_and_gate(self):
        self.assertEqual(audit.process_gate(self.summary()),1)
        for field in ('status','external_gate','process'):
            value=self.summary();value[field]='failed' if field=='status' else dict(exit_code=1)
            with self.subTest(field=field),self.assertRaises(ValueError):audit.process_gate(value)
    def test_all_owned_peers_must_exit_cleanly(self):
        value=self.summary();value.pop('process');value['processes']={k:dict(exit_code=0) for k in ('host','original','python')}
        self.assertEqual(audit.process_gate(value),3);value['processes']['python']['exit_code']=-1
        with self.assertRaises(ValueError):audit.process_gate(value)
    def test_only_exact_declared_native_errors_are_allowed(self):
        expected=['bad player']*2;audit.log_gate(self.log(expected),'UEP_CASE',expected)
        for actual in (expected[:1],expected+['unknown'],['other','other']):
            with self.assertRaises(ValueError):audit.log_gate(self.log(actual),'UEP_CASE',expected)
        with self.assertRaises(ValueError):audit.log_gate(self.log()+'\nTraceback','UEP_CASE')
    def test_success_marker_does_not_replace_ordered_shutdown(self):
        for value in (self.log().replace('Goodbye Python',''),self.log().replace('Log file closed',''),self.log().replace('Goodbye Python','UEP_CASE_SHUTDOWN_PASSED').replace('UEP_CASE_SHUTDOWN_PASSED\nLog','Goodbye Python\nLog')):
            with self.assertRaises(ValueError):audit.log_gate(value,'UEP_CASE')
    def test_source_guard_allows_only_identical_text_with_newline_bom_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'policy.py';path.write_bytes(b'answer=1\r\n')
            rows=[dict(path=str(path),sha256=hashlib.sha256(b'answer=1\n').hexdigest())]
            self.assertEqual(audit.source_guard(path,rows)['equivalence'],'newline-or-bom-only')
            path.write_bytes(b'answer=2\n')
            with self.assertRaises(ValueError):audit.source_guard(path,rows)
    def test_asset_source_requires_exact_native_bytes_and_input_presence(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'widget.uasset';path.write_bytes(b'binary\r\n')
            with self.assertRaises(ValueError):audit.source_guard(path,[])
            rows=[dict(path=str(path),sha256=hashlib.sha256(b'binary\n').hexdigest())]
            with self.assertRaises(ValueError):audit.source_guard(path,rows)
    def test_stale_or_forged_review_is_recomputed_not_trusted(self):
        document=dict(schema_version=1,criterion=audit.REQUIREMENT,completion_proven=True,status='passed',verified_obligations=[],accepted_historical_native_processes=0)
        with patch.object(audit,'inspect',return_value=document):audit.verify_documentation(document,{}, {},'.')
        forged=dict(document,extra='unchecked')
        with patch.object(audit,'inspect',return_value=document),self.assertRaises(ValueError):audit.verify_documentation(forged,{}, {},'.')
        with self.assertRaises(ValueError):audit.verify_documentation(dict(document,criterion='accept entire UI'),{}, {},'.')
    def test_one_exact_original_criterion_is_accepted_without_closing_other_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.json';path.write_text('{}',encoding='utf-8')
            rows=[dict(version='0.13.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.13.0',text='All navigation',completion_proven=False)]
            report=dict(requirements=rows,inputs=[],full_migration_acceptance_proven=False)
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')):
                migration.attach_ui_failure_review(report,{}, {},'.',path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven']);self.assertFalse(report['full_migration_acceptance_proven'])
            report['requirements'][0]['text']='Narrow substitute'
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')),self.assertRaises(ValueError):migration.attach_ui_failure_review(report,{}, {},'.',path)
