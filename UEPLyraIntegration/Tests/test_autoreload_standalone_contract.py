from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from test_autoreload_contract import family_report
from uep_lyra_abilities import autoreload_standalone_contract as gate


def report(weapon='rifle',capacity=30):
    result=family_report(weapon,capacity)
    result.update(native_mode='Standalone',standalone_native_equipment_fixture=True,
        temporary_weapon_removed=True,original_inventory_restored=True,
        native_weapon_fixture=dict(weapon=weapon,slot=1,owned_item='/World/TemporaryItem',
            original_model=dict(definition='ID_Pistol'),original_inventory=dict(active=0,items=['/World/OriginalPistol'],
                slots=['/World/OriginalPistol',None,None]),original_auto_active=True))
    return result


class StandaloneAutoReloadEquipmentTests(unittest.TestCase):
    def test_both_native_families_keep_the_full_six_pair_matrix(self):
        for weapon,capacity in (('rifle',30),('shotgun',8)):
            result=gate.validate(report(weapon,capacity))
            self.assertEqual(result['pairs'],6);self.assertTrue(result['native_temporary_equipment_restored'])

    def test_network_or_unsupported_equipment_cannot_claim_standalone_acceptance(self):
        for key,value in (('native_mode','Client'),('weapon','pistol'),('weapon','netshooter')):
            result=report();result[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(RuntimeError):gate.validate(result)

    def test_missing_native_cleanup_and_rollback_are_rejected(self):
        for field in ('standalone_native_equipment_fixture','temporary_weapon_removed','original_inventory_restored'):
            result=report();result[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):gate.validate(result)

    def test_foreign_or_original_item_cannot_be_removed_as_fixture_cleanup(self):
        for key,value in (('slot',0),('owned_item','/World/OriginalPistol'),('weapon','shotgun'),('original_auto_active',False)):
            result=report();result['native_weapon_fixture'][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):gate.validate(result)

    def test_equipment_cleanup_does_not_replace_real_firing_to_empty(self):
        result=report();result['cases'][3]['python']['ammo_api_calls_after_firing_began']=1
        with self.assertRaises(RuntimeError):gate.validate(result)
        result=report();result['cases'][3]['python']['real_fire_rounds']=0
        with self.assertRaises(RuntimeError):gate.validate(result)

    def test_equipment_cleanup_does_not_excuse_late_callbacks(self):
        result=report();result['cases'][4]['python']['no_callbacks_after_end']=False
        with self.assertRaises(RuntimeError):gate.validate(result)
