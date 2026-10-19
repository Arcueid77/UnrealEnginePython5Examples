"""Reject fabricated break/Tick, changed shader semantics or missing parent work."""
import copy
import unittest
from uep_lyra_weapons.physics_field_contract import PLAN,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',pairs=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','break_callbacks_replayed','tick_callbacks_replayed','native_timer_properties_written','health_properties_written','identical_random_physics_fragments_claimed'):r[k]=False
    for k in ('owned_actors_destroyed','original_health_unchanged','production_profiles_restored'):r[k]=True
    for name,controlled,switch in PLAN:
        before=dict(material_valid=[True,True],material_slots_match=True,notify_breaks=True,target=1.,current=0.)
        after=dict(root_broken=True,target=0.,material_slots_match=True)
        evidence=dict(python_construction=1,fallback_construction=0,python_begin=1,fallback_begin=0,python_tick=2 if switch else 0,fallback_tick=2 if switch else 0,last_delta=.016)
        r['pairs'].append(dict(name=name,initial_sphere_begin_entries=[1,1],initial_material_entries=[1,1],natural_samples=4,all_shaders_and_current_glow_unchanged=True,chaos_event_counts=[2,2],chaos_payloads_valid=True,break_handler_counts=[2,2],initial_states=[before,copy.deepcopy(before)],final_states=[after,copy.deepcopy(after)],field_evidence=[evidence,copy.deepcopy(evidence)],profile_switch_observed=switch,parent_trigger_calls=0 if controlled else 2,final_profiles=['Python','BlueprintFallback'] if switch else ['BlueprintFallback','Python']))
    return r


class PhysicsContractTests(unittest.TestCase):
    def test_actual_parent_and_strain_matrix(self):self.assertEqual(validate(report())['native_shatter_actors'],4)
    def test_real_chaos_payload_must_identify_source_component(self):
        r=report();r['pairs'][0]['chaos_payloads_valid']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_disconnected_tick_cannot_be_repaired_in_migration(self):
        r=report();r['pairs'][0]['all_shaders_and_current_glow_unchanged']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_root_must_actually_break(self):
        r=report();r['pairs'][0]['final_states'][0]['root_broken']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_break_target_assignment_must_be_zero(self):
        r=report();r['pairs'][0]['final_states'][0]['target']=1.
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_material_initialization_required(self):
        r=report();r['pairs'][0]['initial_states'][0]['material_slots_match']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_parent_constructor_and_begin_each_run_once(self):
        r=report();r['pairs'][0]['field_evidence'][0]['python_begin']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_live_tick_must_follow_both_profiles(self):
        r=report();r['pairs'][-1]['field_evidence'][0]['fallback_tick']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_live_chaos_callback_follows_profile_switch(self):
        r=report();r['pairs'][-1]['final_profiles']=['BlueprintFallback','Python']
        with self.assertRaises(RuntimeError):validate(r)
    def test_callback_replay_and_broad_acceptance_rejected(self):
        for k in ('break_callbacks_replayed','tick_callbacks_replayed','pixels_tested','identical_random_physics_fragments_claimed'):
            r=report();r[k]=True
            with self.subTest(key=k),self.assertRaises(RuntimeError):validate(r)
