"""Require actual original macro outputs and caller-owned inventory restoration."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_weapons.macro_closure_contract import FALSE_FIELDS,TRUE_FIELDS,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',weapon_cases=[{}]*7,ammo_cases=[{}]*5,tag_cases=[{}]*4,specific_cases=[{}]*3);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r


class MacroContractTests(unittest.TestCase):
    def test_complete_original_macro_matrix(self):self.assertEqual(validate(report())['weapon_cases'],7)
    def test_actual_completion_and_branch_outputs_required(self):
        for key in ('exact_native_ammo_completion_and_values_match','exact_native_specific_mesh_macro_matches'):
            r=report();r[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_original_definitions_must_not_be_changed(self):
        r=report();r['original_macro_assets_modified']=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_real_inventory_state_and_probe_lifetime_must_restore(self):
        r=report();r['original_equipment_spawn_array_and_magazine_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
