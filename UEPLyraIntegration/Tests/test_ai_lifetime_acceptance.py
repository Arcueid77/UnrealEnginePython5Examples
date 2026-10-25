import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'Tools'),str(BASE/'Overlay/Content/Scripts')]
import audit_ai_lifetime_acceptance as audit
from audit_migration_acceptance import attach_ai_lifetime_review

class AILifetimeAcceptanceTests(unittest.TestCase):
    def test_old_cue_macro_import_is_bounded_to_the_unused_helper_change(self):
        old="import unreal_engine as ue\ndef lib(name):return ue.find_class(name).get_cdo()\ndef append(actor,component):return None\ndef dash(mesh):return mesh.call_function('ComponentHasTag','ignore')\ndef death(mesh):return mesh.call_function('ComponentHasTag','ignore')\n"
        new=old.replace('import unreal_engine as ue','import unreal_engine as ue\nfrom .macro_policies import ignore_tag').replace('return None','return component').replace("mesh.call_function('ComponentHasTag','ignore')",'ignore_tag(mesh)')
        macro=(BASE/'Overlay/Content/Scripts/uep_lyra_weapons/macro_policies.py').read_text(encoding='utf-8-sig')
        self.assertIn('added_macro_import',audit.imported_lib_bridge(old,new,macro))
        for changed,helper in ((new.replace('get_cdo()','get_other()'),macro),(new+'ue.request_exit()\n',macro),(new,macro+'\nue.request_exit()\n'),(new,macro.replace('def snapshot():','def snapshot(value=ue.find_class("Actor")):'))):
            with self.assertRaises(ValueError):audit.imported_lib_bridge(old,changed,helper)
    def test_only_original_twelve_ai_candidates_at_original_version(self):
        rows=[dict(path='/ShooterCore/Bot/C'+str(i),version='0.12.0') for i in range(12)]
        self.assertEqual(len(audit.ai_candidates(dict(assets=rows))),12)
        for invalid in (rows[:-1],rows+[rows[0]],rows[:-1]+[dict(rows[-1],version='0.13.0')]):
            with self.assertRaises(ValueError):audit.ai_candidates(dict(assets=invalid))
    def test_shared_lib_closure_does_not_execute_unrelated_cue_append(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'uep_lyra_world').mkdir();(root/'uep_lyra_weapons').mkdir()
            (root/'uep_lyra_world/shooter_ai_mixin.py').write_text('from uep_lyra_weapons.hero_burst_cue_mixin import lib\n')
            (root/'uep_lyra_weapons/hero_burst_cue_mixin.py').write_text('def lib(name):\n return None\ndef append():\n from . import macro_policies\n')
            (root/'uep_lyra_weapons/macro_policies.py').write_text('raise RuntimeError()\n')
            self.assertEqual(set(audit.closure(root,['shooter_ai'])),{'uep_lyra_world.shooter_ai_mixin',audit.SHARED})
    def test_wider_changed_cue_dependency_cannot_use_lib_exception(self):
        for text in ('import uep_lyra_weapons.hero_burst_cue_mixin\n','from uep_lyra_weapons.hero_burst_cue_mixin import lib,append\n'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);(root/'uep_lyra_world').mkdir();(root/'uep_lyra_world/shooter_ai_mixin.py').write_text(text)
                with self.assertRaises(ValueError):audit.closure(root,['shooter_ai'])
    def test_acceptance_attaches_only_exact_ai_criterion(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'review.json';path.write_text('{}')
            rows=[dict(version='0.12.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.12.0',text='other condition',completion_proven=False)]
            report=dict(requirements=rows,inputs=[])
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):attach_ai_lifetime_review(report,{}, {}, folder,path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven'])
            self.assertFalse(rows[0]['full_migration_acceptance_proven'])
    def test_changed_or_duplicate_requirement_never_attaches(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'review.json';path.write_text('{}')
            for rows in ([],[dict(version='0.13.0',text=audit.REQUIREMENT)],[dict(version='0.12.0',text=audit.REQUIREMENT)]*2):
                with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):
                    with self.assertRaises(ValueError):attach_ai_lifetime_review(dict(requirements=rows,inputs=[]),{}, {},folder,path)
    def test_missing_semantic_proof_rejected_before_any_inspection(self):
        with self.assertRaises(ValueError):audit.verify_documentation({'criterion':audit.REQUIREMENT,'completion_proven':False},{},{},'.')
