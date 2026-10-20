"""Native feed assertions must reject missing delivery, ordering and cleanup."""
import copy
import unittest
from uep_lyra_hud.elimination_feed_relay_contract import CASES,PROFILES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',natural_relays=1,profiles=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','production_subscription_replaced','native_relay_proxies_cancelled_by_fixture','health_properties_written'):r[k]=False
    for k in ('observer_scope_closed','owned_actors_destroyed','owned_components_destroyed','original_scores_restored','actual_tdm_target_score_restored','original_health_unchanged','diagnostic_probe_root_removed','production_profiles_restored'):r[k]=True
    for p in PROFILES:
        row=dict(profile=p,native_listener_proxies=1,cases=[],diagnostic_fallbacks=0,relay_proxy_gi_released_after_gc_and_message=True,engine_gc_frames=3,python_multicast_requests=4,python_cosmetic_broadcasts=4)
        for name in CASES:
            matched=name not in ('wrong-channel','child-channel');expected=dict(attacker='a',attackee='b',attacker_team=1,attackee_team=2,tags=['test'],slot='HUD.Slot.EliminationFeed',channel='Lyra.AddNotification.KillFeed')
            row['cases'].append(dict(name=name,fixture_entries=int(matched),natural_entries=int(matched),notifications=[copy.deepcopy(expected) for _ in range(2)] if matched else [],expected=expected))
        r['profiles'].append(row)
    return r


class RelayContractTests(unittest.TestCase):
    def test_complete_source_python_matrix(self):self.assertEqual(validate(report())['native_message_cases'],12)
    def test_natural_map_relay_cannot_be_replaced_with_only_a_fixture(self):
        r=report();r['natural_relays']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_exact_matching_cannot_accept_wrong_or_child_channel(self):
        for index in (4,5):
            r=report();r['profiles'][0]['cases'][index]['fixture_entries']=1
            with self.subTest(index=index),self.assertRaises(RuntimeError):validate(r)
    def test_player_order_team_tags_and_slot_must_survive_native_typed_delivery(self):
        for field,value in (('attacker','b'),('attacker_team',2),('tags',[]),('slot','wrong')):
            r=report();r['profiles'][0]['cases'][0]['notifications'][0][field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_original_proxy_must_release_after_component_destruction(self):
        r=report();r['profiles'][0]['relay_proxy_gi_released_after_gc_and_message']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_rpc_and_cosmetic_side_effect_counts_must_both_match(self):
        for key in ('python_multicast_requests','python_cosmetic_broadcasts'):
            r=report();r['profiles'][1][key]=8
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_no_callback_replay_or_production_subscription_cancellation(self):
        for key in ('callbacks_replayed','begin_play_replayed','native_relay_proxies_cancelled_by_fixture','production_subscription_replaced'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
