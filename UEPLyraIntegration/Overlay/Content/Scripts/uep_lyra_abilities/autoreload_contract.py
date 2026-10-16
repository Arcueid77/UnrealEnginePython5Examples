"""Native ammo predicates and real input -> original/Python auto-reload proof."""
import argparse
import json
from pathlib import Path

PLAN = ("nonempty", "empty-no-spare", "empty-spare", "real-fire-auto-reload", "native-cancel", "active-profile-switch")


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_default_python_loop_owned"] and
        report["original_player_restored"] and report["original_ability_active_restored"], "native AutoReload fixture/default/restore failed")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "ammo_properties_written", "activation_handler_replayed",
                  "task_callbacks_replayed", "reload_handler_called_by_probe", "poll_interval_or_idle_threshold_written"):
        require(report[field] is False, "unsupported AutoReload claim: "+field)
    require(report["fixture_native_inventory_api_used"] and [row["name"] for row in report["cases"]] == list(PLAN), "native AutoReload matrix incomplete")
    for row in report["cases"]:
        for side in ("blueprint", "python"):
            value = row[side]
            require(value["native_type_preserved"] and value["native_equipment_item_source_matches"] and value["tasks_at_start"] == 1 and
                value["tasks_after_end"] == 0 and value["no_callbacks_after_end"] and value["fixture_ammo_restored"], "native AutoReload type/source/task cleanup missing")
            require(value["ammo_check"] == (row["name"] == "empty-spare"), "native public ammo predicate differs")
            if row["name"] in ("empty-spare", "real-fire-auto-reload"):
                require(value["reload_event_deliveries"] == 1 and value["native_reload_active_observed"] and value["native_reload_tag_observed"] and
                    value["final_magazine"] == value["magazine_capacity"] and value["ammo_conserved"], "native automatic event/reload completion missing or duplicated")
            else: require(value["reload_event_deliveries"] == 0, "ineligible/canceled AutoReload requested a reload")
            if row["name"] == "real-fire-auto-reload":
                require(value["real_fire_rounds"] == value["magazine_capacity"] and value["native_input_injections"] > 2 and
                    value["ammo_api_calls_after_firing_began"] == 0, "real fire-to-empty was replaced by ammo fixture writes")
            if row["name"] == "active-profile-switch": require(value["profile_teardown_ended_native_ability"], "active AutoReload Profile teardown missing")
        require(row["blueprint"]["final_magazine"] == row["python"]["final_magazine"] and
            row["blueprint"]["final_spare"] == row["python"]["final_spare"], "original/Python native ammo outcomes differ")
        stats = row["python"]["counters"]
        require(stats["activations"] == 1 and stats["polls"] >= 1 and stats["scopes_created"] == stats["scopes_closed"] and
            stats["reload_requests"] == int(row["name"] in ("empty-spare", "real-fire-auto-reload")), "AutoReload per-instance policy/scope count differs")
    stats = report["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [] and
        report["observer_scopes_created"] == report["observer_scopes_closed"] == len(PLAN)*2, "AutoReload native observer/policy leak")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(PLAN), real_fire_to_empty_tested=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
