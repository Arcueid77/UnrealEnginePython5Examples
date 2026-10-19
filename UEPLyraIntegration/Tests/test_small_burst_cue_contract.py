"""Reject missing actual Niagara/audio/music/parent lifetime evidence."""
import copy
import unittest
from uep_lyra_weapons.small_burst_cue_contract import validate,HEAL_SOUND


def report():
    value=dict(status='passed',error=None,native_mode='Standalone',color_cases=[],melee_cases=[],edge_cases=[],heal_cases=[],manager_cases=[])
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','hardware_audio_playback_tested','callbacks_replayed','native_timer_properties_written','health_properties_written'):value[key]=False
    for key in ('controlled_edge_spawn_arrays','owned_actors_destroyed','owned_effects_removed','production_profiles_restored','original_health_unchanged','spawner_default_definition_restored','heal_audio_playing_on_later_native_tick','heal_parent_minimum_five_second_lifetime_and_pool_return'):value[key]=True
    for kind in ('pickup','grenade'):
        for rgba in ([.1,.2,.3,1.],[.8,.5,.2,1.]):
            for profile in ('BlueprintFallback','Python'):value['color_cases'].append(dict(kind=kind,profile=profile,entries=1,native_parent_fx_count=1,color_valid=True,color_after=rgba[:],expected_color=rgba[:]))
    for player in ('local','remote'):
        for profile in ('BlueprintFallback','Python'):value['melee_cases'].append(dict(profile=profile,player_kind=player,entries=1,music_fire_entries=int(player=='local'),intensity_before=.3,intensity_after=.5 if player=='local' else .3))
    for kind,mode in (('pickup','null-first'),('grenade','null-first'),('grenade','wrong-target')):
        for profile in ('BlueprintFallback','Python'):value['edge_cases'].append(dict(kind=kind,profile=profile,mode=mode,entries=1,first_color_unchanged=True,second_color_unchanged=True))
    for repeat in range(2):
        for profile in ('BlueprintFallback','Python'):value['heal_cases'].append(dict(profile=profile,entries=1,native_parent_fx_count=repeat+1,native_audio_playing=True,native_audio_sound=HEAL_SOUND))
    for kind in ('pickup','melee','grenade','heal'):value['manager_cases'].append(dict(kind=kind,profile='Python',entries=1))
    return value


class SmallBurstContractTests(unittest.TestCase):
    def test_complete_native_parent_and_audio_matrix(self):self.assertEqual(validate(report())['real_default_manager_tags'],4)
    def test_real_parent_particle_is_required(self):
        value=report();value['color_cases'][0]['native_parent_fx_count']=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_source_color_including_alpha_is_required(self):
        value=report();value['color_cases'][0]['color_after'][3]=0.
        with self.assertRaises(RuntimeError):validate(value)
    def test_source_melee_strength_is_point_two(self):
        value=report();value['melee_cases'][0]['intensity_after']=.7
        with self.assertRaises(RuntimeError):validate(value)
    def test_remote_player_does_not_trigger_local_music_receiver(self):
        value=report();value['melee_cases'][-1]['music_fire_entries']=1
        with self.assertRaises(RuntimeError):validate(value)
    def test_second_particle_must_remain_untouched(self):
        value=report();value['edge_cases'][0]['second_color_unchanged']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_actual_heal_play_and_retrigger_required(self):
        value=report();value['heal_cases'][-1]['native_audio_playing']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_actual_heal_source_sound_required(self):
        value=report();value['heal_cases'][0]['native_audio_sound']='other-sound'
        with self.assertRaises(RuntimeError):validate(value)
    def test_source_heal_retrigger_keeps_append_only_parent_results(self):
        value=report();value['heal_cases'][-1]['native_parent_fx_count']=1
        with self.assertRaises(RuntimeError):validate(value)
    def test_duplicate_profile_does_not_prove_a_paired_case(self):
        value=report();value['color_cases'][1]['profile']='BlueprintFallback'
        with self.assertRaises(RuntimeError):validate(value)
    def test_native_parent_lifetime_required(self):
        value=report();value['heal_parent_minimum_five_second_lifetime_and_pool_return']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_real_manager_default_python_required(self):
        value=report();value['manager_cases'][0]['profile']='BlueprintFallback'
        with self.assertRaises(RuntimeError):validate(value)
    def test_broad_acceptance_callback_replay_or_health_write_rejected(self):
        for key in ('full_acceptance','hardware_audio_playback_tested','callbacks_replayed','health_properties_written'):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
