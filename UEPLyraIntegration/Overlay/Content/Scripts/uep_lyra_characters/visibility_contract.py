"""Native InitState/hidden flags; no pixel or full BeginPlay certification."""
import argparse
import json
from pathlib import Path
from .possessed_contract import validate as possession_validate
from .initial_inventory_contract import require, CLASS

SCENARIOS = [(name, calls, profile) for name, calls in (("single", 1), ("repeat", 2), ("destroy-pending", 1), ("switch-pending", 1)) for profile in ("BlueprintFallback", "Python")]


def payload(value, actor, component=None):
    require(value["actor"] == actor and value["state"] == "InitState.GameplayReady" and value["feature"] and value["implementer"] and
        (component is None or value["implementer"] == component), "actual native InitState payload differs")


def natural(value, actor, hidden):
    require({key: value[key] for key in ("python_calls", "fallback_calls", "delay_requests", "resumes", "show_calls")} ==
        dict(python_calls=1, fallback_calls=0, delay_requests=1, resumes=1, show_calls=1) and value["pending"] is False and hidden is False,
        "natural native InitState did not enter one Python delayed-show continuation")
    payload(value["last_payload"], actor)


def check_trial(row, scenario):
    name, calls, profile = scenario; py = profile == "Python"; destroyed = name == "destroy-pending"
    require((row["name"], row["native_registration_calls"], row["profile"]) == scenario and row["native_character_class"] == CLASS,
        "native visibility trial order/type differs")
    for key in ("actual_native_initstate_registration", "hidden_before_resume", "actor_was_not_rooted", "owned_new_pawn_destroyed",
                "no_late_script_work_after_owned_destruction", "owned_team_observers_collected", "original_active_proxies_preserved", "visibility_quiet_after_destroy"):
        require(row[key] is True, "native visibility timing/owner cleanup differs: "+key)
    require(row["callback_manually_replayed"] is False and row["native_hidden_fields_written_directly"] is False and
        row["native_hidden_before_destroy"] is destroyed and all(value is True for value in row["cleanup"].values()), "native visibility early/late show or fixture ownership differs")
    payload(row["payload"], row["native_actor_path"], row["native_component_path"])
    require(row["visibility_delta"] == dict(python_calls=calls if py else 0, fallback_calls=0 if py else calls,
        delay_requests=calls if py else 0, resumes=int(py and not destroyed), show_calls=int(py and not destroyed)), "selected native visibility receiver/resumption count differs")
    expected_profile = ("Python" if profile == "BlueprintFallback" else "BlueprintFallback") if name == "switch-pending" else profile
    require(row["profile_before_resume"] == expected_profile, "pending visibility Profile switch missing")


def scope(report):
    require(report["visibility_callback_business_migrated"] is True and report["visibility_native_backend"] == "DelayUntilNextTick" and
        report["visibility_python_ticker_registered"] is False and report["visibility_physical_pixels_tested"] is False,
        "visibility migration/native backend/scope differs")


def validate(report):
    result = possession_validate(report); scope(report)
    natural(report["natural_startup_visibility"], report["natural_startup_visibility_actor"], report["natural_startup_hidden"])
    for row in report["readiness_transition_cases"]:
        py = row["profile"] == "Python"; values = row["visibility_before_destroy"]
        require(row["native_hidden_after_spawn"] is True and row["native_hidden_before_destroy"] is False and
            values["python_calls"] == int(py) and values["fallback_calls"] == int(not py) and values["resumes"] == values["show_calls"] == int(py),
            "native unpossessed-to-ready visibility/profile differs")
        payload(values["last_payload"], row["native_visibility_actor_path"])
        require(not py or values["uuid"] not in row["inventory_latent_uuids"], "Python visibility/inventory latent UUID collision")
    require(len(report["visibility_cases"]) == len(SCENARIOS), "native visibility case matrix missing")
    for row, scenario in zip(report["visibility_cases"], SCENARIOS): check_trial(row, scenario)
    return dict(result, native_initstate_visibility_accepted=True, native_visibility_pairs=4, physical_pixels_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
