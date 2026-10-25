import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'Tools'),str(BASE/'Overlay/Content/Scripts')]
import audit_effects_match_acceptance as audit
from audit_migration_acceptance import attach_effects_match_review

class EffectsMatchAcceptanceTests(unittest.TestCase):
    def test_original_non_ai_scope_cannot_be_shrunk(self):
        rows=[dict(path='/Game/Effects/C'+str(i),version='0.12.0') for i in range(63)]
        self.assertEqual(len(audit.checkpoint_assets(dict(assets=rows+[dict(path='/ShooterCore/Bot/AI',version='0.12.0')]))),63)
        for bad in (rows[:-1],rows+[rows[0]],rows[:-1]+[dict(rows[-1],version='0.13.0')]):
            with self.assertRaises(ValueError):audit.checkpoint_assets(dict(assets=bad))
    def spawning_pair(self):
        before="def spawn(actor):return actor.get_property('TargetActor')\ndef colors(actor):return actor.get_property('TargetActor')\ndef update(actor,value):return actor.get_property('TargetActor')\ndef removal(actor):return actor.get_property('TargetActor')\n"
        after="def mesh_target(actor):\n target=actor.get_property('TargetActor')\n return target if valid(target) else None\n"+before.replace("actor.get_property('TargetActor')",'mesh_target(actor)')
        return before,after
    def test_only_spawning_nullable_target_guard_is_equivalent(self):
        before,after=self.spawning_pair();self.assertIn('valid-target-paths-identical',audit.spawning_equivalence(before,after))
        for changed in (after.replace('target if valid(target) else None','None'),after+'OTHER=1\n',after.replace('def removal(actor):return mesh_target(actor)','def removal(actor):return None')):
            with self.assertRaises(ValueError):audit.spawning_equivalence(before,changed)
    def dispatch_pair(self):
        head="def sound_params(actor,spawn):\n if not valid(actor) or not actor.is_a(ue.find_class('Pawn')):return\n local=bool(actor.call_function('IsLocallyViewed'))\n"
        old=" instigator=actor.get_property('Instigator')\n if not valid(instigator):return\n controller=instigator.call_function('GetController')\n if not valid(controller):return\n quickbar=controller.get_component_by_type(ue.find_class('LyraQuickBarComponent'))\n if not valid(quickbar):return\n item=quickbar.call_function('GetActiveSlotItem')\n tag=GameplayTag(TagName='Lyra.ShooterGame.Weapon.MagazineAmmo')\n if not valid(item):return True\n ammo=int(item.call_function('GetStatTagStackCount',tag)) if item.call_function('HasStatTag',tag) else 0\n"
        new=" completed,ammo,diagnostic=macro_policies.weapon_ammo(actor)\n if diagnostic:return True\n if not completed:return\n"
        tail=" for audio in spawn.AudioComponents:\n  if not valid(audio):continue\n  audio.call_function('SetIntParameter','PawnSeed',-1)\n  if local:audio.call_function('SetIntParameter','MagazineAmmo',ammo)\n"
        return head+old+tail,'from . import macro_policies\n'+head+new+tail
    def test_extracted_ammo_macro_preserves_exact_dispatch_body(self):
        before,after=self.dispatch_pair();macro=(BASE/'Overlay/Content/Scripts/uep_lyra_weapons/macro_policies.py').read_text(encoding='utf-8-sig')
        self.assertIn('ammo-macro-extraction-equivalent',audit.dispatch_equivalence(before,after,macro))
        for changed,helper in ((after.replace("'MagazineAmmo'","'OtherParameter'"),macro),(after,macro.replace("'GetController'","'GetOwner'")),(after,macro.replace('return False,0,True','return False,0,False'))):
            with self.assertRaises(ValueError):audit.dispatch_equivalence(before,changed,helper)
    def test_only_actually_unchanged_imported_cue_helpers_can_bridge(self):
        before='def lib(name):return 1\ndef components(a,b,c):return 2\ndef team(a,b):return 3\n';after=before+'def unrelated():return 4\n'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'consumer.py';path.write_text('from uep_lyra_weapons.hero_burst_cue_mixin import lib,components,team\n');files={'consumer':path}
            self.assertEqual(audit.cue_helper_equivalence(before,after,files),['components','lib','team'])
            with self.assertRaises(ValueError):audit.cue_helper_equivalence(before,after.replace('return 2','return 9'),files)
            path.write_text('import uep_lyra_weapons.hero_burst_cue_mixin\n')
            with self.assertRaises(ValueError):audit.cue_helper_equivalence(before,after,files)
    def test_full_pinned_plan_keeps_both_modes_and_new_cache_case(self):
        pairs={(n,name) for n,name,_ in audit.SPECS};self.assertEqual(len(pairs),len(audit.SPECS));self.assertEqual(len(pairs),45)
        self.assertTrue({(138,'Differential02FallbackSeamless'),(138,'Differential03PythonSeamless'),(135,'Differential06StyleGameFrames'),(135,'Differential07StyleCP'),(253,'SpawningRendered01'),(253,'SpawningDestroyed01'),(92,'ImpactsRegression01Expired')}<=pairs)
    def test_attachment_accepts_only_this_exact_original_criterion(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'review.json';path.write_text('{}');rows=[dict(version='0.12.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.12.0',text='Multi-client score/phase state',completion_proven=False)];report=dict(requirements=rows,inputs=[])
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):attach_effects_match_review(report,{},{},folder,path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven']);self.assertFalse(rows[0]['full_migration_acceptance_proven'])
            rows[0]['text']='partial substitute'
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}),self.assertRaises(ValueError):attach_effects_match_review(report,{},{},folder,path)
    def test_unsupported_claim_rejected_before_inspection(self):
        with self.assertRaises(ValueError):audit.verify_documentation(dict(criterion=audit.REQUIREMENT,completion_proven=False),{},{},'.')
