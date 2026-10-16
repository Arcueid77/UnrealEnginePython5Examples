"""Native gameplay event/Quickbar/equipment comparison; no hardware claim."""
import argparse
import json
from pathlib import Path

PLAN = (("select-fraction", 0, 1), ("select-negative-fraction", 1, 0), ("select-negative", 0, 0),
        ("select-out-of-range", 0, 0), ("cycle-forward", 0, 1), ("cycle-backward", 0, 2),
        ("forward-wrap", 2, 0), ("unrelated-event", 0, 0), ("native-cancel", 0, 1),
        ("active-profile-switch", 0, 1))


def require(condition, message):
    if not condition: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_gameplay_event_producer"] is True and
            report["native_default_owned_python_scope"] is True and
            report["original_player_restored"] is True and report["original_ability_active_restored"] is True,
            "Quickslot native source/restoration failed")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "hardware_input_tested", "enhanced_input_tested",
                  "python_handler_replayed", "task_callbacks_replayed", "inventory_properties_written", "native_rpc_bypassed"):
        require(report[field] is False, "unsupported Quickslot claim: "+field)
    require([row["name"] for row in report["cases"]] == [name for name, _, _ in PLAN], "Quickslot matrix incomplete")
    for row, (_, _, selected) in zip(report["cases"], PLAN):
        require(row["blueprint"]["inventory"] == row["python"]["inventory"], "native BP/Python selection/equipment differs")
        for side in ("blueprint", "python"):
            actual = row[side]
            require(actual["inventory"]["active"] == selected and actual["inventory"]["equipment_instigator_matches"] and
                    actual["native_type_preserved"] and actual["native_tasks_before"] == 3 and actual["native_tasks_after_end"] == 0 and
                    actual["ended_inactive"] and actual["ended_event_ignored"], "Quickslot task/native result/cleanup missing")
            require(actual["profile_switch_reactivated"] == (row["name"] == "active-profile-switch"), "Quickslot Profile switch missing")
        stats = row["python"]["counters"]
        require(stats["activations"] == stats["scopes_created"] == stats["scopes_closed"] == 1 and stats["tasks_created"] == 3,
                "Python Quickslot did not own three native tasks in one balanced scope")
        require(stats["selects"] == int(row["name"].startswith("select")) and
                stats["backward"] == int(row["name"] == "cycle-backward") and
                stats["forward"] == int(row["name"] in ("cycle-forward", "forward-wrap", "native-cancel")),
                "native event did not reach exactly its matching Python task")
    stats = report["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [],
            "Quickslot shutdown leaked native task delegates")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(PLAN), hardware_input_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
