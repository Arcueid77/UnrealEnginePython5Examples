"""Reject missing real entry paths, changed parameters and synthetic cleanup proof."""
import copy
import unittest
from uep_lyra_weapons.footstep_contract import PROFILES, PATHS, CASES, validate


def report():
    value = dict(status="passed", error=None, native_mode="Standalone", cases=[], timer_cases=[])
    for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "pixels_tested", "audio_playback_tested", "timer_properties_written", "latent_callback_replayed", "health_properties_written", "natural_animation_dispatch_tested"): value[key] = False
    for key in ("native_warmup_ready", "all_test_actors_destroyed", "original_pawn_health_unchanged", "production_classes_restored", "diagnostic_probe_unrooted", "materials_unrooted"): value[key] = True
    for profile in PROFILES:
        for path in PATHS:
            for name in CASES:
                state = dict(trigger=True, side=False, surface=0, surface_niagara=0, location=[1.,2.,3.], orientation=[0.,0.,0.,1.], hit="hit")
                before = copy.deepcopy(state)
                if name.startswith("unsupported-"): state["surface"] = 4 if name.endswith("four") else 63
                parameters = {k:copy.deepcopy(state[k]) for k in ("trigger", "side", "location", "orientation")}; parameters["surface"] = 0
                value["cases"].append(dict(profile=profile, path=path, name=name, state=state, before_state=before,
                    parameters=parameters, before_parameters=copy.deepcopy(parameters), input_surface=state["surface"],
                    actual_selected_motion_dispatch=True, stored_mesh_unchanged=True, component_valid=True,
                    same_cached=name not in ("cold", "replace-inactive"), attached_to_root=True, relative_location=[0.,0.,0.], relative_rotation=[0.,0.,0.]))
        value["timer_cases"].append(dict(profile=profile, native_retrigger_observed=True, survived_original_deadline=True,
            destroyed_after_retrigger=True, destroy_elapsed=4.1, valid_inactive_kept_actor_alive=True,
            native_repeat_cleanup_observed=True, destroyed_after_component_removal=True))
    return value


class TestFootstepContract(unittest.TestCase):
    def test_complete_native_matrix(self): self.assertEqual(validate(report())["actual_native_motion_calls"], 64)
    def test_real_blueprint_caller_required(self):
        value = report(); value["cases"] = [r for r in value["cases"] if r["path"] != "blueprint"]
        with self.assertRaises(RuntimeError): validate(value)
    def test_actual_selected_motion_dispatch_required(self):
        value = report(); value["cases"][0]["actual_selected_motion_dispatch"] = False
        with self.assertRaises(RuntimeError): validate(value)
    def test_niagara_quaternion_must_match_actor(self):
        value = report(); value["cases"][0]["parameters"]["orientation"][0] = .5
        with self.assertRaises(RuntimeError): validate(value)
    def test_original_and_python_states_must_match(self):
        value = report(); value["cases"][-2]["state"]["location"][0] = 7.; value["cases"][-2]["parameters"]["location"][0] = 7.
        with self.assertRaises(RuntimeError): validate(value)
    def test_unsupported_surface_cannot_write_niagara(self):
        value = report(); row = next(r for r in value["cases"] if r["name"] == "unsupported-four"); row["parameters"]["trigger"] = False
        with self.assertRaises(RuntimeError): validate(value)
    def test_miss_cannot_write_existing_actor_state(self):
        value = report(); row = next(r for r in value["cases"] if r["name"] == "miss"); row["state"]["hit"] = "other"
        with self.assertRaises(RuntimeError): validate(value)
    def test_valid_inactive_cache_must_retain_actor(self):
        value = report(); value["timer_cases"][0]["valid_inactive_kept_actor_alive"] = False
        with self.assertRaises(RuntimeError): validate(value)
    def test_unrun_natural_animation_or_timer_replay_claim_rejected(self):
        for key in ("natural_animation_dispatch_tested", "latent_callback_replayed", "timer_properties_written"):
            value = report(); value[key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): validate(value)
    def test_provider_restore_and_owned_cleanup_required(self):
        value = report(); value["production_classes_restored"] = False
        with self.assertRaises(RuntimeError): validate(value)
