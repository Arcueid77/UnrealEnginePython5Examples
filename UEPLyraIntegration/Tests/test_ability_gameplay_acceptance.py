import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_ability_gameplay_acceptance as audit
from audit_migration_acceptance import attach_ability_gameplay_review


def jobs():
    modes={spec:mode for values in audit.COVERAGE.values() for mode,specs in values.items() for spec in specs}
    return [dict(batch=batch,name=name,mode=mode,directory=f'run/{batch}/{name}') for (batch,name),mode in modes.items()]


def summary(network=False):
    process=dict(pid=10,exit_code=0,arguments=['stage.uproject','/Game/Map','-game'])
    value=dict(status='passed',error=None,cpp_compile_executed=False,cook_package_executed=False,
        process=process,processes={},external_gate=dict(exit_code=0))
    if network:value['processes']={peer:dict(process,pid=10+i) for i,peer in enumerate(('server','A','B0'))}
    return value


class AbilityGameplayAcceptanceTests(unittest.TestCase):
    def test_all_six_behaviors_need_both_modes_and_each_native_family(self):
        rows=jobs();self.assertEqual(len(audit.matrix(rows)),12)
        rows=[row for row in rows if not(row['batch']==219 and row['name']=='NetShooter01')]
        with self.assertRaises(ValueError):audit.matrix(rows)

    def test_network_or_duplicate_record_cannot_substitute_for_standalone(self):
        rows=jobs();rows[0]['mode']='network'
        with self.assertRaises(ValueError):audit.matrix(rows)
        rows=jobs();rows.append(copy.deepcopy(rows[0]))
        with self.assertRaises(ValueError):audit.matrix(rows)

    def test_native_peer_identity_exit_and_actual_mode_are_required(self):
        self.assertEqual(audit.processes(summary())[1],'Standalone')
        self.assertEqual(audit.processes(summary(True))[1],'network')
        for change in ('missing-client','nonzero','duplicate-pid','missing-gate'):
            value=summary(True)
            if change=='missing-client':value['processes'].pop('B0')
            elif change=='nonzero':value['processes']['A']['exit_code']=1
            elif change=='duplicate-pid':value['processes']['A']['pid']=10
            else:value['external_gate']['exit_code']=1
            with self.subTest(change=change),self.assertRaises(ValueError):audit.processes(value)
        value=summary();value['process']['arguments'].remove('-game')
        with self.assertRaises(ValueError):audit.processes(value)

    def test_fourth_peer_is_only_allowed_for_the_integrated_rejoin_record(self):
        value=summary(True);value['processes']['B1']=dict(pid=20,exit_code=0)
        with self.assertRaises(ValueError):audit.processes(value)
        self.assertEqual(len(audit.processes(value,integrated=True)[0]),4)

    def test_report_pin_schemas_do_not_confuse_a_json_report_with_its_log(self):
        self.assertEqual(audit.report_hash({},dict(report_hashes={'server':'abc'}),'native','server.json'),'ABC')
        self.assertEqual(audit.report_hash({},dict(reports=[dict(file='jump.json',sha256='abc')]),'native','jump.json'),'ABC')
        with self.assertRaises(ValueError):audit.report_hash({},dict(report_hashes={'server':'abc'}),'native','server.log')
        with self.assertRaises(ValueError):audit.report_hash({},dict(reports=[dict(file='other.json',sha256='abc')]),'native','jump.json')

    def test_only_known_interpreter_flags_can_be_normalized_before_pure_gates(self):
        self.assertEqual(audit.arguments(['-B','-X','utf8','-m','uep_demo.sample_contract','--report','raw.json']),
                         ['-B','-m','uep_demo.sample_contract','--report','raw.json'])
        for args in (['-B','launch_game.py'],['-X','unsafe','-m','uep_demo.sample_contract']):
            with self.subTest(args=args),self.assertRaises(ValueError):audit.arguments(args)

    def test_integrated_comparison_keeps_real_ammo_definition_and_slot_outcomes(self):
        row=dict(phase='fire',server_after=dict(A=dict(weapon=dict(definition='Pistol',magazine=9,spare=48,maximum=12,slot=0,item='/old/path'),world_token='unstable')))
        report=dict(phases=[row]);other=copy.deepcopy(report);other['phases'][0]['server_after']['A']['world_token']='new-world'
        self.assertEqual(audit.integrated_outcome(report),audit.integrated_outcome(other))
        other['phases'][0]['server_after']['A']['weapon']['magazine']=8
        self.assertNotEqual(audit.integrated_outcome(report),audit.integrated_outcome(other))

    def test_only_the_exact_original_gameplay_criterion_is_promoted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'review.json';path.write_text('{}',encoding='utf-8')
            rows=[dict(version='0.11.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.14.0',text='Both full Experiences',completion_proven=False)]
            report=dict(requirements=rows,inputs=[])
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')):attach_ability_gameplay_review(report,{}, {},temporary,path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven'])
            rows[0]['version']='0.10.0'
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')),self.assertRaises(ValueError):
                attach_ability_gameplay_review(report,{}, {},temporary,path)

    def test_metadata_flag_cannot_replace_reproduced_native_evidence(self):
        for document in (dict(criterion='partial',completion_proven=True),dict(criterion=audit.REQUIREMENT,completion_proven=False)):
            with self.assertRaises(ValueError):audit.verify_documentation(document,{}, {},'.')
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=dict(native_gameplay_runs_revalidated=1))
        with patch.object(audit,'inspect',return_value=dict(native_gameplay_runs_revalidated=40)),self.assertRaises(ValueError):
            audit.verify_documentation(document,{}, {},'.')
