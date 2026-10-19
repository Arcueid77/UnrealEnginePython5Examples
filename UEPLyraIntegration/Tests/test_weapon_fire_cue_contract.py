"""Cue proof augments the real firing gate and rejects weak typed transport."""
import copy
import unittest
from unittest.mock import patch
from uep_lyra_weapons import weapon_fire_cue_contract as contract


def report():
    def row(weapon,profile,surface=0):return dict(weapon=weapon,profile=profile,surface=surface,native_gas_cue_requests=1,native_cue_entries=1,native_weapon_fire_entries=1,
        typed_payload_matches=True,rifle_audio_entries=int(weapon=="Rifle"),rifle_sound_matches=True,python_order_matches=True)
    value=dict(cue_observers_and_profiles_restored=True,native_static_audio_abi_preserved=True,cue_handler_replayed=False,
        controlled_cue_cases=[row(*case) for case in contract.PLAN])
    expected=[(weapon.title(),profile) for weapon,profile,_ in contract.FIRING_PLAN]+[("Pistol",profile) for profile in contract.PROFILES for _ in range(4)]
    value["native_input_cue_cases"]=[row(*case) for case in expected];return value


class TestWeaponFireCueContract(unittest.TestCase):
    def setUp(self):self.guard=patch.object(contract,"validate_firing");self.base=self.guard.start();self.addCleanup(self.guard.stop)
    def test_complete_cue_matrix_still_runs_the_original_native_firing_gate(self):
        value=report();result=contract.validate(value);self.base.assert_called_once_with(value);self.assertFalse(result["audible_playback_accepted"])
    def test_missing_surface_or_profile_case_rejected(self):
        value=report();value["controlled_cue_cases"].pop()
        with self.assertRaises(RuntimeError):contract.validate(value)
    def test_native_typed_payload_and_single_entry_required(self):
        for key,val in (("native_gas_cue_requests",0),("native_cue_entries",0),("native_weapon_fire_entries",2),("typed_payload_matches",False)):
            value=report();value["controlled_cue_cases"][0][key]=val
            with self.subTest(key=key),self.assertRaises(RuntimeError):contract.validate(value)
    def test_rifle_specific_audio_and_original_order_required(self):
        for key,val in (("rifle_audio_entries",0),("rifle_sound_matches",False),("python_order_matches",False)):
            value=report();row=next(row for row in value["controlled_cue_cases"] if row["weapon"]=="Rifle" and row["profile"]=="Python");row[key]=val
            with self.subTest(key=key),self.assertRaises(RuntimeError):contract.validate(value)
    def test_actual_input_case_order_cannot_be_replaced_by_repeated_cues(self):
        value=report();value["native_input_cue_cases"][0]["weapon"]="Shotgun"
        with self.assertRaises(RuntimeError):contract.validate(value)
    def test_live_input_cue_payload_must_match(self):
        value=report();value["native_input_cue_cases"][0]["typed_payload_matches"]=False
        with self.assertRaises(RuntimeError):contract.validate(value)
    def test_observer_abi_restoration_and_no_replay_required(self):
        for key,val in (("cue_observers_and_profiles_restored",False),("native_static_audio_abi_preserved",False),("cue_handler_replayed",True)):
            value=report();value[key]=val
            with self.subTest(key=key),self.assertRaises(RuntimeError):contract.validate(value)
