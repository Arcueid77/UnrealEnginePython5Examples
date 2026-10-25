import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_ability_lifetime_acceptance as audit
from audit_migration_acceptance import attach_ability_lifetime_review


def source_fixtures():
    return {module:'APIS='+repr(apis) for module,_,apis in audit.FAMILIES}


class AbilityLifetimeAcceptanceTests(unittest.TestCase):
    def test_all_factory_sites_need_their_own_native_family(self):
        sources=source_fixtures(); rows=audit.source_inventory(sources)
        self.assertEqual(len(rows),26)
        self.assertEqual(len({v for r in rows for v in r['apis'] if v.startswith('AbilityTask_')}),7)
        sources['unreviewed_policy']='factory="AbilityTask_WaitTargetData"'
        with self.assertRaises(ValueError):audit.source_inventory(sources)

    def test_missing_task_or_new_async_factory_cannot_pass_the_old_inventory(self):
        sources=source_fixtures(); sources.pop(audit.A+'quickslot_mixin')
        with self.assertRaises(ValueError):audit.source_inventory(sources)
        sources=source_fixtures();sources[audit.A+'quickslot_mixin']+='\nproxy="AsyncAction_NewUnreviewedListener"'
        with self.assertRaises(ValueError):audit.source_inventory(sources)

    def test_added_latent_or_timer_api_requires_its_own_review(self):
        for api in ('RetriggerableDelay','K2_SetTimerDelegate'):
            sources=source_fixtures();sources[audit.A+'death_mixin']+='\nnew_boundary='+repr(api)
            with self.subTest(api=api),self.assertRaises(ValueError):audit.source_inventory(sources)

    def test_quickslot_cannot_accidentally_select_the_copied_emote_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'Acceptance').mkdir();path=root/'Acceptance/20-fixture.json'
            correct=dict(directory='.build/20261016-quickslot/Network01')
            foreign=dict(directory='.build/20261016-emote/Network01')
            path.write_text(json.dumps(dict(runs=[correct,foreign])),encoding='utf-8')
            self.assertEqual(audit.selected_record(root,20,'Network01')[2],correct)
            path.write_text(json.dumps(dict(runs=[correct,copy.deepcopy(correct),foreign])),encoding='utf-8')
            with self.assertRaises(ValueError):audit.selected_record(root,20,'Network01')

    def test_legacy_jump_normalization_only_allows_the_exact_pure_contract(self):
        scripts=Path('/workspace/scripts')
        args=['-B',str(scripts/'uep_lyra_abilities/jump_contract.py'),'--report','old.json']
        self.assertEqual(audit.contract_arguments(args,scripts),['-B','-m','uep_lyra_abilities.jump_contract','--report','old.json'])
        with self.assertRaises(ValueError):audit.contract_arguments(['-B','/other/jump_contract.py'],scripts)
        with self.assertRaises(ValueError):audit.contract_arguments(['-B','launch_native_game.py'],scripts)

    def test_native_shutdown_failure_and_unexpected_diagnostics_remain_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'native.log'
            for text in ('Log file closed\nGoodbye Python','Goodbye Python\nTraceback\nLog file closed',
                         'Goodbye Python\nLogPython: Error: callback leaked\nLog file closed'):
                path.write_text(text,encoding='utf-8')
                with self.subTest(text=text),self.assertRaises(ValueError):audit.native_log(path)
            path.write_text('Goodbye Python\nLog file closed',encoding='utf-8')
            self.assertTrue(audit.native_log(path)['native_interpreter_and_log_closed'])

    def test_shared_scope_source_change_cannot_be_hidden_by_old_native_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'Content/Scripts/uep_runtime';folder.mkdir(parents=True)
            for name in ('__init__.py','subscriptions.py'):(folder/name).write_text('close=True\n',encoding='utf-8')
            with patch.object(audit.subprocess,'check_output',return_value=b'close=True\n'):
                self.assertEqual(len(audit.scope_provenance(root,'parent')),2)
                (folder/'subscriptions.py').write_text('close=False\n',encoding='utf-8')
                with self.assertRaises(ValueError):audit.scope_provenance(root,'parent')

    def test_generic_native_nonzero_exit_cannot_become_a_current_sdk_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);migration=root/'Migration';(migration/'Acceptance').mkdir(parents=True);(root/'native').mkdir()
            ledger=dict(native_run=dict(directory='native',summary_sha256='pinned'))
            (migration/'Acceptance/257-current-native-rpc-delegate-and-editor-latent-rejection.json').write_text(json.dumps(ledger),encoding='utf-8')
            summary=dict(status='passed',input_hashes=[],process=dict(exit_code=1),external_gate=dict(exit_code=0))
            (root/'native/summary.json').write_text(json.dumps(summary),encoding='utf-8')
            with patch.object(audit,'sha',return_value='pinned'),self.assertRaises(ValueError):audit.generic_boundaries(root,migration)

    def test_only_the_exact_original_lifetime_requirement_is_promoted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'review.json';path.write_text('{}',encoding='utf-8')
            rows=[dict(version='0.11.0',text=audit.REQUIREMENT,completion_proven=False),
                  dict(version='0.11.0',text='All Standalone and network gameplay',completion_proven=False)]
            report=dict(requirements=rows,inputs=[])
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')):
                attach_ability_lifetime_review(report,{}, {},temporary,path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven'])
            self.assertFalse(rows[0]['full_migration_acceptance_proven'])
            rows[0]['version']='0.10.0'
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')),self.assertRaises(ValueError):
                attach_ability_lifetime_review(report,{}, {},temporary,path)

    def test_a_completion_flag_without_reproducible_native_evidence_is_rejected(self):
        for document in (dict(criterion='partial',completion_proven=True),dict(criterion=audit.REQUIREMENT,completion_proven=False)):
            with self.assertRaises(ValueError):audit.verify_documentation(document,{}, {},'.')
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=dict(native_lifetime_runs_revalidated=1))
        with patch.object(audit,'inspect',return_value=dict(native_lifetime_runs_revalidated=37)),self.assertRaises(ValueError):
            audit.verify_documentation(document,{}, {},'.')
