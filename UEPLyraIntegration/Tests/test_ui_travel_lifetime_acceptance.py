import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_ui_travel_lifetime_acceptance as audit
import audit_migration_acceptance as migration
from test_ui_travel_lifetime_contract import report

class UITravelLifetimeAcceptanceTests(unittest.TestCase):
    def test_complete_pair_requires_both_profiles(self):
        audit.pair([report('BlueprintFallback'),report('Python')])
        with self.assertRaises(ValueError):audit.pair([report('Python'),report('Python')])
    def test_profile_pair_does_not_replace_raw_native_checkpoint_checks(self):
        values=[report('BlueprintFallback'),report('Python')];values[1]['cases'][2]['parent_other_callbacks']=1
        with self.assertRaises(RuntimeError):audit.pair(values)
    def test_checked_flag_without_pinned_native_runs_is_rejected(self):
        with self.assertRaises(ValueError):audit.verify_documentation(dict(criterion=audit.REQUIREMENT,completion_proven=True),'.')
    def test_substitute_requirement_or_run_is_rejected(self):
        for r in (dict(criterion='Accept every UI path',completion_proven=True),dict(criterion=audit.REQUIREMENT,completion_proven=True,native_runs=[dict(directory='other')])):
            with self.assertRaises(ValueError):audit.verify_documentation(r,'.')
    def test_attachment_only_accepts_exact_lifetime_criterion(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.json';path.write_text('{}')
            rows=[dict(version='0.13.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.13.0',text='Navigation and settings',completion_proven=False)]
            r=dict(requirements=rows,inputs=[],full_migration_acceptance_proven=False)
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')):migration.attach_ui_lifetime_review(r,'.',path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven']);self.assertFalse(r['full_migration_acceptance_proven'])
            rows[0]['text']='Subset substitute'
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')),self.assertRaises(ValueError):migration.attach_ui_lifetime_review(r,'.',path)
