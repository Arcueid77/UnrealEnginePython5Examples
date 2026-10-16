"""Pressed-widget original/Python orchestration and precise lifetime gate."""
import argparse
import json
from pathlib import Path
from .widget_pressed_context_contract import CLASSES, WIDGETS, require

PLAN = ("native-close", "native-cancel", "external-native-end", "active-profile-switch", "repeat-open",
        "inactive-profile-switch", "paused-world-time")
NETWORK_PLAN = tuple(name for name in PLAN if name != "paused-world-time")
TARGETS = ("inventory", "map")
FALSE_CLAIMS = ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested",
    "activation_handler_replayed", "task_callbacks_replayed", "widget_class_written", "widgets_created_by_probe",
    "input_filter_tokens_directly_observed", "widget_pixel_text_parity_tested", "ui_widget_business_migrated",
    "cold_disk_io_claimed", "native_ui_destroyed_claimed", "localonly_authority_activation_claimed")


def validate(report, plan=PLAN, extras=True):
    require(report["status"] == "passed" and report["error"] is None, "pressed-widget native report failed")
    for field in FALSE_CLAIMS: require(report[field] is False, "unsupported pressed-widget claim: " + field)
    for field in ("original_specs_restored", "original_profiles_restored", "original_cdos_preserved", "native_layer_restored", "fixture_observers_closed"):
        require(report[field] is True, "pressed-widget restoration/lifetime missing: " + field)
    require([(row["target"], row["name"]) for row in report["cases"]] == [(target, name) for target in TARGETS for name in plan],
            "pressed-widget native matrix incomplete")
    for pair in report["cases"]:
        for side in ("blueprint", "python"):
            row = pair[side]
            for field in ("native_type_preserved", "profile_selected", "original_config_preserved", "native_widget_active", "native_widget_owner",
                "native_original_layer", "release_kept_ui", "native_ability_ended", "layer_restored", "specs_preserved", "foreign_listener_preserved", "no_late_callbacks"):
                require(row[field] is True, "pressed-widget native observation missing: " + field)
            require(row["widget_class"] == WIDGETS[pair["target"]] and row["native_tasks_during"] == row["native_tasks_after"] == 0 and
                    row["input_injections"] == 1 and row["native_instance_count"] == 2 and row["foreign_native_events"] >= 1,
                    "pressed-widget native input/duplicate grant/no-task/UI proof incomplete")
            if pair["name"] in ("native-cancel", "external-native-end", "inactive-profile-switch"):
                require(row["ordinary_end_preserved_native_ui"], "ordinary End must not deactivate UI-owned panel")
            if pair["name"] == "active-profile-switch": require(row["profile_teardown_ended_all"], "pressed-widget active handoff did not native-End")
            if pair["name"] == "inactive-profile-switch": require(row["inactive_handoff_kept_ui"], "inactive handoff deactivated UI with no ownership claim")
            if pair["name"] == "paused-world-time": require(row["native_pause_observed"] and row["native_ui_active_during_pause"], "pressed-widget UI should survive game-clock pause")
        stats = pair["python"]["counters"]
        require(stats["activations"] == stats["pushes_requested"] == stats["widgets_pushed"] == 2 and stats["fallback_activations"] == 0 and
                stats["scopes_created"] == stats["scopes_closed"] == 4, "pressed-widget Python bypass/duplicate/leak")
        require(pair["blueprint"]["counters"]["fallback_activations"] == 2 and pair["blueprint"]["counters"]["activations"] == 0,
                "pressed-widget baseline did not use two existing original-BP grants")
    if extras:
        require([(row["target"], row["name"]) for row in report["pending_regressions"]] ==
                [(target, name) for target in TARGETS for name in ("cancel-pending", "profile-switch-pending", "other-spec-pending")], "pressed pending matrix incomplete")
        for row in report["pending_regressions"]:
            for field in ("native_pending_observed", "native_pending_proxy_collected", "native_scopes_balanced", "native_layer_restored", "native_abilities_ended", "no_late_callbacks"):
                require(row[field], "pressed pending native lifetime missing: " + field)
            require(row["native_asc_handle_activation_fixture"] and row["bp_parity_claimed"] is False, "pending safety fixture is not original-BP parity")
        require([(row["target"], row["order"]) for row in report["mixed_profiles"]] == [(target, order) for target in TARGETS for order in (0, 1)], "same-BP mixed-Profile matrix incomplete")
        for row in report["mixed_profiles"]:
            require(row["native_asc_handle_activation_fixture"] and row["profiles_independent"] and row["native_type_preserved"] and
                    row["native_ui_observed"] and row["native_layer_restored"] and row["scopes_balanced"], "same-BP instance Profile isolation missing")
            require(row["counters"]["activations"] == row["counters"]["fallback_activations"] == 1, "mixed-Profile activation source differs")
    else:
        require(report["pending_regressions"] == report["mixed_profiles"] == [], "network did not run standalone extras")
    stats = report["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [] and
            report["fixture_scopes_created"] == report["fixture_scopes_closed"] == len(TARGETS) * len(plan) * 2,
            "pressed-widget policy/fixture shutdown leak")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(TARGETS) * len(plan),
                pending_regressions=len(report["pending_regressions"]), mixed_profile_cases=len(report["mixed_profiles"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
