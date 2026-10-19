"""Keep native two-owner Cue gates and require actual default audio counters."""
import copy
import unittest
from unittest.mock import patch
from test_weapon_fire_cue_network_contract import reports as cue_reports
from uep_lyra_weapons import weapon_audio_network_contract as contract
from uep_lyra_weapons import weapon_fire_cue_network_contract as cues


def audio_state():return {key:dict(registered=True,selected_profile="Python",counters={field:0 for field in contract.REQUIRED.get(key,())}) for key in contract.ROUTERS}
def reports():
    server,clients=cue_reports()
    for report in [server,*clients.values()]:report.update(manual_audio_registration=False,audio_helpers_preloaded_by_probe=False,audio_profiles_changed_by_probe=False)
    for row in server["cases"]:row.update(audio_case_before=audio_state(),audio_case_after=audio_state())
    for client in clients.values():
        for row in client["cases"]:
            cue=row["native_firing_cues"][0];before=audio_state();after=copy.deepcopy(before)
            for key,fields in contract.REQUIRED.items():
                for field in fields:after[key]["counters"][field]=1
            cue.update(audio_before=before,audio_after=after)
    return server,clients


class TestWeaponAudioNetworkContract(unittest.TestCase):
    def setUp(self):self.guard=patch.object(cues,"validate_firing");self.native=self.guard.start();self.addCleanup(self.guard.stop)
    def test_composes_all_existing_prediction_cost_damage_and_cue_gates(self):
        result=contract.validate(*reports());self.assertEqual(result["actual_default_audio_dispatch_entries"],32);self.assertEqual(self.native.call_count,1)
        self.native.side_effect=RuntimeError("native prediction proof missing")
        with self.assertRaises(RuntimeError):contract.validate(*reports())
    def test_remote_registered_helper_without_actual_python_dispatch_rejected(self):
        server,clients=reports();clients["B0"]["cases"][0]["native_firing_cues"][0]["audio_after"]["early"]["counters"]["python_calls"]=0
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_dedicated_authority_must_not_execute_any_cosmetic_audio_helper(self):
        server,clients=reports();server["cases"][0]["audio_case_after"]["whiz"]["counters"]["python_calls"]=1
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_original_cue_payload_validation_is_not_bypassed(self):
        server,clients=reports();clients["A"]["cases"][0]["native_firing_cues"][0]["payloads"][0]["surfaces"]=[4]
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_audio_profiles_cannot_follow_switched_cue_profiles(self):
        server,clients=reports();clients["A"]["cases"][0]["native_firing_cues"][0]["audio_after"]["dispatch"]["selected_profile"]="BlueprintFallback"
        with self.assertRaises(RuntimeError):contract.validate(server,clients)
    def test_probe_registration_warming_or_profile_writes_disqualify_proof(self):
        for key in ("manual_audio_registration","audio_helpers_preloaded_by_probe","audio_profiles_changed_by_probe"):
            server,clients=reports();clients["A"][key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):contract.validate(server,clients)
