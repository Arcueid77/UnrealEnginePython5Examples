"""Inherited stencil decisions, native clamping/child recursion and old team gate."""
import argparse
import json
from pathlib import Path
from .team_cosmetics_contract import validate as team, require

PAIRS = [(target+"-"+name, target, value, calls) for target in ("owner", "unpossessed")
    for name, value, calls in (("zero", 0, 1), ("team", 7, 1), ("max", 255, 1), ("negative", -1, 1), ("overflow", 256, 1), ("repeat", 42, 3))]
PLAN = [(name, profile, target, value, calls) for name, target, value, calls in PAIRS for profile in ("BlueprintFallback", "Python")]


def check_counts(stats, profile, calls, count, local_player):
    py = profile == "Python"
    require(stats["python_calls"] == (calls if py else 0) and
        stats["fallback_calls"] == (0 if py else calls) and
        stats["component_queries"] == (calls if py else 0) and stats["component_writes"] == (count*calls if py else 0) and
        stats["local_player_zeroes"] == (calls if py and local_player else 0), "selected inherited stencil dispatch/native operations differ")


def validate(report):
    prior = team(report)
    startup = report["natural_startup_stencil_python_dispatch"]
    require(startup["python_calls"] >= 1 and startup["fallback_calls"] == 0 and startup["component_queries"] == startup["python_calls"],
        "natural team startup did not enter inherited Python stencil")
    for row in report["cases"]:
        check_counts(row["stencil_counters"], row["profile"], row["calls"], len(row["actual"]["primitives"]),
            row["locally_controlled"] and row["player_controlled"])
    require(len(report["stencil_cases"]) == len(PLAN), "direct inherited stencil matrix incomplete")
    for row, expected in zip(report["stencil_cases"], PLAN):
        name, profile, target, value, calls = expected
        require((row["name"], row["profile"], row["target"], row["team_id"], row["calls"]) == expected and row["bp_reference_call"] is True,
            "direct inherited stencil call plan differs")
        local_player = row["locally_controlled"] and row["player_controlled"]
        expected_value = 0 if local_player else min(255, max(0, value))
        require(row["components"] and all(item["value"] == expected_value and item["render_custom_depth_unchanged"] is True for item in row["components"]),
            "native stencil clamp/control/render-toggle result differs")
        require(row["child_components"] == (0 if target == "owner" else 1), "actual native ChildActor recursion differs")
        check_counts(row["counters"], profile, calls, len(row["components"]), local_player)
        require(row["native_gc_held_components_and_callers_survived"] is True and row["original_visual_camera_profile_restored"] is True,
            "native stencil GC/original state restore failed")
    for index in range(0, len(PLAN), 2):
        a, b = report["stencil_cases"][index:index+2]
        require(a["components"] == b["components"], "original/Python native stencil components differ")
    require(report["native_child_actor_created_destroyed"] is True and report["native_child_component_recursive_discovery"] is True and
        report["native_fixture_extra_component_created"] is True and report["fixture_actor_replication_disabled"] is True and
        report["stencil_caller_roots_created"] == report["stencil_caller_roots_released"] == 1,
        "native child fixture/extra component/caller lifetime scope differs")
    require(report["parent_bp_asset_modified"] is False and report["whole_parent_class_family_migrated"] is False,
        "inherited stencil pilot cannot claim parent-family migration")
    return dict(prior, native_direct_stencil_pairs=len(PAIRS), native_direct_stencil_bp_calls=sum(row[-1] for row in PLAN),
        native_child_actor_recursion_and_clamping=True, native_case_trials=len(report["cases"])+len(PLAN), full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
