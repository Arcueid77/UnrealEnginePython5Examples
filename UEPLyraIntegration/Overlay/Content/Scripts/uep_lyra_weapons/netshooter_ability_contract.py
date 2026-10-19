"""Bounded native input/target-data/no-op/Cue/spawn/montage acceptance gates."""
import argparse
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

PROFILES=("BlueprintFallback","Python")
KINDS=("complete-default","complete-offset","cancel","interrupt","null-montage")
PLAN=tuple((profile,kind) for profile in PROFILES for kind in KINDS)


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native NetShooter ability run failed")
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested",
                "activation_handler_replayed","target_data_callback_replayed","montage_callback_replayed","health_properties_written",
                "ammo_properties_written","projectile_spawn_requested_by_fixture","projectile_physics_accepted"):
        require(report[key] is False,"NetShooter ability scope overclaim: "+key)
    require(len(report["cases"])==len(PLAN) and [(row["profile"],row["kind"]) for row in report["cases"]]==list(PLAN),"native NetShooter input matrix incomplete")
    for row in report["cases"]:
        require(row["native_input_used"] and row["activations"]==1 and row["native_ammo_cost"]==1,"native NetShooter input/commit/cost missing")
        require(row["target_data_entries"]==1 and row["parent_target_data_calls"]==0 and row["parent_fire_timers_or_complete"]==0,"empty child target-data override or unused timer semantics changed")
        require(row["native_firing_cue_entries"]==1 and row["native_cue_geometry_matches"] and row["native_cue_default_fields_match"],"original native NetShooter firing Cue differs")
        require(row["controller_forward_differs_from_camera_forward"] and row["native_location_direction_match"],"original controller-forward/camera-rotation spawn pose differs")
        require(row["native_projectile_spawns"]==1 and row["native_projectile_transform_matches"] and row["native_owner_none_instigator_source"] and row["native_default_exposed_hit"],"native authority projectile defaults/transform differ")
        require(row["projectile_destroyed_by_fixture_before_movement_tick"] and row["native_ability_ended"],"bounded projectile cleanup/native ability end missing")
        expected="OnCancelled" if row["kind"]=="null-montage" else "OnInterrupted" if row["kind"] in ("cancel","interrupt") else "OnCompleted"
        require(row["native_callbacks"]==[expected],"original native montage callback identity/lifetime differs")
        require(row["native_montage_observed"]==(row["kind"]!="null-montage"),"actual native montage did not match input")
    for key in ("native_independent_camera_view_target_fixture","original_view_target_restored","inherited_added_listener_once","original_inventory_restored","original_player_health_unchanged","original_player_pose_control_movement_restored",
                "all_test_actors_destroyed","production_profiles_restored","cue_observer_restored"):
        require(report[key],"NetShooter native cleanup/inheritance missing: "+key)
    return dict(status="passed",native_input_cases=len(PLAN),native_empty_target_data_cases=len(PLAN),native_montage_lifecycle_cases=len(PLAN),full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
