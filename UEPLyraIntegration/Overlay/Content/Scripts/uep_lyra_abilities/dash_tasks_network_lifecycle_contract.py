"""Native two-owner early cancellation/rebind and replicated cleanup, no replay."""
import argparse
import copy
import json
from pathlib import Path
from . import dash_activation_contract as activation
from .dash_tasks_contract import shutdown, compare_cues
from .dash_rpc_input_contract import require, client as rpc_client
from .dash_local_direction_contract import local_row


def tasks(value, owner, switched=False):
    data = value["task_business"]; counts = data["stats"]; python = value["profile"] == "Python"
    require(data["actual_task_scope_closed"] and data["observer_errors"] == [] and len(data["ui"]) == 1 and
        data["ui"][0]["instigator"] == data["target"] and abs(data["ui"][0]["duration"]-data["ui"][0]["native_cooldown"]) <= .0001,
        "native early-end task/UI/scope proof missing")
    require(len(data["cues"]) == int(owner), "native owner Cue delivery missing/duplicated")
    expected = dict(task_starts=int(python), fallback_task_starts=int(not python), montage_tasks=int(python), root_tasks=int(python),
        root_finished=0, native_delays_started=0, delay_completed=0, fallback_delay_completed=0,
        cues=int(python and not owner), ui_messages=int(python), scopes_created=int(python), scopes_closed=int(python),
        native_ends=int(python and not (owner and switched)), fallback_native_ends=int(not python and not (owner and switched)), remote_commits=int(python and not owner))
    require(all(counts.get(key, 0) == count for key, count in expected.items()), "native early-end task/callback ownership differs")
    interrupted, cancelled = counts.get("montage_interrupted", 0), counts.get("montage_cancelled", 0)
    require(interrupted in (0, 1) and cancelled in (0, 1) and interrupted+cancelled == int(python and not switched),
        "native early-end montage event missing/duplicated")


def client(report):
    base = copy.deepcopy(report); base["dash_task_business_migrated"] = False
    rpc_client(base); shutdown(report)
    require(report["network_lifecycle_interventions"] is True, "network lifecycle lane missing")
    for value in report["cases"]:
        local_row(value, require_changed=value["profile"] == "Python"); activation.activation_row(value, True, False)
        action = value["network_lifecycle"]; switched = value["index"]%2 == 1
        require(action["authority_ready_observed"] and action["active_before"] and action["root_before"] and action["montage_before"] and
            action["active_after"] is False and action["quiet_unchanged"] and .07 <= action["elapsed"] < .25,
            "real active owner intervention/authority barrier missing")
        require(action["native_entry"] == ("ue.set_mixin_profile" if switched else "GameplayAbility.K2_CancelAbility"), "wrong native owner intervention")
        if switched: require(action["new_profile"] != value["profile"], "native owner Profile did not change")
        tasks(value, True, switched)
    for name in ("forward", "left"):
        bp, py = [next(value for value in report["cases"] if (value["name"], value["profile"]) == (name, profile)) for profile in ("BlueprintFallback", "Python")]
        compare_cues(bp["task_business"]["cues"], py["task_business"]["cues"])


def validate(reports):
    base = copy.deepcopy(reports)
    for peer in ("A", "B0"): base[peer]["dash_task_business_migrated"] = False
    activation.network(base)
    for peer in ("A", "B0"): client(reports[peer])
    shutdown(reports["server"])
    require(reports["server"]["network_lifecycle_interventions"] is True, "authority lifecycle lane missing")
    for value in reports["server"]["cases"]:
        require(value["authority_ready_sent"] is True, "owner intervention preceded actual authority RPC/tasks")
        tasks(value, False, switched=value["index"]%2 == 1)
    return dict(status="passed", actual_native_two_owner_interventions=8, original_python_cancel_and_active_profile_switch_tested=True,
        native_replicated_task_scope_cleanup_tested=True, network_pause_travel_rejoin_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); args = parser.parse_args(); root = Path(args.directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
