"""ADS input -> camera/speed/mapping/native typed UI contract."""
import argparse
import json
from pathlib import Path

PLAN = ("release-held", "native-cancel", "external-native-end", "active-profile-switch", "repeat-held", "paused-world-time")
NETWORK_PLAN = tuple(name for name in PLAN if name != "paused-world-time")


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report, plan=PLAN):
    require(report["status"] == "passed" and report["error"] is None and report["original_player_restored"] and
        report["original_widget_grant_preserved"] and report["source_observer_closed"], "ADS source/restore/lifetime proof missing")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
        "task_callbacks_replayed", "camera_or_speed_written_by_probe", "mapping_context_written_by_probe", "ui_messages_injected_by_probe"):
        require(report[field] is False, "unsupported ADS claim: "+field)
    require([row["name"] for row in report["cases"]] == list(plan), "ADS native matrix incomplete")
    for row in report["cases"]:
        for side in ("blueprint", "python"):
            value = row[side]
            for field in ("native_type_preserved", "native_camera_while_held", "native_speed_while_held", "native_mapping_priority_11",
                "actual_reticle_ads_on", "actual_reticle_ads_off", "camera_speed_mapping_restored", "widget_grant_preserved", "no_late_callbacks"):
                require(value[field], "ADS native observation missing: "+field)
            require(value["input_injections"] >= 3 and value["wait_tasks_while_held"] == 1 and value["tasks_after_end"] == 0,
                "ADS input/task proof incomplete")
            require(value["source_ui_events"] == [True, False], "actual native ADS source message missing/duplicated")
            if row["name"] == "paused-world-time": require(value["native_pause_observed"], "ADS state changed while paused")
            if row["name"] == "active-profile-switch": require(value["profile_teardown_ended_ability"], "ADS active Profile teardown incomplete")
        stats = row["python"]["counters"]
        require(stats["activations"] == stats["tasks_created"] == stats["scopes_created"] == stats["scopes_closed"] == 1 and
            stats["ui_on"] == stats["ui_off"] == stats["mappings_added"] == stats["mappings_removed"] == 1,
            "ADS policy/cleanup bypass or leak")
        if row["name"] in ("release-held", "repeat-held", "paused-world-time"):
            require(stats["input_releases"] == 1, "native GAS WaitInputRelease callback not observed")
    stats = report["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["helpers_rooted"] == stats["helpers_unrooted"] and
        stats["errors"] == [] and report["source_scopes_created"] == report["source_scopes_closed"] == len(plan)*2, "ADS policy/source/helper shutdown leak")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(plan), native_enhanced_input_tested=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
