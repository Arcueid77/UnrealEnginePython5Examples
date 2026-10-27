import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_batch1a_acceptance as audit
from audit_migration_acceptance import attach_batch1a_review


class Batch1AAcceptanceTests(unittest.TestCase):
    def test_capture_must_match_actual_native_ack_owner_and_weapon(self):
        ack=dict(weapon=dict(magazine=9,item='owned'),player=dict(controller_path='controller',pawn_path='pawn',
            world_token='world',player_id=42),weapon_hud={'widget':'production'})
        capture=dict(phase='fire_a',native=dict(ack['weapon']),controller='controller',pawn='pawn',world='world',
            player_id=42,production_widget='production')
        native={'A':dict(phases=[dict(phase='fire_a',ack=ack)])};visual={'A':dict(captures=[capture])}
        audit.native_matches(native,visual)
        for field,value in [('controller','foreign'),('pawn','foreign'),('world','foreign'),('player_id',99),
                            ('production_widget','test clone'),('native',{'magazine':0})]:
            changed=copy.deepcopy(visual);changed['A']['captures'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):audit.native_matches(native,changed)

    def test_attachment_accepts_only_original_batch1a_requirement(self):
        report=dict(requirements=[dict(version='0.9.0',text=audit.REQUIREMENT,completion_proven=False),
            dict(version='0.14.0',text='Both Experiences',completion_proven=False)],inputs=[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json';path.write_text('{}')
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):
                attach_batch1a_review(report,{}, {},directory,path)
            self.assertTrue(report['requirements'][0]['completion_proven'])
            self.assertFalse(report['requirements'][1]['completion_proven'])
            report['requirements'][0]['version']='0.14.0'
            with patch.object(audit,'verify_documentation',return_value={}),self.assertRaises(ValueError):
                attach_batch1a_review(report,{}, {},directory,path)

    def test_audited_claim_cannot_replace_actual_runtime_and_image_review(self):
        expected=dict(status='passed',criterion=audit.REQUIREMENT,visual_checkpoint_pairs=5,summary_sha256='A'*64)
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=expected)
        with patch.object(audit,'inspect',return_value=expected):
            audit.verify_documentation(document,{}, {},'.')
            changed=copy.deepcopy(document);changed['review']['visual_checkpoint_pairs']=4
            with self.assertRaises(ValueError):audit.verify_documentation(changed,{}, {},'.')


if __name__=='__main__':unittest.main()
