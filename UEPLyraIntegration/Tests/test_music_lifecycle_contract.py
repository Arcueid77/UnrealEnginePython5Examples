"""Preserve native delayed GI lifetime and reject replay/extra subscriptions."""
import unittest
from uep_lyra_audio.music_lifecycle_contract import PLAN,validate


def report():
    value=dict(status="passed",error=None,natural_python_begin_before_probe=1,cases=[])
    for key in ("full_acceptance","network_acceptance","child_delay_business_migrated","begin_play_replayed","callback_replayed","python_subscription_roots_added","native_proxies_cancelled_by_probe","cpp_compile_executed"):value[key]=False
    for key in ("original_music_pointer_restored","natural_manager_fields_restored","player_health_unchanged","owned_actors_destroyed","all_owned_proxy_gi_references_released"):value[key]=True
    for index in range(4):
        mode="reuse" if index%2==0 else "create";messages=[dict(channel=c,target=t,intensity=a,callback_entries=int(c!="Lyra.Elimination")) for c,t,a in PLAN]
        value["cases"].append(dict(index=index,mode=mode,native_begin_calls=1,native_proxies_added=2,component_gi_music_same=True,created_new_music=mode=="create",messages=messages,
            profile_switch_proxy_count_unchanged=True,switched_message_intensity=1.,switched_callback_entries=1,component_destroyed=True,
            proxy_gi_references_immediately_after_destroy=2,proxy_gi_references_after_broadcast=0,owned_proxies_inactive_after_broadcast=True,native_gc_boundary_observed=True))
    return value


class TestMusicLifecycleContract(unittest.TestCase):
    def test_native_lifetime_and_complete_message_matrix(self):self.assertEqual(validate(report())["native_listener_proxies"],8)
    def test_proactive_cleanup_does_not_match_original_delayed_behavior(self):
        value=report();value["cases"][0]["proxy_gi_references_immediately_after_destroy"]=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_missing_post_broadcast_release_rejected(self):
        value=report();value["cases"][0]["proxy_gi_references_after_broadcast"]=2
        with self.assertRaises(RuntimeError):validate(value)
    def test_profile_switch_must_not_add_a_listener(self):
        value=report();value["cases"][0]["profile_switch_proxy_count_unchanged"]=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_wrong_target_filter_or_duplicate_dispatch_rejected(self):
        value=report();value["cases"][0]["messages"][1]["intensity"]=1.
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value["cases"][0]["messages"][0]["callback_entries"]=2
        with self.assertRaises(RuntimeError):validate(value)
    def test_begin_replay_python_roots_and_child_business_overclaim_rejected(self):
        for key in ("begin_play_replayed","callback_replayed","python_subscription_roots_added","child_delay_business_migrated"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
