import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_rc_api_acceptance as audit
from audit_migration_acceptance import attach_rc_api_review


SOURCE='''static PyMethodDef unreal_engine_methods[] = {
#if WITH_EDITOR
 { "helper", (PyCFunction)helper, METH_VARARGS | METH_KEYWORDS, "doc" },
#endif
 { NULL, NULL, 0, NULL }
};
static PyMethodDef ue_PyUObject_methods[] = {
 { "object_method", object_method, METH_VARARGS, "" },
 { NULL, NULL, 0, NULL }
};
'''


def fixture():
    return dict(candidate_matrix_accepted=True,other_original_009_criteria_accepted=6,
        supported_capabilities=list(audit.CAPABILITIES),registration_counts=[213,462],known_release_blocking_api_defects=[],
        sdk_bootstrap_fix_verified=True,isolated_lyra_guard_required=True,official_lyra_issue_retained=True,
        original_netshooter_native_discrepancy_retained=True)


class RCApiTests(unittest.TestCase):
    def test_conditional_entries_and_whitespace_preserve_registration(self):
        result=audit.compare_tables(SOURCE,SOURCE.replace('METH_VARARGS |','METH_VARARGS|'))
        self.assertEqual([result[n]['current'] for n in audit.TABLES],[1,1])

    def test_public_registration_removal_addition_function_and_flags_reject(self):
        changes=[SOURCE.replace(' { "helper", (PyCFunction)helper, METH_VARARGS | METH_KEYWORDS, "doc" },\n',''),
            SOURCE.replace('"helper"','"new_helper"'),SOURCE.replace('(PyCFunction)helper','(PyCFunction)other'),
            SOURCE.replace('METH_VARARGS | METH_KEYWORDS','METH_NOARGS')]
        for changed in changes:
            with self.subTest(changed=changed),self.assertRaises(ValueError):audit.compare_tables(SOURCE,changed)

    def test_duplicate_registration_cannot_hide_coverage(self):
        changed=SOURCE.replace('#endif',' { "helper", helper, METH_VARARGS, "" },\n#endif')
        with self.assertRaises(ValueError):audit.method_tables(changed)

    def test_complete_scoped_freeze_passes(self):audit.freeze_gate(fixture())

    def test_incomplete_candidate_or_known_api_defect_blocks_freeze(self):
        for field,wrong in [('candidate_matrix_accepted',False),('other_original_009_criteria_accepted',5),
                             ('known_release_blocking_api_defects',['unresolved correctness bug']),
                             ('registration_counts',[213,461]),('supported_capabilities',[])]:
            value=fixture();value[field]=wrong
            with self.subTest(field=field),self.assertRaises(ValueError):audit.freeze_gate(value)

    def test_external_findings_and_current_bootstrap_fix_remain_explicit(self):
        for field in ('sdk_bootstrap_fix_verified','isolated_lyra_guard_required','official_lyra_issue_retained',
                      'original_netshooter_native_discrepancy_retained'):
            value=fixture();value[field]=False
            with self.subTest(field=field),self.assertRaises(ValueError):audit.freeze_gate(value)

    def test_attachment_accepts_only_original_rc_condition(self):
        report=dict(requirements=[dict(version='0.9.0',text=audit.REQUIREMENT,completion_proven=False),
            dict(version='0.14.0',text='Both Experiences',completion_proven=False)],inputs=[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json';path.write_text('{}')
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):attach_rc_api_review(report,{}, {},directory,path)
            self.assertTrue(report['requirements'][0]['completion_proven']);self.assertFalse(report['requirements'][1]['completion_proven'])
            report['requirements'][0]['version']='0.14.0'
            with patch.object(audit,'verify_documentation',return_value={}),self.assertRaises(ValueError):attach_rc_api_review(report,{}, {},directory,path)

    def test_review_must_equal_recomputed_evidence(self):
        expected=dict(status='passed',criterion=audit.REQUIREMENT,scope='supported API',new_native_processes=0,rc_tag_or_release_created=False)
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=expected)
        with patch.object(audit,'inspect',return_value=expected):
            audit.verify_documentation(document,{}, {},'.')
            changed=copy.deepcopy(document);changed['review']['rc_tag_or_release_created']=True
            with self.assertRaises(ValueError):audit.verify_documentation(changed,{}, {},'.')


if __name__=='__main__':unittest.main()
