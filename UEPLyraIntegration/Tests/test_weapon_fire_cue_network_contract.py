"""Typed Cue/profile checks cannot replace native firing replication evidence."""
import copy
import unittest
from unittest.mock import patch
from uep_lyra_weapons import weapon_fire_cue_network_contract as contract


def identity(number):return dict(valid=True,transport="Legacy",wire_id=str(number))


def reports(weapon="pistol"):
    server=dict(weapon=weapon,cases=[],cue_handler_replayed=False,cue_assets_or_policy_changed=False)
    clients={peer:dict(cases=[],cue_handler_replayed=False,cue_assets_or_policy_changed=False) for peer in contract.PEERS}
    for position,(_,profile) in enumerate(contract.PLAN):
        source=identity(100+position//2);server["cases"].append(dict(source_identity=source,native_firing_cues=[]))
        order=["SendWeaponFire","Weapon.Fire"]+(["Weapon.TriggerFireAudio"] if weapon=="rifle" else [])+["SetWeaponSoundParams","EarlyReflections","WhizBy"]
        for client in clients.values():
            cue=dict(profile=profile,target=copy.deepcopy(source),location=[1.,2.,3.],normal=[0.,0.,1.],surface=1,
                payloads=[dict(positions=[[1.,2.,3.]],normals=[[0.,0.,1.]],surfaces=[1])],
                rifle_sounds=[dict(sound=contract.RIFLE_SOUND,target=copy.deepcopy(source))] if weapon=="rifle" else [],python_order=order if profile=="Python" else None)
            client["cases"].append(dict(native_firing_cues=[cue]))
    return server,clients


class TestWeaponFireCueNetworkContract(unittest.TestCase):
    def setUp(self):self.guard=patch.object(contract,"validate_firing");self.base=self.guard.start();self.addCleanup(self.guard.stop)
    def test_actual_firing_replication_gate_is_still_required_for_each_weapon(self):
        for weapon in ("pistol","rifle","shotgun"):
            values=reports(weapon);self.assertEqual(contract.validate(*values)["native_predicted_remote_cue_entries"],8)
        self.assertEqual(self.base.call_count,3)
    def test_wrong_executed_profile_or_source_identity_rejected(self):
        for key,value in (("profile","Python"),("target",identity(999))):
            server,clients=reports();clients["A"]["cases"][0]["native_firing_cues"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_duplicate_or_missing_native_cue_rejected(self):
        for count in (0,2):
            server,clients=reports();row=clients["B0"]["cases"][0];row["native_firing_cues"]*=count
            with self.subTest(count=count),self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_native_vector_and_surface_arrays_must_match_the_cue(self):
        server,clients=reports();clients["A"]["cases"][0]["native_firing_cues"][0]["payloads"][0]["surfaces"]=[4]
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_predicted_remote_location_and_normal_quantization_limits(self):
        server,clients=reports();cue=clients["B0"]["cases"][0]["native_firing_cues"][0];cue["location"][0]+=1.;cue["payloads"][0]["positions"][0][0]+=1.
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_rifle_specific_sound_and_target_required(self):
        server,clients=reports("rifle");clients["A"]["cases"][0]["native_firing_cues"][0]["rifle_sounds"][0]["sound"]="different"
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_python_order_and_no_cosmetic_authority_execution_required(self):
        server,clients=reports();clients["A"]["cases"][1]["native_firing_cues"][0]["python_order"].reverse()
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
        server,clients=reports();server["cases"][0]["native_firing_cues"]=[{}]
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_replay_or_production_mutation_cannot_be_claimed_as_native_proof(self):
        for field in ("cue_handler_replayed","cue_assets_or_policy_changed"):
            server,clients=reports();server[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):contract.validate(server,clients)
