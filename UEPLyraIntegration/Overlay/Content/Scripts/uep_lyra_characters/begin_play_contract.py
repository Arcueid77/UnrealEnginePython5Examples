"""Natural native BeginPlay order and default-profile fixture isolation."""
import argparse
import json
from pathlib import Path
from .visibility_contract import validate as visibility_validate, natural
from .initial_inventory_contract import require, CLASS, P

SCENARIOS = [(name, profile) for name in ("pending", "ready") for profile in ("BlueprintFallback", "Python")]


def counts(values, profile):
    py = profile == "Python"
    require(values == dict(python_calls=int(py), fallback_calls=int(not py), parent_calls=int(py), listen_calls=int(py), hide_calls=int(py), register_calls=int(py),
        order=["parent", "listen", "hide", "register"] if py else []), "native BeginPlay selected Profile/ordered calls differ")


def scope(report):
    require(report["begin_play_business_migrated"] is True and report["begin_play_manually_replayed"] is False and
        report["ancestor_construction_death_business_migrated"] is False, "BeginPlay migration/ancestor scope differs")


def validate(report):
    result = visibility_validate(report, begin_play_migrated=True); scope(report); counts(report["natural_startup_begin_play"], "Python")
    require(len(report["begin_play_cases"]) == len(SCENARIOS), "native BeginPlay case matrix incomplete")
    for row, scenario in zip(report["begin_play_cases"], SCENARIOS):
        name, profile = scenario; py = profile == "Python"
        require((row["name"], row["profile"]) == scenario and row["native_character_class"] == CLASS, "native BeginPlay identity/order differs")
        counts(row["begin_play_counters"], profile)
        for key in ("actual_native_new_actor_begin_play", "fixture_cdo_profile_temporarily_overridden_for_spawn", "cdo_profile_restored_immediately",
                    "cdo_profile_still_restored", "actor_was_not_rooted", "owned_new_pawn_destroyed", "no_late_script_work_after_owned_destruction",
                    "owned_team_observers_collected", "original_active_proxies_preserved", "begin_play_quiet_after_destroy"):
            require(row[key] is True, "native BeginPlay/default/owner cleanup differs: "+key)
        require(row["begin_play_manually_replayed"] is False and all(value is True for value in row["cleanup"].values()), "BeginPlay replay or native fixture cleanup differs")
        listener = row["listener_counters"]
        require(listener["python_calls"] == int(py) and listener["fallback_calls"] == int(not py) and listener["factories"] == listener["binds"] == listener["activations"] == int(py),
            "actual BeginPlay did not enter exactly one selected native team-listener path")
        if name == "pending":
            require(row["native_hidden"] is True and row["visibility_counters"]["python_calls"] == row["visibility_counters"]["fallback_calls"] == 0,
                "unready new Actor shown or received premature InitState callback")
        else:
            values = row["visibility_counters"]
            require(row["native_hidden"] is False and values["python_calls"] == int(py) and values["fallback_calls"] == int(not py) and
                values["resumes"] == values["show_calls"] == int(py), "ready new Actor InitState/visibility Profile differs")
            require(row["native_inventory_model"]["items"] == [P] and row["native_inventory_model"]["slots"] == [P, None, None], "real ready native loadout differs")
    require(report["begin_play_cases"][2]["native_inventory_model"] == report["begin_play_cases"][3]["native_inventory_model"], "original/Python natural startup inventory differs")
    return dict(result, native_begin_play_accepted=True, native_begin_play_pairs=2, ancestor_construction_death_business_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
