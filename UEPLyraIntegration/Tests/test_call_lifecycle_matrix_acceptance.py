import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_call_lifecycle_matrix_acceptance as audit
from audit_migration_acceptance import attach_call_lifecycle_matrix_review


def matrix():
    return (Path(__file__).resolve().parents[3]/'docs/Mixin_Call_Lifecycle_Matrix.md').read_text(encoding='utf-8-sig')


def pie():
    return dict(status='passed',same_editor_process=True,error=None,sessions=[dict(cycle=i,
        placed_and_spawned=True,construction=True,native_gc_collected=True,router_restored=True,
        closed_scopes=2,begin_end_counts=[2,2]) for i in range(1,4)])


class CallLifecycleMatrixAcceptanceTests(unittest.TestCase):
    def test_every_classified_path_has_a_scoped_reproducer(self):
        rows=audit.matrix_rows(matrix())
        self.assertEqual(len(rows),33)
        self.assertEqual([sum(r['category']==c for r in rows) for c in
            ('Tested supported','Intentionally rejected','Bypass/unsupported')],[24,6,3])
        self.assertTrue(all(audit.FIXTURES[r['proof_group']] for r in rows))

    def test_missing_duplicate_unknown_or_unbound_paths_fail(self):
        text=matrix();line=next(s for s in text.splitlines() if s.startswith('| C01 |'))
        for changed in (text.replace(line,''),text.replace(line,line+'\n'+line),text.replace('| C01 |','| C99 |'),
                        text.replace('| C01 |','| Missing identity |'),
                        text.replace('proof group `callsite`','proof group `missing`',1)):
            with self.subTest(changed=changed[-30:]),self.assertRaises(ValueError):audit.matrix_rows(changed)

    def test_rejected_or_unsupported_paths_cannot_be_promoted(self):
        text=matrix()
        for identity in sorted(audit.REJECTED|audit.UNSUPPORTED):
            line=next(s for s in text.splitlines() if s.startswith('| '+identity+' |'))
            parts=line.split('|');parts[3]=' Tested supported '
            with self.subTest(identity=identity),self.assertRaises(ValueError):
                audit.matrix_rows(text.replace(line,'|'.join(parts)))

    def test_cooked_rpc_sparse_gc_and_recompile_boundaries_cannot_disappear(self):
        for boundary in ('No sparse-delegate coverage claim','No RPC invocation/network test is implied',
                         'not a universal runtime interception claim','not a synchronous-GC guarantee',
                         'Restart for generated type/signature changes'):
            with self.subTest(boundary=boundary),self.assertRaises(ValueError):audit.matrix_rows(matrix().replace(boundary,''))

    def test_bp_fallthrough_counters_cannot_be_hidden_by_passed_status(self):
        phases=[('original',[(1,0,1),(1,0,1)]),('mixed',[(1,1,2),(2,0,1)]),
            ('mixed_again',[(1,2,2),(3,0,1)]),('profiles_swapped',[(2,2,1),(3,1,2)]),('restored',[(3,2,1),(4,1,1)])]
        value=dict(status='passed',evidence=dict(caller_compiled_before_registration=True,
            zero_parameter_native_fallback=True,same_class=True,restoration_passed=True,
            phases=[dict(name=n,targets=[dict(blueprint_calls=b,python_calls=p,last_route=r) for b,p,r in ts]) for n,ts in phases]))
        audit.case_gate('callsite',value)
        value['evidence']['phases'][2]['targets'][0]['blueprint_calls']+=1
        with self.assertRaises(ValueError):audit.case_gate('callsite',value)

    def test_signature_success_does_not_replace_actual_rejections(self):
        value=dict(status='passed',same_class=True,supported=[{}]*7,rejected=[dict(profile=p) for p in
            ('BadSignature','NonConstOutputs','StaticFunction')])
        audit.case_gate('signature-shared',value)
        value['rejected'].pop()
        with self.assertRaises(ValueError):audit.case_gate('signature-shared',value)

    def test_expected_exception_needs_normal_shutdown_and_exclusive_diagnostics(self):
        text='LogPython: Error: UEP_EXPECTED_MIXIN_EXCEPTION\nUEP_MIXIN_EXCEPTION_PASSED\nGoodbye Python\nLog file closed'
        audit.log_gate('mixin-exception',text,1)
        for broken,exit_code in ((text.replace('Log file closed',''),1),
            (text+'\nLogPython: Error: unrelated failure',1),(text,3)):
            with self.subTest(exit_code=exit_code),self.assertRaises(ValueError):audit.log_gate('mixin-exception',broken,exit_code)

    def test_each_pie_session_requires_gc_scope_and_router_restoration(self):
        audit.pie_gate(pie())
        for field,value in [('cycle',1),('native_gc_collected',False),('router_restored',False),
                            ('closed_scopes',1),('begin_end_counts',[2,1])]:
            report=pie();report['sessions'][1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):audit.pie_gate(report)

    def test_attachment_accepts_only_the_exact_original_matrix_criterion(self):
        report=dict(requirements=[dict(version='0.9.0',text=audit.REQUIREMENT,completion_proven=False),
            dict(version='0.9.0',text='Another criterion',completion_proven=False)],inputs=[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json';path.write_text('{}',encoding='utf-8')
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):
                attach_call_lifecycle_matrix_review(report,{}, {},Path(directory),path)
            self.assertTrue(report['requirements'][0]['completion_proven'])
            self.assertFalse(report['requirements'][1]['completion_proven'])
            bad=copy.deepcopy(report);bad['requirements'][0]['version']='0.10.0'
            with patch.object(audit,'verify_documentation',return_value={}),self.assertRaises(ValueError):
                attach_call_lifecycle_matrix_review(bad,{}, {},Path(directory),path)

    def test_recorded_proof_cannot_be_replaced_by_an_unchecked_claim(self):
        expected=dict(status='passed',criterion=audit.REQUIREMENT,call_paths=21,lifecycle_paths=12,
            tested_supported_paths=24,intentionally_rejected_paths=6,bypass_unsupported_paths=3,current_generic_call_cases=11)
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=expected)
        with patch.object(audit,'inspect',return_value=expected):
            audit.verify_documentation(document,{}, {},Path('.'))
            tampered=copy.deepcopy(document);tampered['review']['current_generic_call_cases']=2
            with self.assertRaises(ValueError):audit.verify_documentation(tampered,{}, {},Path('.'))


if __name__=='__main__':unittest.main()
