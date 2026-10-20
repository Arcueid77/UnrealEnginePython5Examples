"""Require actual native scheduling/GAS delivery and original actor cleanup."""
import unittest
from uep_lyra_world.shooter_ai_contract import FALSE_FIELDS,TRUE_FIELDS,validate


def report():
    r=dict(status='passed',error=None,profile='Python',mode='tdm',native_mode='Standalone',ammo_cases=[{}]*4,weapon_cases=[{}]*5,diagnostic_fallbacks=0,native_tree_tick_samples=4);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r


class ShooterContractTests(unittest.TestCase):
    def test_complete_native_tree_matrix(self):self.assertEqual(validate(report())['weapon_cases'],5)
    def test_real_tree_and_gas_delivery_required(self):
        for key in ('native_tree_service_callbacks_and_intervals_observed','native_gas_reload_slot_fire_payloads_observed'):
            r=report();r[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_cleanup_and_no_health_writes_required(self):
        for key,value in (('inventory_slots_stats_and_transforms_restored',False),('health_properties_written',True)):
            r=report();r[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_cp_mode_requires_actual_cp_controller_child(self):
        r=report();r.update(mode='cp',natural_controller_class='B_AI_Controller_LyraShooter_C')
        with self.assertRaises(RuntimeError):validate(r)
