"""Hero Heal native task/effect/input/movement contract, not legacy pickup Heal."""
import argparse
import json
from pathlib import Path

PLAN = ("original-montage", "native-input-press", "native-cancel", "native-interrupt",
        "external-native-end", "active-profile-switch", "native-state-end", "paused-world-time")
NETWORK_PLAN = tuple(name for name in PLAN if name != "paused-world-time")


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report, plan=PLAN, network=False):
    require(report["status"] == "passed" and report["error"] is None and report["original_player_restored"] and
        report["original_ability_specs_restored"] and report["fixture_native_asc_grant_activate_and_input_api"], "Hero Heal fixture/restore incomplete")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_or_enhanced_input_tested",
        "activation_handler_replayed", "task_callbacks_replayed", "health_properties_written", "animation_assets_modified", "original_montage_or_effect_written"):
        require(report[field] is False, "unsupported Hero Heal claim: "+field)
    require([row["name"] for row in report["cases"]] == list(plan), "Hero Heal matrix incomplete")
    for row in report["cases"]:
        name = row["name"]
        for side in ("blueprint", "python"):
            value = row[side]
            require(value["native_type_preserved"] and value["native_tasks_at_start"] == 3 and value["movement_locked_at_start"] and
                value["original_montage_playing_observed"] and value["tasks_after_end"] == 0 and value["native_ability_ended"] and
                value["movement_unlocked_after_end"] and value["native_montage_stopped"] and value["native_heal_effects_restored"] and
                value["no_late_callbacks"] and value["fixture_health_restored"], "Hero Heal native task/effect/movement cleanup missing")
            require(value["health_after"] > value["health_before"] and value["health_after"] <= value["max_health"], "original native GE did not heal")
            if name == "native-input-press": require(value["native_input_press_sent"], "native GAS input press not delivered")
            if name == "active-profile-switch": require(value["profile_teardown_ended_ability"], "active Hero Heal Profile teardown missing")
            if name == "native-state-end":
                require(value["native_state_end_released_movement_while_active"], "native local state callback did not unlock while ability active")
                if network:
                    require(value["authority_health_confirmed"] and value["native_heal_effects_restored"], "native authoritative GE removal did not replicate after local state end")
                else: require(value["native_state_end_released_effects_while_active"], "standalone state callback did not release effect while active")
            if name == "paused-world-time": require(value["native_pause_observed"], "native montage/state advanced while paused")
        for key in ("health_before", "health_after", "native_tasks_at_start", "tasks_after_end", "native_heal_effects_restored"):
            require(row["blueprint"][key] == row["python"][key], "Hero Heal original/Python outcome differs: "+key)
        stats = row["python"]["counters"]
        require(stats["activations"] == stats["effects_applied"] == stats["movement_locks"] == stats["movement_unlocks"] == 1 and
            stats["tasks_created"] == 3 and stats["scopes_created"] == stats["scopes_closed"] == 1, "Hero Heal policy bypass or scope leak")
        reason = {"original-montage": "montage_blends", "paused-world-time": "montage_blends", "native-input-press": "input_presses", "native-state-end": "state_ends"}.get(name)
        if reason: require(stats[reason] == 1, "native Hero Heal callback missing: "+reason)
    stats = report["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [], "Hero Heal shutdown scope leak")
    if not network:
        require([row["name"] for row in report["foreign_lock_regressions"]] == ["montage-end", "state-end", "profile-teardown"], "Python foreign-input-lock native regression missing")
        for row in report["foreign_lock_regressions"]:
            require(row["external_lock_added_with_native_api"] and row["external_lock_preserved_after_native_end"] and
                row["external_lock_released_once_restores_baseline"] and row["tasks_after_end"] == row["effects_after_end"] == 0 and
                row["health_after"] > 75. and row["no_late_callbacks"], "Python consumed foreign movement lock or leaked native work")
            if row["name"] == "state-end": require(row["state_cleanup_preserved_external_lock"], "state cleanup consumed foreign movement lock")
            require(row["counters"]["movement_locks"] == row["counters"]["movement_unlocks"] == 1 and
                row["counters"]["scopes_created"] == row["counters"]["scopes_closed"] == 1, "foreign-lock regression ownership imbalance")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(plan), network_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
