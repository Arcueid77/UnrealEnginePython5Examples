"""Require child delivery, nullable targets, original verb and listener cleanup."""
import copy
import unittest
from uep_lyra_hud.accolade_relay_contract import PROFILES,CASES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',natural_relays=1,profiles=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','production_subscription_replaced','native_relay_proxies_cancelled_by_fixture','health_properties_written'):r[k]=False
    for k in ('observer_scope_closed','owned_actors_destroyed','owned_components_destroyed','original_scores_restored','actual_tdm_target_score_restored','original_health_unchanged','diagnostic_probe_root_removed','production_profiles_restored'):r[k]=True
    for p in PROFILES:
        row=dict(profile=p,native_listener_proxies=1,cases=[],diagnostic_fallbacks=0,relay_proxy_gi_released_after_gc_and_message=True,engine_gc_frames=3,python_client_requests=3,python_cosmetic_broadcasts=6,python_player_helper_calls=12)
        for name in CASES:
            matched=name not in ('wrong-channel','parent-channel');expected=dict(player=None if name in ('foreign','null') else 'player-state',target_channel='Lyra.ShooterGame.Accolade',payload_tag='Lyra.ShooterGame.Accolade.EliminationChain.2x',text='',object=None,channel='Lyra.AddNotification.Message')
            row['cases'].append(dict(name=name,fixture_entries=int(matched),natural_entries=int(matched),expected=expected,notifications=[copy.deepcopy(expected) for _ in range(2)] if matched else []))
        r['profiles'].append(row)
    return r


class AccoladeContractTests(unittest.TestCase):
    def test_complete_native_partial_matrix(self):self.assertEqual(validate(report())['native_message_cases'],16)
    def test_child_and_nested_channels_must_actually_arrive(self):
        for index in (1,2):
            r=report();r['profiles'][0]['cases'][index]['fixture_entries']=0
            with self.subTest(index=index),self.assertRaises(RuntimeError):validate(r)
    def test_parent_and_wrong_channel_must_not_arrive(self):
        r=report();r['profiles'][0]['cases'][7]['fixture_entries']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_null_target_must_not_be_replaced_or_dropped(self):
        r=report();r['profiles'][0]['cases'][5]['notifications'][0]['player']='other'
        with self.assertRaises(RuntimeError):validate(r)
    def test_original_verb_empty_text_and_object_must_survive_native_transport(self):
        for key,value in (('payload_tag','Lyra.ShooterGame.Accolade'),('text','invented'),('object','asset')):
            r=report();r['profiles'][0]['cases'][0]['notifications'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_independent_sequence_and_duplicate_native_helper_calls_required(self):
        for key,value in (('python_client_requests',6),('python_cosmetic_broadcasts',3),('python_player_helper_calls',6)):
            r=report();r['profiles'][1][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_native_proxy_lifetime_and_cleanup_required(self):
        r=report();r['profiles'][0]['relay_proxy_gi_released_after_gc_and_message']=False
        with self.assertRaises(RuntimeError):validate(r)
