import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'Tools'),str(BASE/'Overlay/Content/Scripts')]
import audit_match_network_acceptance as audit
from audit_migration_acceptance import attach_match_network_review
from test_tdm_lethal_network_contract import report

class MatchNetworkAcceptanceTests(unittest.TestCase):
    def pair(self):
        original={p:report(p) for p in ('server','A','B0')};python=copy.deepcopy(original)
        for r in original.values():r.update(run_id='original',requested_profile='BlueprintFallback')
        for r in python.values():r['run_id']='python'
        return original,python
    def test_original_python_tdm_checkpoints_must_agree(self):
        original,python=self.pair();self.assertEqual(audit.compare_tdm(original,python)['native_lethal_cases'],2)
        python['B0']['result']['postgame_damage_immunity']=False
        with self.assertRaises(ValueError):audit.compare_tdm(original,python)
    def test_three_peers_and_separate_profiles_are_required(self):
        original,python=self.pair()
        for changed in ({k:v for k,v in original.items() if k!='B0'},python):
            with self.assertRaises(ValueError):audit.compare_tdm(changed,python)
        python['server']['run_id']='original'
        with self.assertRaises(ValueError):audit.compare_tdm(original,python)
    def test_legacy_completion_marker_requires_clean_ordered_exit(self):
        log='Goodbye Python\nUEP_NOTIFICATION_RELAYS_NETWORK_PASSED\nLog file closed'
        audit.relay_log_gate(log)
        client=log.replace('NETWORK_PASSED','SHUTDOWN_PASSED');audit.relay_log_gate(client,'A')
        with self.assertRaises(ValueError):audit.relay_log_gate(log,'A')
        for bad in (log.replace('Goodbye Python',''),log.replace('UEP_NOTIFICATION_RELAYS_NETWORK_PASSED','Traceback'),log+'\nLogPython: Error: Bad','\n'.join(reversed(log.splitlines()))):
            with self.assertRaises(ValueError):audit.relay_log_gate(bad)
    def test_plan_retains_tdm_cp_and_both_notification_routes(self):
        self.assertEqual(len(audit.SPECS),5)
        self.assertEqual([s[0] for s in audit.SPECS],[129,205,205,252,252])
        self.assertTrue(all(s[-1] for s in audit.SPECS));self.assertEqual(len(audit.RELAY),2)
    def test_attachment_only_accepts_exact_original_network_criterion(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'review.json';path.write_text('{}');rows=[dict(version='0.12.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.12.0',text='Same-input effects checkpoints',completion_proven=False)];result=dict(requirements=rows,inputs=[])
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')):attach_match_network_review(result,folder,path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven']);self.assertFalse(rows[0]['full_migration_acceptance_proven'])
            rows[0]['text']='partial substitute'
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')),self.assertRaises(ValueError):attach_match_network_review(result,folder,path)
    def test_checked_metadata_is_not_native_proof(self):
        for value in (dict(criterion='partial',completion_proven=True),dict(criterion=audit.REQUIREMENT,completion_proven=False)):
            with self.assertRaises(ValueError):audit.verify_documentation(value,'.')
