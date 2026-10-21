import json
from pathlib import Path
import tempfile
import unittest
from test_tdm_lethal_network_contract import report as pipeline_report
from uep_lyra_weapons.weapon_lethal_network_contract import validate, validate_all


def report(peer='server'):
    value=pipeline_report(peer)
    value.update(actual_native_damage_spec_applied=False,fixture_damage_spec_applied=False,
                 native_weapon_damage_observed=peer in ('server','A'),weapon_input_released=True,weapon_profile_classes_restored=True,run_id='one-native-run')
    if peer in ('server','A'):
        value['result']['weapon']=dict(native_pistol_definition=True,ammo_before=12,ammo_after=10,
            activation_entries=2,target_data_entries=2,target_hits=2,only_requested_weapon_profile=True,
            input_entry='PlayerController.inject_enhanced_input_for_action',input_gestures=2,native_clear_line_of_sight=True)
    return value


class WeaponLethalNetworkContractTests(unittest.TestCase):
    def test_native_weapon_producer_on_all_three_peers(self):
        for peer in ('server','A','B0'):
            self.assertEqual(validate(report(peer))['native_weapon_lethal_cases'],1)

    def test_direct_damage_spec_cannot_substitute_for_weapon_input(self):
        for key in ('actual_native_damage_spec_applied','fixture_damage_spec_applied'):
            value=report();value[key]=True
            with self.assertRaises(RuntimeError):validate(value)

    def test_actual_ammo_cost_target_data_and_profile_required(self):
        for key,replacement in (('ammo_after',12),('target_hits',0),('activation_entries',0),('only_requested_weapon_profile',False)):
            value=report();value['result']['weapon'][key]=replacement
            with self.assertRaises(RuntimeError):validate(value)

    def test_native_six_shot_cost_is_allowed_but_cannot_exceed_magazine(self):
        value=report('A');value['result']['weapon'].update(ammo_after=6,input_gestures=6)
        self.assertEqual(validate(value)['native_weapon_lethal_cases'],1)
        value['result']['weapon'].update(ammo_after=-1,input_gestures=13)
        with self.assertRaises(RuntimeError):validate(value)

    def test_native_owner_input_and_line_of_sight_required(self):
        for key,replacement in (('input_gestures',0),('native_clear_line_of_sight',False)):
            value=report('A');value['result']['weapon'][key]=replacement
            with self.assertRaises(RuntimeError):validate(value)

    def test_unreleased_input_or_unrestored_weapon_observers_rejected(self):
        for key in ('weapon_input_released','weapon_profile_classes_restored'):
            value=report();value[key]=False
            with self.assertRaises(RuntimeError):validate(value)

    def test_native_run_identity_and_owner_authority_ammo_must_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for peer in ('server','A','B0'):(root/(peer+'.json')).write_text(json.dumps(report(peer)),encoding='utf-8')
            self.assertEqual(validate_all(root)['real_clients'],2)
            value=report('A');value['result']['weapon']['ammo_after']=9;(root/'A.json').write_text(json.dumps(value),encoding='utf-8')
            with self.assertRaises(RuntimeError):validate_all(root)
