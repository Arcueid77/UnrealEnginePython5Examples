"""Reject duplicate parent/Delay dispatch and child-specific continuation drift."""
import unittest
from uep_lyra_audio.music_family_contract import PLAN,validate


def report():
    value=dict(status="passed",error=None,cases=[])
    for key in ("full_acceptance","network_acceptance","begin_play_replayed","delay_callback_replayed","message_callback_replayed","python_subscription_roots_added","production_proxies_cancelled_by_probe","cpp_compile_executed"):value[key]=False
    for key in ("original_gi_music_preserved","natural_manager_fields_restored","base_profile_family_restored","player_health_unchanged","owned_actors_destroyed","all_owned_proxy_gi_references_released","diagnostic_probe_roots_removed"):value[key]=True
    for index,(label,profile,mode) in enumerate(PLAN):
        row=dict(index=index,**{"class":label},profile=profile,mode=mode,native_parent_begin_calls=1,immediate_proxy_count=2,after_delay_calls=int(mode!="destroy"),
            after_delay_elapsed=.22,after_delay_profile=("Python" if profile=="BlueprintFallback" else "BlueprintFallback") if mode=="switch" else profile,
            audio_menu=label=="front_end",component_menu=False,proxy_count_after_delay=3 if label=="control_point" and mode!="destroy" else 2,
            stinger_positive_arguments=[True,False,False],captured_callback_entries=3,proxy_refs_after_gc_and_messages=0,proxies_inactive_after_gc_and_messages=True)
        value["cases"].append(row)
    return value


class TestMusicFamilyContract(unittest.TestCase):
    def test_complete_three_child_profile_timing_matrix(self):self.assertEqual(validate(report())["cases"],18)
    def test_parent_replay_or_duplicate_listener_rejected(self):
        for key,wrong in (("native_parent_begin_calls",2),("immediate_proxy_count",4)):
            value=report();value["cases"][0][key]=wrong
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_destroyed_target_cannot_complete_delay(self):
        value=report();value["cases"][2]["after_delay_calls"]=1
        with self.assertRaises(RuntimeError):validate(value)
    def test_delay_and_current_profile_are_required(self):
        value=report();value["cases"][0]["after_delay_elapsed"]=.01
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value["cases"][1]["after_delay_profile"]=value["cases"][1]["profile"]
        with self.assertRaises(RuntimeError):validate(value)
    def test_control_point_team_transform_must_reach_stinger(self):
        value=report();row=next(r for r in value["cases"] if r["class"]=="control_point" and r["mode"]=="normal");row["stinger_positive_arguments"]=[True,True,False]
        with self.assertRaises(RuntimeError):validate(value)
    def test_new_python_roots_and_replayed_latent_callback_disqualify_proof(self):
        for key in ("python_subscription_roots_added","delay_callback_replayed","message_callback_replayed"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
