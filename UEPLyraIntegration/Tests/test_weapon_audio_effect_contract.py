"""Natural effect initialization cannot be replaced by component or tap fixtures."""
import unittest
from test_weapon_audio_cold_contract import report as cold_report
from uep_lyra_weapons.weapon_audio_effect_contract import validate


def report():
    value=cold_report();value.update(effect_shots=[],authored_settings_unchanged=True)
    for key in ("preset_initialized_by_probe","preset_settings_written_by_probe","fixture_taps_added","audio_components_created_by_probe","physical_audio_output_tested","waveform_output_accepted"):value[key]=False
    for index in range(2):
        preset=dict(resident=True,authored_taps=[dict(TapId=i) for i in range(8)],dynamic_tap_ids=list(range(8)),dynamic_taps=[dict(TapId=i) for i in range(8)])
        value["effect_shots"].append(dict(index=index,preset_after=preset,weapon_components=[dict(sound="/Game/Audio/Pistol/ActualFire.ActualFire",playing=True)]))
    return value


class TestWeaponAudioEffectContract(unittest.TestCase):
    def test_actual_initialized_taps_and_native_weapon_playing_components(self):self.assertEqual(validate(report())["actual_native_initialized_taps"],8)
    def test_empty_dynamic_preset_is_not_effect_initialization(self):
        value=report();value["effect_shots"][0]["preset_after"]["dynamic_tap_ids"]=[]
        with self.assertRaises(RuntimeError):validate(value)
    def test_manual_bootstrap_or_probe_audio_components_disqualify_natural_claim(self):
        for key in ("preset_initialized_by_probe","preset_settings_written_by_probe","fixture_taps_added","audio_components_created_by_probe"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_missing_or_unrelated_audio_component_rejected(self):
        value=report();value["effect_shots"][0]["weapon_components"][0]["sound"]="/Game/Audio/Music"
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value["effect_shots"][0]["weapon_components"][0]["playing"]=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_authored_changes_hardware_and_waveform_overclaim_rejected(self):
        for key,wrong in (("authored_settings_unchanged",False),("physical_audio_output_tested",True),("waveform_output_accepted",True)):
            value=report();value[key]=wrong
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_rifle_cached_component_requires_actual_native_fire_trigger(self):
        value=report();value["selected_weapon"]="rifle"
        for shot in value["shots"]:shot["weapon"]="rifle"
        for row in value["effect_shots"]:
            row["weapon_components"]=[dict(path="cached-rifle",sound="/Game/Audio/Rifle/ActualFire",playing=True,reused_from_before_shot=True)]
            row["trigger_events"]=[dict(component="cached-rifle",native_fire_trigger_delta=1)]
        self.assertEqual(validate(value)["actual_weapon_components"],2)
        value["effect_shots"][1]["trigger_events"][0]["native_fire_trigger_delta"]=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_unrelated_cached_rifle_component_is_not_trigger_witness(self):
        value=report();value["selected_weapon"]="rifle"
        for shot in value["shots"]:shot["weapon"]="rifle"
        for row in value["effect_shots"]:
            row["weapon_components"]=[dict(path="other",sound="/Game/Audio/Rifle/ActualFire",playing=True)]
            row["trigger_events"]=[dict(component="actual-cache",native_fire_trigger_delta=1)]
        with self.assertRaises(RuntimeError):validate(value)
