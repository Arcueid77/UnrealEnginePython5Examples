"""Counterexample models, not native trace/GAS evidence."""
import copy
from pathlib import Path
import unittest
from uep_lyra_abilities.melee_trace_contract import PLAN, validate


def example():
    rows = []
    for index, (scenario, profile) in enumerate(PLAN):
        python = profile == "Python"; applied = scenario == "hostile"
        trace = dict(hit=scenario != "miss", target=None if scenario == "miss" else "target", target_asc_valid=scenario != "invalid-asc", distance=100.,
            start=[0.,0.,0.], end=[350.,0.,0.],
            team_comparison=0 if scenario == "friendly" else 1, occluded=scenario == "occluded")
        root = dict(direction=[1., 0., 0.], strength=2200.*100./350., duration=.05, additive=True, gravity=True, finish_mode=0,
            curve=None, finish_velocity=[0., 0., 0.], clamp=1000.)
        cue = dict(target="source", original="GameplayCue.Weapon.Melee.Hit", location=[0., 0., 0.], normal=[0., 0., 0.], source=None,
            normalized=0., raw=0., effect_level=1, ability_level=1)
        rows.append(dict(index=index, scenario=scenario, profile=profile, source="source", target=None if scenario == "miss" else "target", preflight=trace,
            native_request_accepted=True, native_active_observed=True, native_montage_task_observed=True, native_ended=True, actual_scope_closed=True,
            foreign_health_unchanged=True, specs_unchanged=True, config_unchanged=True, native_tasks_after=0, quiet_ticks=20, health_events_quiet=True,
            trace_stats=dict(queries=int(python), fallback_queries=int(not python), misses=int(python and scenario == "miss"),
                invalid_asc=int(python and scenario == "invalid-asc"), nondifferent_team=int(python and scenario == "friendly"),
                occluded=int(python and scenario == "occluded"), root_tasks=int(python and applied), effects=int(python and applied), cues=int(python and applied)),
            root_tasks=[root] if applied else [], cues=[cue] if applied else [], health_delta=50. if applied else 0.,
            health_events=[dict(target="target", old=100., new=50.)] if applied else [],
            original_config=dict(Strength=2200., Duration=.05, Distance=350.),
            stored_effect_context=dict(valid=True, has_hit=True, hit_actor=None, blocking=False, distance=0.)))
    result = dict(status="passed", error=None, actual_granted_primary_instance=True, native_role=3, request_entry="ASC.TryActivateAbilityByClass",
        cases=rows, native_control_restoration=dict(control_rotation=True), observation_errors=[],
        shutdown=dict(active_count=0, errors=[], scopes_created=5, scopes_closed=5))
    result.update({name: False for name in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "health_properties_written",
        "activation_event_replayed", "task_callbacks_replayed", "ability_granted_by_fixture", "quantitative_movement_parity_tested")})
    result.update({name: True for name in ("profile_restored", "specs_unchanged", "config_unchanged", "native_pose_restored", "fixtures_destroyed", "cue_observer_restored", "observer_scopes_closed")})
    return result


class TestMeleeTraceContract(unittest.TestCase):
    def setUp(self): self.report = example()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError)): validate(self.report)
    def test_complete_model(self): self.assertEqual(validate(self.report)["native_trace_trials"], 10)
    def test_missing_trial(self): self.report["cases"].pop(); self.reject()
    def test_unreal_role_not_authority(self): self.report["native_role"] = 2; self.reject()
    def test_fabricated_activation(self): self.report["activation_event_replayed"] = True; self.reject()
    def test_health_written(self): self.report["health_properties_written"] = True; self.reject()
    def test_false_network_claim(self): self.report["network_acceptance"] = True; self.reject()
    def test_scope_leak(self): self.report["shutdown"]["scopes_closed"] = 4; self.reject()
    def test_cue_observer_not_restored(self): self.report["cue_observer_restored"] = False; self.reject()
    def test_miss_incorrect_target(self): self.report["cases"][0]["preflight"]["hit"] = True; self.reject()
    def test_invalid_asc_accepted(self): self.report["cases"][2]["preflight"]["target_asc_valid"] = True; self.reject()
    def test_friendly_is_hostile(self): self.report["cases"][4]["preflight"]["team_comparison"] = 1; self.reject()
    def test_occlusion_not_observed(self): self.report["cases"][6]["preflight"]["occluded"] = False; self.reject()
    def test_original_fallthrough(self): self.report["cases"][-1]["trace_stats"]["fallback_queries"] = 1; self.reject()
    def test_rejected_target_damage(self): self.report["cases"][4]["health_delta"] = 50.; self.reject()
    def test_no_hostile_damage(self): self.report["cases"][-1]["health_delta"] = 0.; self.reject()
    def test_health_delegate_missing(self): self.report["cases"][-1]["health_events"] = []; self.reject()
    def test_native_root_missing(self): self.report["cases"][-1]["root_tasks"] = []; self.reject()
    def test_native_root_wrong_strength(self): self.report["cases"][-1]["root_tasks"][0]["strength"] = 2200.; self.reject()
    def test_native_root_follows_actual_rotated_trace(self):
        for row in self.report["cases"][-2:]:
            row["preflight"]["end"]=[0.,350.,0.]; row["root_tasks"][0]["direction"]=[0.,1.,0.]
        self.assertEqual(validate(self.report)["status"],"passed")
    def test_world_x_is_not_actual_actor_facing(self):
        self.report["cases"][-1]["preflight"]["end"]=[0.,350.,0.]; self.reject()
    def test_real_small_actor_yaw_not_clamped_to_world_axis(self):
        for row in self.report["cases"][-2:]:
            row["preflight"]["start"]=[200000.,200000.,2100.]
            row["preflight"]["end"]=[200349.99999999726,200000.001386664,2100.]
            row["root_tasks"][0]["direction"]=[.9999999999921517,3.9618970923982785e-6,0.]
        self.assertEqual(validate(self.report)["status"],"passed")
    def test_native_root_wrong_finish(self): self.report["cases"][-1]["root_tasks"][0]["finish_mode"] = 2; self.reject()
    def test_native_root_wrong_gravity(self): self.report["cases"][-1]["root_tasks"][0]["gravity"] = False; self.reject()
    def test_copied_real_hit_context(self): self.report["cases"][-1]["stored_effect_context"]["hit_actor"] = "target"; self.reject()
    def test_native_cue_missing(self): self.report["cases"][-1]["cues"] = []; self.reject()
    def test_cue_on_target(self): self.report["cases"][-1]["cues"][0]["target"] = "target"; self.reject()
    def test_cue_hit_point_invented(self): self.report["cases"][-1]["cues"][0]["location"] = [1., 0., 0.]; self.reject()
    def test_different_bp_python_damage(self):
        row = self.report["cases"][-1]; row["health_delta"] = 40.; row["health_events"][0]["new"] = 60.; self.reject()
    def test_foreign_health_changed(self): self.report["cases"][-1]["foreign_health_unchanged"] = False; self.reject()
    def test_late_health_event(self): self.report["cases"][-1]["health_events_quiet"] = False; self.reject()
    def test_generator_retains_original_trace(self):
        text = (Path(__file__).resolve().parents[1]/"Tools/generate_melee_trace_assets.py").read_text(encoding="utf-8")
        self.assertIn('connect(authority, "True", call, "execute")', text)
        self.assertIn('trace.node_find_pin("then").get_linked_to()', text)
        self.assertIn('if call.node_find_pin("then").get_linked_to()', text)
    def test_bare_fixture_has_native_root(self):
        text = (Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/melee_trace_validation.py").read_text(encoding="utf-8")
        self.assertIn('box = actor.add_actor_root_component(ue.find_class("BoxComponent"), label)', text)
    def test_cue_observer_uses_native_hit_asset_not_impact_asset(self):
        text = (Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/melee_trace_validation.py").read_text(encoding="utf-8")
        self.assertIn('CUE = "/ShooterCore/GameplayCues/GCN_Weapon_Melee.GCN_Weapon_Melee_C"', text)


if __name__ == "__main__": unittest.main()
