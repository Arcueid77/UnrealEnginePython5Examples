"""Independent native spawn effect, input delay and ownership acceptance gate."""
import argparse
import json
from pathlib import Path

PLAN = ("natural-duration", "montage-interrupt", "native-cancel", "external-native-end", "active-profile-switch", "repeat",
    "zero-input-fraction", "end-input-fraction", "foreign-input-lock", "paused-world-time")


def require(condition, message):
    if not condition: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["original_player_restored"] and
        report["original_ability_specs_restored"] and report["original_fraction_restored"] and report["native_default_on_spawn_observed"],
        "native SpawnEffect baseline/restore failed")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "activation_handler_replayed", "task_callbacks_replayed",
        "health_properties_written", "animation_assets_modified", "original_montage_or_effect_written"):
        require(report[field] is False, "unsupported SpawnEffect claim: "+field)
    require([row["name"] for row in report["cases"]] == list(PLAN), "native SpawnEffect matrix incomplete")
    for row in report["cases"]:
        for side in ("blueprint", "python"):
            value = row[side]
            require(value["native_type_preserved"] and value["effect_at_start"] == 1 and value["immune_at_start"] and
                value["movement_locked_at_start"] and value["native_montage_playing_observed"] and value["native_ability_ended"] and
                value["effects_after_end"] == value["tasks_after_end"] == 0 and value["immune_after_end"] is False and
                value["movement_after_end"] == (row["name"] == "foreign-input-lock") and value["foreign_lock_released_restores_baseline"] and
                value["original_player_restored"] and value["native_type_preserved"] and value["no_late_business_mutation"],
                "native SpawnEffect activation/cleanup/source state differs")
            duration, elapsed = value["montage_length"], value["native_elapsed"]
            early = row["name"] in ("native-cancel", "external-native-end", "active-profile-switch")
            require((elapsed < duration-.5) if early else (duration-.15 <= elapsed < duration+.5), "native spawn completion timing differs")
            if not early and row["name"] != "foreign-input-lock":
                require(value["unlock_elapsed"] is not None and abs(value["unlock_elapsed"]-duration*value["input_fraction"]) < .16,
                    "native spawn fractional movement unlock timing differs")
            require(value["profile_teardown_ended_ability"] == (row["name"] == "active-profile-switch") and
                value["native_pause_observed"] == (row["name"] == "paused-world-time") and
                value["interrupt_left_ability_active"] == (row["name"] == "montage-interrupt"), "spawn native lifetime intervention missing")
        stats = row["python"]["counters"]
        require(stats["activations"] == stats["scopes_created"] == stats["scopes_closed"] == stats["effects_applied"] == stats["effects_removed"] ==
            stats["movement_locks"] == stats["movement_unlocks"] == 1 and stats["tasks_created"] == 3,
            "spawn native scope/effect/input ownership not balanced")
        require(stats["native_ends"] == int(row["name"] != "active-profile-switch"), "spawn native End route differs")
    stats = report["policy_shutdown"]
    require(stats["errors"] == [] and stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"], "SpawnEffect shutdown error/leak")
    if "native_immediate_handoff_tested" in report:
        require(report["native_immediate_handoff_tested"], "immediate BP/Python handoff not tested")
        handoff = report["blueprint_to_python_immediate_handoff"]
        require(handoff["old_activation_ended"] and handoff["new_python_activated"] and handoff["alive_after_old_bp_deadline"] and
            handoff["new_python_enable_requests"] == 2 and handoff["effects_after_end"] == handoff["tasks_after_end"] == 0 and
            handoff["original_player_restored"] and abs(handoff["new_native_elapsed"]-handoff["montage_length"]) < .16 and
            handoff["unlock_elapsed"] is not None and abs(handoff["unlock_elapsed"]-handoff["montage_length"]*handoff["input_fraction"]) < .16,
            "old native Blueprint latent delay affected the new Python activation")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(PLAN), native_default_on_spawn_observed=True,
        native_immediate_handoff_tested=report.get("native_immediate_handoff_tested", False), network_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
