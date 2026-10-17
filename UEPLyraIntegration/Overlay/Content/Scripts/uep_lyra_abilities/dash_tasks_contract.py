"""Previous input/activation gates plus actual native producers and task-scope closure."""
import argparse
import copy
import json
import math
from pathlib import Path
from . import dash_activation_contract as activation
from .dash_local_direction_contract import local_row, close_vector
from .dash_rpc_input_contract import require, client as rpc_client


def shutdown(report):
    require(report["dash_task_business_migrated"] is True and report["task_callbacks_replayed"] is report["cue_or_ui_producer_replayed"] is False and
        report["original_kismet_delay_retained"] is True, "native task/Cue/UI origin/scope missing")
    scopes, observer = report["task_shutdown"], report["producer_shutdown"]
    require(scopes["active_count"] == 0 and scopes["scopes_created"] == scopes["scopes_closed"] and scopes["errors"] == [] and
        observer["scope_closed"] and observer["cue_function_restored"] and observer["errors"] == [], "task or producer-observer lifetime leaked")


def row(value, zero=False, authority=True, remote=False, target=None, replicated_end=False):
    data = value["task_business"]; counts = data["stats"]; python = value["profile"] == "Python"
    require(data["target"] == target and data["observer_errors"] == [] and data["actual_task_scope_closed"] is True, "native callback/producer/scope failure")
    expected = dict(task_starts=int(python and not zero), fallback_task_starts=int(not python and not zero),
        montage_tasks=int(python and not zero), root_tasks=int(python and not zero), root_finished=int(python and not zero),
        native_delays_started=int(python and not zero), delay_completed=int(python and not zero), fallback_delay_completed=int(not python and not zero),
        cues=int(python and not zero and authority), ui_messages=int(python and not zero),
        montage_interrupted=0, montage_cancelled=0, native_ends=int(python), fallback_native_ends=int(not python),
        remote_commits=int(python and remote), scopes_created=int(python and not zero), scopes_closed=int(python and not zero))
    if replicated_end and not zero:
        # Native End replication can win against the other world's latent
        # action; GameplayAbility::EndAbility removes that pending action.
        # The complete network gate below still requires a real completion
        # in at least one world, rather than accepting two silent ends.
        selected = "delay_completed" if python else "fallback_delay_completed"
        require(counts.get(selected, 0) in (0, 1), "native network Delay callback duplicated")
        expected[selected] = counts.get(selected, 0)
    require(all(counts.get(key, 0) == wanted for key, wanted in expected.items()), "selected task/Delay/End business counts differ")
    require(len(data["ui"]) == int(not zero), "actual typed UI producer missing/duplicated")
    for message in data["ui"]:
        require(message["instigator"] == target and math.isfinite(message["duration"]) and message["duration"] > 0. and
            abs(message["duration"]-message["native_cooldown"]) <= .0001, "actual native UI owner/cooldown differs")
    require(len(data["cues"]) == int(not zero and not data["native_dedicated_server"]), "actual native Cue receiver missing/duplicated")
    for cue in data["cues"]:
        require(cue["target"] == target and abs(cue["normalized"]-.25) <= .0001 and abs(cue["raw"]-1850.) <= .0001 and
            cue["effect_level"] == cue["ability_level"] == 1 and cue["replicate_location"] is False,
            "actual native Cue target/parameters differ")
        direction = value.get("chosen", value.get("stored"))["direction"]
        require(close_vector(cue["normal"], direction), "native Cue direction not the actual stored native direction")


def compare_cues(left, right):
    require(len(left) == len(right), "BP/Python native Cue count differs")
    for bp, py in zip(left, right):
        require(close_vector(bp["normal"], py["normal"]), "BP/Python native Cue normal differs")
        omitted = {"game_time", "normal"}
        require({key: value for key, value in bp.items() if key not in omitted} ==
            {key: value for key, value in py.items() if key not in omitted}, "BP/Python complete native Cue parameters differ")


def standalone(report):
    base = copy.deepcopy(report); base["dash_task_business_migrated"] = False
    # This projection reuses only previous controls; it does not certify tasks.
    activation.standalone(base); shutdown(report)
    for case in report["cases"]: row(case, zero=case["zero_direction"], target=case["actor"])
    for name in activation.SCENARIOS:
        bp, py = [next(value for value in report["cases"] if (value["name"], value["profile"]) == (name, profile)) for profile in ("BlueprintFallback", "Python")]
        for field in ("cues", "ui"):
            require(len(bp["task_business"][field]) == len(py["task_business"][field]), "BP/Python native producer multiplicity differs")
        compare_cues(bp["task_business"]["cues"], py["task_business"]["cues"])
    return dict(status="passed", actual_native_task_trials=12, native_cue_and_typed_ui_observed=True,
        original_kismet_delay_retained=True, task_scopes_closed=True, extended_lifecycle_pause_interrupt_tested=False, full_acceptance=False)


def client(report):
    base = copy.deepcopy(report); base["dash_task_business_migrated"] = False
    rpc_client(base); shutdown(report)
    for case in report["cases"]:
        local_row(case, require_changed=case["profile"] == "Python"); activation.activation_row(case, True, False)
        row(case, authority=False, target=case["task_business"]["target"], replicated_end=True)


def network(reports):
    base = copy.deepcopy(reports)
    for peer in ("A", "B0"): base[peer]["dash_task_business_migrated"] = False
    result = activation.network(base)
    for peer in ("A", "B0"): client(reports[peer])
    shutdown(reports["server"])
    for case in reports["server"]["cases"]:
        row(case, authority=True, remote=True, target=case["task_business"]["target"], replicated_end=True)
        owner = reports[case["target"]]["cases"][case["index"]]
        selected = "delay_completed" if case["profile"] == "Python" else "fallback_delay_completed"
        completions = owner["task_business"]["stats"].get(selected, 0)+case["task_business"]["stats"].get(selected, 0)
        require(1 <= completions <= 2, "both worlds ended without any real native Delay completion")
    for peer in ("A", "B0"):
        for name in ("forward", "left"):
            bp, py = [next(case for case in reports[peer]["cases"] if (case["name"], case["profile"]) == (name, profile)) for profile in ("BlueprintFallback", "Python")]
            compare_cues(bp["task_business"]["cues"], py["task_business"]["cues"])
    return dict(result, native_task_business_migrated=True, native_task_cue_ui_business_tested=True, task_scopes_closed=True,
        extended_lifecycle_pause_interrupt_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--directory"); group.add_argument("--report"); args = parser.parse_args()
    if args.directory:
        root = Path(args.directory); result = network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    else: result = standalone(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))
    print(json.dumps(result))
