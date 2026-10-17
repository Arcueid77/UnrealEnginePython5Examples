"""Independent native trace/Health/root-task/Cue matrix gate, not a release gate."""
import argparse
import json
import math
from pathlib import Path
from .melee_hit_montage_contract import require

SCENARIOS = ("miss", "invalid-asc", "friendly", "occluded", "hostile")
PLAN = tuple((name, profile) for name in SCENARIOS for profile in ("BlueprintFallback", "Python"))


def direction_matches_trace(root, trace, original):
    # The original query uses ActorForward*Distance. Derive the independent
    # native facing from its recorded world endpoints, not a fixed world axis.
    expected = [(end-start)/original["Distance"] for start,end in zip(trace["start"],trace["end"])]
    return len(root["direction"]) == len(expected) == 3 and all(math.isclose(actual,wanted,rel_tol=1e-9,abs_tol=1e-9) for actual,wanted in zip(root["direction"],expected))


def validate(report):
    require(report["status"] == "passed" and report["error"] is None, "native trace report failed")
    require(report["actual_granted_primary_instance"] and report["native_role"] == 3 and
        report["request_entry"] == "ASC.TryActivateAbilityByClass", "actual authority ability/ASC entry missing")
    for name in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "health_properties_written",
            "activation_event_replayed", "task_callbacks_replayed", "ability_granted_by_fixture", "quantitative_movement_parity_tested"):
        require(report[name] is False, "trace scope overclaimed: "+name)
    for name in ("profile_restored", "specs_unchanged", "config_unchanged", "native_pose_restored", "fixtures_destroyed", "cue_observer_restored", "observer_scopes_closed"):
        require(report[name] is True, "trace cleanup missing: "+name)
    require(report["native_control_restoration"]["control_rotation"] and report["observation_errors"] == [] and
        report["shutdown"]["active_count"] == 0 and report["shutdown"]["errors"] == [] and
        report["shutdown"]["scopes_created"] == report["shutdown"]["scopes_closed"], "native trace lifetime/observer failure")
    require(len(report["cases"]) == len(PLAN), "native trace matrix incomplete")
    for index, row in enumerate(report["cases"]):
        scenario, profile = PLAN[index]; applied = scenario == "hostile"; python = profile == "Python"
        require((row["index"], row["scenario"], row["profile"]) == (index, scenario, profile), "trace matrix identity differs")
        for name in ("native_request_accepted", "native_active_observed", "native_montage_task_observed", "native_ended", "actual_scope_closed", "foreign_health_unchanged", "specs_unchanged", "config_unchanged"):
            require(row[name] is True, "native trace observation missing: "+name)
        require(row["native_tasks_after"] == 0 and row["quiet_ticks"] >= 20 and row["health_events_quiet"], "trace End/quiet cleanup failed")
        trace = row["preflight"]
        require(trace["hit"] == (scenario != "miss"), "real capsule hit/miss fixture differs")
        if scenario != "miss":
            require(trace["target"] == row["target"] and trace["target_asc_valid"] == (scenario != "invalid-asc"), "native target/ASC fixture differs")
        if scenario in ("friendly", "occluded", "hostile"):
            require(trace["team_comparison"] == (0 if scenario == "friendly" else 1), "native team fixture differs")
        if scenario in ("occluded", "hostile"):
            require(trace["occluded"] == (scenario == "occluded"), "real line-trace occlusion fixture differs")
        counts = row["trace_stats"]
        expected = dict(queries=int(python), fallback_queries=int(not python), misses=int(python and scenario == "miss"),
            invalid_asc=int(python and scenario == "invalid-asc"), nondifferent_team=int(python and scenario == "friendly"),
            occluded=int(python and scenario == "occluded"), root_tasks=int(python and applied), effects=int(python and applied), cues=int(python and applied))
        require(counts == expected, "Python/native fallback branch ownership differs")
        require(len(row["root_tasks"]) == int(applied) and len(row["cues"]) == int(applied), "native root task/Cue count differs")
        if not applied:
            require(row["health_delta"] == 0 and row["health_events"] == [], "rejected trace damaged target")
        else:
            require(row["health_delta"] > 0 and len(row["health_events"]) == 1, "real native target Health damage missing/duplicate")
            event = row["health_events"][0]
            require(event["target"] == row["target"] and math.isclose(event["old"]-event["new"], row["health_delta"], abs_tol=1e-5), "native Health delegate does not match damage")
            root = row["root_tasks"][0]; original = row["original_config"]
            require(direction_matches_trace(root, trace, original) and root["additive"] and root["gravity"] and root["finish_mode"] == 0 and root["curve"] is None and
                math.isclose(root["duration"], original["Duration"], abs_tol=1e-6) and root["finish_velocity"] == [0., 0., 0.] and root["clamp"] == 1000., "native root-motion original options differ")
            require(math.isclose(root["strength"], original["Strength"]*trace["distance"]/original["Distance"], abs_tol=.01), "native unclamped hit-distance strength differs")
            context = row["stored_effect_context"]
            require(context["valid"] and context["has_hit"] and context["hit_actor"] is None and not context["blocking"] and context["distance"] == 0., "original empty hit context was replaced")
            cue = row["cues"][0]
            require(cue["target"] == row["source"] and cue["original"] == "GameplayCue.Weapon.Melee.Hit" and
                cue["location"] == [0., 0., 0.] and cue["normal"] == [0., 0., 0.] and cue["source"] is None and
                cue["normalized"] == cue["raw"] == 0. and cue["effect_level"] == cue["ability_level"] == 1, "original owner/default Cue changed")
    for scenario in SCENARIOS:
        bp, py = [row for row in report["cases"] if row["scenario"] == scenario]
        require(bp["health_delta"] == py["health_delta"] and len(bp["root_tasks"]) == len(py["root_tasks"]) and len(bp["cues"]) == len(py["cues"]), "native BP/Python business outcomes differ")
    return dict(status="passed", native_trace_trials=len(PLAN), real_hostile_damage_compared=True,
        invalid_asc_friendly_occlusion_miss_compared=True, native_root_task_and_cue_observed=True,
        network_acceptance=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True); args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
