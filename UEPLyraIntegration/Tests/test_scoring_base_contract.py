"""Native score/filter/cleanup and actual reset evidence requirements."""
import unittest
from uep_lyra_weapons.scoring_base_contract import CASES,PROFILES,EXPECTED,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',natural_child_begin_python=1,natural_child_warmup_python=1,message_cases=[],lifetime_cases=[],warmup_cases=[],reset_cases=[],spawning_skip_cases=[dict(tag_present=True,same_pawn=True)])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','python_subscription_roots_added','native_proxy_cancelled_by_fixture','health_properties_written'):r[k]=False
    for k in ('owned_native_proxy_gi_refs_released','owned_actors_destroyed','owned_components_destroyed','diagnostic_sender_root_removed','actual_tdm_target_score_restored'):r[k]=True
    for profile in PROFILES:
        for name,channel,a,b in CASES:
            callback=dict(elimination=int(name in ('enemy','friendly','null','pawn-source','pawn-target')),assist=int(name in ('assist','assist-pawn')))
            r['message_cases'].append(dict(name=name,profile=profile,delta=EXPECTED[name][:],fixture_callbacks=callback.copy(),real_child_callbacks=callback.copy()))
        r['lifetime_cases'].append(dict(profile=profile,native_proxies=2,gi_refs_released=True,engine_gc_frames=3))
        r['warmup_cases'].append(dict(profile=profile,spawner_available=True,grenade_destroyed=True,callback_entries=1))
        r['reset_cases'].append(dict(profile=profile,old_pawn='old-'+profile,new_pawn='new-'+profile,health=100.,death=0,native_asc_bound=True,callback_entries=1,spawning_skip_calls=0))
    return r


class ScoringBaseContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_message_cases'],16)
    def test_team_add_before_failed_instigator_cast_required(self):
        r=report();r['message_cases'][3]['delta']=[0]*8
        with self.assertRaises(RuntimeError):validate(r)
    def test_friendly_death_is_not_counted(self):
        r=report();r['message_cases'][1]['delta'][1]=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_real_child_static_base_call_required(self):
        r=report();r['natural_child_begin_python']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_actual_child_receives_same_exact_channels(self):
        r=report();r['message_cases'][0]['real_child_callbacks']['elimination']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_gc_and_matching_broadcast_release_required(self):
        r=report();r['lifetime_cases'][0]['gi_refs_released']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_post_warmup_destroys_actual_grenade(self):
        r=report();r['warmup_cases'][0]['grenade_destroyed']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_reset_must_replace_pawn_and_rebind_asc(self):
        r=report();r['reset_cases'][0]['new_pawn']=r['reset_cases'][0]['old_pawn']
        with self.assertRaises(RuntimeError):validate(r)
    def test_spawning_pawn_must_be_skipped(self):
        r=report();r['spawning_skip_cases'][0]['same_pawn']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_callback_replay_or_health_write_cannot_fake_reset(self):
        for key in ('callbacks_replayed','health_properties_written','network_acceptance'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
