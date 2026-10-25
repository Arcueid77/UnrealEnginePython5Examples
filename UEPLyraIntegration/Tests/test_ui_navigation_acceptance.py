import ast,copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
import audit_ui_navigation_acceptance as audit
import audit_migration_acceptance as migration
BEFORE='import unreal_engine as ue\nCONST=1\ndef lib(name):return ue.find_class(name).get_cdo()\ndef append(actor,component):return component\ndef untouched():return 2\n'
AFTER=BEFORE.replace('return component','return component if component else None')
class UINavigationAcceptanceTests(unittest.TestCase):
    def test_settings_reader_cli_key_matches_the_actual_validator(self):
        repo=Path(__file__).resolve().parents[3]
        source=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_hud/settings_persistence_validation.py'
        keys={n.args[0].value for n in ast.walk(ast.parse(source.read_text(encoding='utf-8-sig'))) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='arg' and n.args and isinstance(n.args[0],ast.Constant)}
        expected=[k for k in keys if k.endswith('WriteReport')];self.assertEqual(len(expected),1)
        self.assertIn('-'+expected[0]+'=',(repo/'Validation/Run-UEP58UIRoutesValidation.ps1').read_text(encoding='utf-8-sig'))
    def test_imported_lib_unchanged_with_only_unrelated_append_body_change(self):
        self.assertIn('lib-unchanged',audit.verify_lib_only_change(BEFORE,AFTER))
    def test_changed_imported_lib_rejected(self):
        with self.assertRaises(ValueError):audit.verify_lib_only_change(BEFORE,AFTER.replace('get_cdo()','get_default_object()'))
    def test_changed_import_time_state_rejected(self):
        for text in (AFTER.replace('CONST=1','CONST=2'),AFTER+'ue.request_exit()\n'):
            with self.assertRaises(ValueError):audit.verify_lib_only_change(BEFORE,text)
    def test_another_changed_or_new_function_rejected(self):
        for text in (AFTER.replace('return 2','return 3'),AFTER+'def surprise():return 3\n'):
            with self.assertRaises(ValueError):audit.verify_lib_only_change(BEFORE,text)
    def test_changed_append_signature_is_not_body_only(self):
        for text in (AFTER.replace('actor,component','actor,component=ue.request_exit()'),AFTER.replace('def append','@ue.decorator\ndef append')):
            with self.assertRaises(ValueError):audit.verify_lib_only_change(BEFORE,text)
    def test_hash_index_keeps_conflicting_capture_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.py';path.write_text('x=1\n')
            rows=[dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()),dict(path=str(path),sha256='0'*64)]
            indexed=audit.index_hashes(rows)[audit.key(path)];self.assertEqual(len(indexed),2)
            with self.assertRaises(ValueError):audit.source_guard(path,indexed)
    def test_checked_flag_or_old_review_does_not_replace_recomputation(self):
        with self.assertRaises(ValueError):audit.verify_documentation(dict(criterion='subset',completion_proven=True),{}, {},'.')
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,current_native_refresh_runs=[],review=dict(status='passed'))
        with patch.object(audit,'inspect',return_value=dict(status='passed',changed_native_input=True)),self.assertRaises(ValueError):audit.verify_documentation(document,{}, {},'.')
    def test_only_exact_original_requirement_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.json';path.write_text('{}')
            rows=[dict(version='0.13.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.11.0',text='Network gameplay',completion_proven=False)]
            report=dict(requirements=rows,inputs=[],full_migration_acceptance_proven=False)
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')):migration.attach_ui_navigation_review(report,{}, {},'.',path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven']);self.assertFalse(report['full_migration_acceptance_proven'])
            rows[0]['text']='Narrow substitute'
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')),self.assertRaises(ValueError):migration.attach_ui_navigation_review(report,{}, {},'.',path)
