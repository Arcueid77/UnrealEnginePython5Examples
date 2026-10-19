"""Default automatic routing must be witnessed by actual firing deltas."""
import copy
import unittest
from uep_lyra_weapons.weapon_audio_cold_contract import ROUTERS,REQUIRED,validate


def report():
    value=dict(status="passed",error=None,native_mode="Standalone",selected_weapon="pistol",shots=[],cold_shots=[])
    for key in ("full_acceptance","network_acceptance","physical_input_tested","audio_playback_tested","pixels_tested","manual_audio_registration","audio_helpers_preloaded_by_probe","audio_profiles_changed_by_probe","cue_profiles_changed_by_probe","cue_handler_replayed","health_properties_written","ammo_properties_written"):value[key]=False
    for key in ("original_player_health_unchanged","original_inventory_ammo_restored","original_control_rotation_restored","observer_profiles_restored","all_test_actors_destroyed","default_field_property_preserved"):value[key]=True
    for index in range(2):
        before={key:dict(registered=True,selected_profile="Python",counters={field:index for field in REQUIRED.get(key,())}) for key in ROUTERS}
        before["cue"]=dict(registered=True,selected_profile="Python",counters=dict(python_calls=index));after=copy.deepcopy(before)
        for key,fields in REQUIRED.items():
            for field in fields:after[key]["counters"][field]+=1
        after["cue"]["counters"]["python_calls"]+=1
        value["cold_shots"].append(dict(index=index,kind="first" if index==0 else "repeat",before=before,after=after))
        value["shots"].append(dict(weapon="pistol",profile="Python",input_press_count=1,input_released=True,native_target_callbacks=1,target_count=1,
            ammo_before=6,ammo_after=5,target_health_before=100.,target_health_after=80.,native_enemy_hit=True,weapon_actor_fire_calls=1,
            native_ability_ended=True,native_tasks_observed=1,native_montage_playing=True))
    return value


class TestWeaponAudioColdContract(unittest.TestCase):
    def test_actual_first_and_repeat_default_routes(self):self.assertEqual(validate(report())["actual_audio_dispatch_entries"],8)
    def test_registered_helpers_without_actual_first_shot_python_calls_rejected(self):
        for key,fields in REQUIRED.items():
            value=report();value["cold_shots"][0]["after"][key]["counters"][fields[0]]=0
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_explicit_warming_or_profile_override_disqualifies_cold_claim(self):
        for key in ("manual_audio_registration","audio_helpers_preloaded_by_probe","audio_profiles_changed_by_probe","cue_profiles_changed_by_probe"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_default_blueprint_fallback_is_not_python_routing(self):
        value=report();value["cold_shots"][0]["after"]["dispatch"]["selected_profile"]="BlueprintFallback"
        with self.assertRaises(RuntimeError):validate(value)
    def test_real_cost_enemy_damage_and_natural_cue_required(self):
        for key,bad in (("ammo_after",6),("target_health_after",100.),("native_target_callbacks",0),("native_enemy_hit",False)):
            value=report();value["shots"][0][key]=bad
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
        value=report();value["cold_shots"][0]["after"]["cue"]["counters"]["python_calls"]=0
        with self.assertRaises(RuntimeError):validate(value)
