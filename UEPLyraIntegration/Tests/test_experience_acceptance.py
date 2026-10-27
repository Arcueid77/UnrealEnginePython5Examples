import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_experience_acceptance as audit
from audit_migration_acceptance import attach_experience_review,complete_original_scope,git_text_snapshot_matches


def cells():
    return [dict(scenario=s,profiles=list(audit.PROFILES),pair_semantics_passed=True,current_editor_sdk=audit.SDK,
        native_processes=6 if s=='ExplorerActionsNetwork' else 2,all_native_exits_zero=True,distinct_clients=2,local_players=2)
        for s in audit.SCENARIOS]


class ExperienceAcceptanceTests(unittest.TestCase):
    def test_all_six_original_comparisons_pass(self):audit.integration_gate(cells())
    def test_missing_experience_profile_current_sdk_or_process_rejected(self):
        with self.assertRaises(ValueError):audit.integration_gate(cells()[:-1])
        for field,wrong in [('profiles',['Python']),('current_editor_sdk','stale'),('native_processes',1),
                             ('pair_semantics_passed',False),('all_native_exits_zero',False)]:
            value=cells();value[0][field]=wrong
            with self.subTest(field=field),self.assertRaises(ValueError):audit.integration_gate(value)
    def test_two_distinct_network_clients_and_two_native_local_players_required(self):
        for scenario,field in [('ExplorerActionsNetwork','distinct_clients'),('ArenaLocalInput','local_players'),('ArenaOpponentBomb','local_players')]:
            value=cells();next(r for r in value if r['scenario']==scenario)[field]=1
            with self.subTest(scenario=scenario),self.assertRaises(ValueError):audit.integration_gate(value)
    def test_exact_retired_test_archive_cannot_excuse_production_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory);base=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_abilities';base.mkdir(parents=True)
            archive=repo/'.build/old.py';archive.parent.mkdir();archive.write_bytes(b'old\n')
            digest=hashlib.sha256(archive.read_bytes()).hexdigest().upper()
            for name,allowed in [('explorer_actions_network_validation.py',True),('explorer_actions_mixin.py',False)]:
                path=base/name;path.write_bytes(b'new\n');row=dict(path=str(path),sha256=digest);mapping={(str(path.resolve()),digest):str(archive)}
                if allowed:self.assertEqual(audit.frozen_input(row,repo,mapping)['recorded_sha256'],digest)
                else:
                    with self.assertRaises(ValueError):audit.frozen_input(row,repo,mapping)
    def test_root_binding_preserves_quoted_paths_and_rejects_extra_control_code(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory);quoted="'"+str((repo/'Validation').resolve())+"'"
            original='param()\n. "$PSScriptRoot/helper.ps1"\n'
            derived='param()\n$uepOriginalValidationRoot='+quoted+'\n\n. "$uepOriginalValidationRoot/helper.ps1"\n'
            provenance=dict(shared_python_live_reader=False,sdk_path_replacements=0)
            audit.control_source_guard(original,derived,repo,provenance)
            with self.assertRaises(ValueError):audit.control_source_guard(original,derived+'Write-Host extra\n',repo,provenance)
    def test_only_original_experience_requirement_is_attached(self):
        report=dict(requirements=[dict(version='0.14.0',text=audit.REQUIREMENT,completion_proven=False),
            dict(version='0.9.0',text='RC',completion_proven=False)],inputs=[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json';path.write_text('{}')
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):attach_experience_review(report,{}, {},directory,path)
            self.assertTrue(report['requirements'][0]['completion_proven']);self.assertFalse(report['requirements'][1]['completion_proven'])
    def test_completion_requires_all_original_criteria_and_candidate_dispositions(self):
        report=dict(requirements=[dict(completion_proven=True) for _ in range(22)],candidate_rows=[{} for _ in range(246)],candidate_rows_not_accepted=0)
        for field,wrong in [('requirements',report['requirements'][:-1]),('candidate_rows',report['candidate_rows'][:-1]),('candidate_rows_not_accepted',1)]:
            value=copy.deepcopy(report);value[field]=wrong
            with self.subTest(field=field),self.assertRaises(ValueError):complete_original_scope(value)
        value=copy.deepcopy(report);value['requirements'][0]['completion_proven']=False
        with self.assertRaises(ValueError):complete_original_scope(value)
        complete_original_scope(report);self.assertTrue(report['full_migration_acceptance_proven']);self.assertFalse(report['release_publication'])
    def test_git_snapshot_accepts_checkout_newlines_but_rejects_content_changes(self):
        blob=b'{"version":1}\n'
        for value in (blob,blob.replace(b'\n',b'\r\n'),b'\xef\xbb\xbf'+blob):
            self.assertTrue(git_text_snapshot_matches(blob,hashlib.sha256(value).hexdigest()))
        self.assertFalse(git_text_snapshot_matches(blob,hashlib.sha256(b'{"version":2}\n').hexdigest()))


if __name__=='__main__':unittest.main()
