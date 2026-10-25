"""Reject unsupported source changes and forged candidate-coverage assertions."""
import ast,copy,hashlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_candidate_dispositions as audit

PREFIX="""import engine
CLASS='unchanged'
def mark(actor,name): pass
"""
BEFORE=PREFIX+''.join('def '+n+"(actor):\n    return actor.get_property('TargetActor')\n" for n in ('spawn','colors','update','removal'))+"class Profile:\n    def OnRemoval(self,target):return removal(self)\n"
AFTER=PREFIX+"def mesh_target(actor):\n    target=actor.get_property('TargetActor')\n    return target if valid(target) else None\n"+''.join('def '+n+'(actor):\n    return mesh_target(actor)\n' for n in ('spawn','colors','update','removal'))+"class Profile:\n    def OnRemoval(self,target):return removal(self)\n"

class CandidateDispositionSourceTests(unittest.TestCase):
    def test_current_ast_equivalence_allows_formatting_only(self):
        self.assertEqual(audit.check_source_change('pkg.policy','VALUE=1\n','# comment\nVALUE = 1\n'),'unchanged-python-ast')
    def test_exact_reviewed_private_helper_change_preserves_class_declaration(self):
        self.assertTrue(audit.check_source_change(audit.SPAWNING,BEFORE,AFTER).startswith('reviewed-private'))
    def test_same_change_in_unreviewed_module_fails(self):
        with self.assertRaisesRegex(ValueError,'Unreviewed'):audit.check_source_change('pkg.other',BEFORE,AFTER)
    def test_public_callback_signature_or_body_changes_fail(self):
        for source in (AFTER.replace('self,target','self,target,extra'),AFTER.replace('return removal(self)','return None')):
            with self.assertRaisesRegex(ValueError,'exceeds'):audit.check_source_change(audit.SPAWNING,BEFORE,source)
    def test_skipping_all_live_targets_is_not_the_cached_target_fix(self):
        with self.assertRaisesRegex(ValueError,'exceeds'):audit.check_source_change(audit.SPAWNING,BEFORE,AFTER.replace('target if valid(target) else None','None'))
    def test_added_import_global_mutation_or_hidden_fallback_fails(self):
        for source in ('import extra\n'+AFTER,AFTER.replace("CLASS='unchanged'","CLASS='different'"),AFTER.replace('return mesh_target(actor)',"return actor.call_mixin_original('OnRemoval')",1)):
            with self.assertRaisesRegex(ValueError,'exceeds'):audit.check_source_change(audit.SPAWNING,BEFORE,source)
    def test_missing_original_helper_cannot_be_hidden_by_new_helper(self):
        source=BEFORE.replace('def spawn(actor):','def no_spawn(actor):')
        with self.assertRaisesRegex(ValueError,'helpers missing'):audit.check_source_change(audit.SPAWNING,source,AFTER)
    def test_class_identity_rename_is_not_an_allowed_private_fix(self):
        with self.assertRaisesRegex(ValueError,'exceeds'):audit.check_source_change(audit.SPAWNING,BEFORE,AFTER.replace('class Profile:','class Replacement:'))
    def test_dependency_walk_resolves_relative_imports_and_cycles(self):
        files={'pkg':('pkg/__init__.py',''), 'pkg.profile':('pkg/profile.py','from .helper import f\nfrom . import helper\n'),
            'pkg.helper':('pkg/helper.py','from .profile import Profile\n'), 'unrelated':('unrelated.py','raise RuntimeError()')}
        self.assertEqual(audit.local_dependencies({'pkg.profile'},files),{'pkg','pkg.profile','pkg.helper'})
    def test_dependency_walk_includes_local_absolute_imports(self):
        files={'a':('a.py','import shared\n'), 'shared':('shared.py','import json\n')}
        self.assertEqual(audit.local_dependencies({'a'},files),{'a','shared'})
    def test_missing_native_profile_module_fails(self):
        with self.assertRaisesRegex(ValueError,'source module missing'):audit.local_dependencies({'missing'},{})
    def test_typed_dispatch_profiles_are_included_in_source_inventory(self):
        coverage=dict(assets=[dict(profiles={'Python':dict(python_class='pkg.direct.Profile')},typed_dispatch_bridges=[dict(profiles={'Python':dict(python_class='pkg.typed.Profile')})])])
        self.assertEqual(audit.source_modules(coverage),{'pkg.direct','pkg.typed'})
    def test_green_flags_without_frozen_provenance_do_not_prove_coverage(self):
        for document in ({},{'status':'passed','candidate_dispositions_proven':True},{'schema_version':1,'status':'passed','candidate_dispositions_proven':True}):
            with self.assertRaisesRegex(ValueError,'flags alone'):audit.verify_documentation(document,{}, {},Path('.'))
    def test_baseline_must_be_an_exact_git_commit(self):
        for value in ('HEAD','--help','deadbeef'):
            with self.assertRaisesRegex(ValueError,'Exact native input'):audit.archive_sources(Path('.'),value,'unused')
    def test_captured_native_source_and_current_stage_allow_formatting_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);frozen=root/'captured.py';stage=root/'stage.py'
            frozen.write_text('VALUE = 1\n',encoding='utf-8');stage.write_text('# formatting\nVALUE=1\n',encoding='utf-8')
            record=dict(frozen_input='captured.py',sha256=hashlib.sha256(frozen.read_bytes()).hexdigest().upper())
            audit.verify_captured_script(root,record,'VALUE=1\n','VALUE = 1\n',stage)
    def test_mutating_captured_native_source_fails_its_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);frozen=root/'captured.py';stage=root/'stage.py'
            frozen.write_text('VALUE=1\n',encoding='utf-8');stage.write_text('VALUE=1\n',encoding='utf-8')
            record=dict(frozen_input='captured.py',sha256=hashlib.sha256(frozen.read_bytes()).hexdigest().upper())
            frozen.write_text('VALUE=2\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Captured native policy script changed'):audit.verify_captured_script(root,record,'VALUE=1\n','VALUE=1\n',stage)
    def test_captured_native_script_must_match_its_git_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);frozen=root/'captured.py';stage=root/'stage.py'
            frozen.write_text('VALUE=2\n',encoding='utf-8');stage.write_text('VALUE=1\n',encoding='utf-8')
            record=dict(frozen_input='captured.py',sha256=hashlib.sha256(frozen.read_bytes()).hexdigest().upper())
            with self.assertRaisesRegex(ValueError,'input Git baseline'):audit.verify_captured_script(root,record,'VALUE=1\n','VALUE=1\n',stage)
    def test_stale_stage_policy_cannot_borrow_current_source_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);frozen=root/'captured.py';stage=root/'stage.py'
            frozen.write_text('VALUE=1\n',encoding='utf-8');stage.write_text('VALUE=2\n',encoding='utf-8')
            record=dict(frozen_input='captured.py',sha256=hashlib.sha256(frozen.read_bytes()).hexdigest().upper())
            with self.assertRaisesRegex(ValueError,'staged policy script differs'):audit.verify_captured_script(root,record,'VALUE=1\n','VALUE=1\n',stage)

if __name__=='__main__':unittest.main()
