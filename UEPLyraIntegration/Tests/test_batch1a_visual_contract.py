import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_batch1a_visual_contract import validate,PHASES


def reports():
    values={}
    for peer,phases in PHASES.items():
        captures=[]
        for phase in phases:
            native=dict(item='item-'+peer,definition='ID_Pistol_C',maximum=12,magazine=0 if phase=='empty_b' else 9,spare=48)
            panel=dict(magazine=str(native['magazine']),spare='48',visibility=0)
            material=dict(Rounds_Max=12.,Rounds_Current=float(native['magazine']),IsLowAmmo=float(native['magazine']<=2))
            captures.append(dict(phase=phase,image=peer+'-'+phase+'.png',native=native,profiles=['BlueprintFallback','Python'],
                counter_profiles=['BlueprintFallback','Python'],panels=[dict(panel),dict(panel)],weapon_names=['Pistol','Pistol'],
                controller='controller-'+peer,pawn='pawn-'+peer,world='world-'+peer,player_id=1,item=native['item'],definition=native['definition'],
                style='Pistol',test_owned_widget_paths=['a','b','c','d'],production_widget='actual',counters=[dict(bar=material,glow=material)]*2))
        paths=[r['image'] for r in captures]
        values[peer]=dict(status='passed',peer=peer,run_id='run',native_gameplay_state_written=False,
            production_lifecycle_replayed=False,full_visual_acceptance=False,error=None,captures=captures,
            widgets_created=0 if peer=='server' else 4,widgets_closed=0 if peer=='server' else 4,active_test_widgets=0,
            screenshot_queue=dict(requested=paths,issued=list(paths),pending_count=0,rendered_files_verified=False))
    return values


class Batch1AVisualContractTests(unittest.TestCase):
    def test_five_complete_pairs_pass_without_render_claim(self):
        result=validate(reports(),'run');self.assertEqual(result['visual_checkpoint_pairs'],5)
        self.assertFalse(result['rendered_files_verified']);self.assertFalse(result['full_visual_acceptance'])

    def test_missing_reordered_or_duplicate_checkpoint_rejected(self):
        for change in ('missing','reorder','duplicate'):
            value=reports();rows=value['A']['captures']
            if change=='missing':rows.pop()
            elif change=='reorder':rows.reverse()
            else:rows.append(copy.deepcopy(rows[0]))
            with self.subTest(change=change),self.assertRaises(ValueError):validate(value,'run')

    def test_widget_or_root_leaks_are_not_hidden_by_passed_status(self):
        for field,value in [('widgets_closed',0),('active_test_widgets',1),('widgets_created',0)]:
            data=reports();data['B0'][field]=value
            with self.assertRaises(ValueError):validate(data,'run')

    def test_wrong_profile_owner_native_state_or_production_replacement_rejected(self):
        for field,value in [('profiles',['Python','Python']),('item','foreign'),('production_widget','a'),
                            ('panels',[{},{}]),('weapon_names',['Pistol','Rifle'])]:
            data=reports();data['A']['captures'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate(data,'run')

    def test_unissued_image_or_render_claim_rejected(self):
        for field,value in [('pending_count',1),('issued',[]),('rendered_files_verified',True)]:
            data=reports();data['A']['screenshot_queue'][field]=value
            with self.assertRaises(ValueError):validate(data,'run')

    def test_material_mismatch_or_gameplay_write_cannot_pass(self):
        value=reports();value['B0']['captures'][0]['counters'][0]['bar']['Rounds_Current']=5.
        with self.assertRaises(ValueError):validate(value,'run')
        value=reports();value['A']['native_gameplay_state_written']=True
        with self.assertRaises(ValueError):validate(value,'run')


if __name__=='__main__':unittest.main()
