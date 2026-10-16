"""Bounded native alive equipment lifecycle, not animation-system replacement."""
import argparse
import json
from pathlib import Path

PLAN = ("pistol", "rifle", "shotgun", "netshooter")


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["original_player_restored"] and
        report["original_cdo_selectors_restored"] and report["observer_profiles_restored"], "equipment fixture/profile restore incomplete")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "lifecycle_called_by_probe",
        "animation_state_written_by_probe", "animation_assets_modified", "native_cpp_time_written", "death_branch_native_tested"):
        require(report[field] is False, "unsupported equipment claim: "+field)
    require([pair["name"] for pair in report["cases"]] == list(PLAN), "equipment native family matrix incomplete")
    require(report["read_only_profile_observer"] and report["fixture_cdo_profile_selector_written"], "equipment native observer/selector fixture missing")
    if report["gc_stress_tested"]:
        require([row["weapon"] for row in report["native_gc_cases"]] == list(PLAN) and
            all(row["native_proxy_collected"] and row["paused_state_preserved"] and row["before"] == row["after"] for row in report["native_gc_cases"]),
            "native equipment proxy GC/playback proof incomplete")
    for pair in report["cases"]:
        for side in ("blueprint", "python"):
            row = pair[side]
            require(row["native_type_preserved"] and row["native_equipment_item_source_matches"] and row["native_outer_cpp_equip_time_observed"] and
                row["fixture_inventory_restored"] and row["instance_profile_switch_preserved_state"] and
                row["native_equip_callbacks"] == row["native_unequip_callbacks"] == 1, "native equipment lifecycle/source/timing/restore differs")
            for event in ("equip", "unequip"):
                state = row[event]
                require(not state["dead_or_dying"] and state["linked_layer"] == state["selected_layer"] and
                    state["montage_playing"] == (state["montage"] is not None), "native equipment linked layer/montage differs")
        require(all(pair["blueprint"][field] == pair["python"][field] for field in ("equip", "unequip", "native_class")), "original/Python equipment state differs")
        stats = pair["python"]["counters"]
        require(stats["equips"] == stats["unequips"] == stats["tag_queries"] == 1 and stats["layer_picks"] == stats["montage_calls"] == 2,
            "Python native equipment handlers were bypassed")
        original = pair["blueprint"]["counters"]
        require(original["fallback_equips"] == original["fallback_unequips"] == original["fallback_tag_queries"] == 1, "original BP equipment handlers were bypassed")
    require(report["policy_shutdown"]["errors"] == [] and report["policy_shutdown"]["active_count"] == 0 and
        report["policy_shutdown"]["script_subscriptions_created"] == 0, "equipment introduced script observer/subscription leak")
    return dict(status="passed", bounded_runtime_acceptance=True, alive_native_family_pairs=len(PLAN), death_branch_native_tested=False, gc_stress_tested=report["gc_stress_tested"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
