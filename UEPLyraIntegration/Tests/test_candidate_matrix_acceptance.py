import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_candidate_matrix_acceptance as audit
from audit_migration_acceptance import attach_candidate_matrix_review


def fixture():
    return dict(generic=dict(clean_suites=6,clean_checks=70,packaged_checks=21,current_call_cases=11,same_editor_pie_sessions=3),
        third_person=[dict(variant=name,current_editor_sdk=audit.SDK,rendered_editor_images=3,editor_exit_code=0,
            actual_packaged_game=True,game_exit_code=0,behavior_and_cleanup_passed=True) for name in ('Mixin','PythonFirst')],
        lyra=dict(normal_no_probe_observation_seconds=20,normal_stop_is_owned_and_intentional=True,current_network_phases=19,
            native_clients=2,travel_and_rejoin=True,direct_component_visual_pairs=5,actual_packaged_weapon_scenarios=42))


class CandidateMatrixTests(unittest.TestCase):
    def test_all_original_cells_pass(self):audit.matrix_gate(fixture())

    def test_missing_family_rejected(self):
        for name in fixture():
            value=fixture();del value[name]
            with self.subTest(name=name),self.assertRaises(ValueError):audit.matrix_gate(value)

    def test_generic_missing_clean_run_call_or_pie_rejected(self):
        for field in fixture()['generic']:
            value=fixture();value['generic'][field]-=1
            with self.subTest(field=field),self.assertRaises(ValueError):audit.matrix_gate(value)

    def test_both_original_third_person_variants_required(self):
        for variants in (['Mixin'],['PythonFirst'],['PythonFirst','Mixin'],['Mixin','Mixin']):
            value=fixture();value['third_person']=[dict(value['third_person'][0],variant=n) for n in variants]
            with self.subTest(variants=variants),self.assertRaises(ValueError):audit.matrix_gate(value)

    def test_third_person_requires_current_visible_editor_and_actual_game(self):
        changes=dict(current_editor_sdk='stale',rendered_editor_images=2,editor_exit_code=1,actual_packaged_game=False,
            game_exit_code=1,behavior_and_cleanup_passed=False)
        for index in (0,1):
            for field,wrong in changes.items():
                value=fixture();value['third_person'][index][field]=wrong
                with self.subTest(index=index,field=field),self.assertRaises(ValueError):audit.matrix_gate(value)

    def test_lyra_requires_no_probe_native_owners_visual_and_package_cells(self):
        for field,old in fixture()['lyra'].items():
            value=fixture();value['lyra'][field]=False if type(old) is bool else old-1
            with self.subTest(field=field),self.assertRaises(ValueError):audit.matrix_gate(value)

    def test_only_exact_original_candidate_requirement_is_attached(self):
        report=dict(requirements=[dict(version='0.9.0',text=audit.REQUIREMENT,completion_proven=False),
            dict(version='0.14.0',text='Both Experiences',completion_proven=False)],inputs=[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json';path.write_text('{}')
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):
                attach_candidate_matrix_review(report,{}, {},directory,path)
            self.assertTrue(report['requirements'][0]['completion_proven']);self.assertFalse(report['requirements'][1]['completion_proven'])
            report['requirements'][0]['version']='0.14.0'
            with patch.object(audit,'verify_documentation',return_value={}),self.assertRaises(ValueError):
                attach_candidate_matrix_review(report,{}, {},directory,path)

    def test_recorded_claim_must_equal_recomputed_source_bound_review(self):
        expected=dict(status='passed',criterion=audit.REQUIREMENT,platform='Win64',configuration='Development',scope='original0.9',new_native_processes=0)
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=expected)
        with patch.object(audit,'inspect',return_value=expected):
            audit.verify_documentation(document,{}, {},'.')
            changed=copy.deepcopy(document);changed['review']['new_native_processes']=1
            with self.assertRaises(ValueError):audit.verify_documentation(changed,{}, {},'.')


if __name__=='__main__':unittest.main()
