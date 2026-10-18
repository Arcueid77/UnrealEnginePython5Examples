"""Reject incomplete/overclaimed explosion evidence and unequal native damage."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("grenade_detonate_contract", Path(__file__).resolve().parents[1]/
    "Overlay/Content/Scripts/uep_lyra_weapons/grenade_detonate_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def report():
    data = dict(status="passed", error=None, native_mode="Standalone", production_classes_restored=True,
                test_actors_destroyed=True, view_target_restored=True, observation_errors=[], cases=[])
    data.update({name: False for name in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested",
        "health_properties_written", "rpc_function_overridden", "body_callback_replayed", "particle_completion_replayed", "audio_playback_tested", "quantitative_flight_tested")})
    for name, profile in contract.PLAN:
        data["cases"].append(dict(name=name, profile=profile, **{"class": contract.CLASS}, body_calls=1, repeat_body_calls=1,
            rpc_flags_preserved=True, hidden=True, movement_active=False, native_role=3, actor_destroyed=True, native_trail_valid=True,
            stats=dict(python_bodies=int(profile == "Python"), fallback_bodies=int(profile == "BlueprintFallback"), cues=1, overlaps=1, trail_bindings=1, traces=0 if name.startswith("empty") else 1),
            team_comparison=1, health_before=100., health_after=50. if name in ("enemy-rpc", "enemy-hit") else 100., all_health_unchanged=True,
            trigger="native-actor-timer" if name == "empty-fuse" else "native-blocking-sweep" if name == "enemy-hit" else "original-reliable-rpc", rpc_requested_by_fixture=name not in ("empty-fuse", "enemy-hit"),
            victim="victim", other_pawn_health_unchanged=True, native_overlap_pawns_before=[] if name.startswith("empty") else ["victim"],
            controlled_native_niagara_completion=True, native_trail_active_before_rpc=True, native_finish_callbacks=["trail"], finished_component="trail",
            context_hit=dict(actor="wall" if name == "occluded-rpc" else "victim", distance=30.), expected_hit_actor="wall" if name == "occluded-rpc" else "victim",
            fuse_seconds=2., body_elapsed=2.01, native_hits=1, hit_other_is_target=True, fuse_before_hit=True, fuse_after_hit=False))
    return data


class TestGrenadeDetonateContract(unittest.TestCase):
    def setUp(self): self.data = report()
    def rejected(self):
        with self.assertRaises(RuntimeError): contract.validate(self.data)
    def test_valid_bounded_report(self): self.assertEqual(contract.validate(self.data)["native_explosion_trials"], 12)
    def test_missing_pair(self): self.data["cases"].pop(); self.rejected()
    def test_rpc_repeated_body(self): self.data["cases"][1]["repeat_body_calls"] = 2; self.rejected()
    def test_native_damage_missing_despite_model_effect(self): self.data["cases"][3]["health_after"] = 100.; self.rejected()
    def test_original_python_damage_diverges(self): self.data["cases"][3]["health_after"] = 55.; self.rejected()
    def test_occluder_control_damages_pawn(self): self.data["cases"][4]["health_after"] = 80.; self.rejected()
    def test_direct_rpc_not_natural_fuse(self): self.data["cases"][8]["rpc_requested_by_fixture"] = True; self.rejected()
    def test_timer_fires_early(self): self.data["cases"][9]["body_elapsed"] = 1.; self.rejected()
    def test_native_hit_does_not_cancel_fuse(self): self.data["cases"][11]["fuse_after_hit"] = True; self.rejected()
    def test_network_overclaim(self): self.data["network_acceptance"] = True; self.rejected()
    def test_missing_observer_restore(self): self.data["production_classes_restored"] = False; self.rejected()
    def test_previous_target_still_in_empty_blast(self): self.data["cases"][8]["native_overlap_pawns_before"] = ["previous-target"]; self.rejected()
    def test_unintended_pawn_damaged(self): self.data["cases"][3]["other_pawn_health_unchanged"] = False; self.rejected()
    def test_wrong_native_hit_context(self): self.data["cases"][5]["context_hit"]["actor"] = "victim"; self.rejected()
    def test_missing_native_finished_delegate(self): self.data["cases"][1]["native_finish_callbacks"] = []; self.rejected()
    def test_niagara_never_activated(self): self.data["cases"][1]["native_trail_active_before_rpc"] = False; self.rejected()
