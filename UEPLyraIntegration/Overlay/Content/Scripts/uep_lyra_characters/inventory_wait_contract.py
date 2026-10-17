"""Strict native readiness transitions, coalescing and destroyed-owner gates."""
import argparse
import json
from pathlib import Path
from .initial_inventory_contract import validate as loadout_validate, require
from .inventory_ready_contract import check_ready, natural, counts
from .initial_inventory_contract import CLASS, P

TRANSITIONS = [(name, stage, calls, profile) for name, stage, calls in (
    ("controller", 0, 1), ("controller-repeat", 0, 2), ("inventory", 1, 1),
    ("inventory-repeat", 1, 2), ("quickbar", 2, 1), ("quickbar-repeat", 2, 2)) for profile in ("BlueprintFallback", "Python")]


def check_pooled_cues(row):
    for cue in row["native_pooled_cue_observers"]:
        require(cue["cue_class"] == "/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C" and cue["cue"] and cue["observer"] and
            all(cue[key] is True for key in ("observed_target_was_test_owned", "inactive", "unrooted", "native_cue_field_never_written",
                "native_cue_handle_still_matches", "native_cue_hidden_owner_cleared")), "retained native pooled Cue observer is not inactive/exact/owned-target/read-only")


def check_transition(row, scenario):
    name, stage, calls, profile = scenario; py = profile == "Python"; grants = 2 if stage == 0 else 1
    require((row["name"], row["stage"], row["calls"], row["profile"]) == scenario and row["native_character_class"] == CLASS,
        "native readiness transition identity/order differs")
    for key in ("actor_was_not_rooted", "components_manipulated_on_test_owned_controller_only", "native_checkpoint_really_missing_before_release",
                "no_grant_before_native_readiness", "native_readiness_released", "owned_new_pawn_destroyed",
                "no_late_script_work_after_owned_destruction", "owned_team_observers_collected", "original_active_proxies_preserved"):
        require(row[key] is True, "native readiness ownership/release differs: "+key)
    require(row["private_inventory_properties_written"] is False and row["native_grants"] == grants and
        row["actual_item_definition"] == P and len(set(row["native_new_item_paths"])) == grants and
        all(value is True for value in row["cleanup"].values()), "native readiness grants/cleanup differ")
    check_pooled_cues(row)
    model = row["native_model"]
    require(model == dict(items=[P]*grants, slots=[P, None, None], active=0, definition=P,
        equipment_class=P.replace("/ID_", "/B_WeaponInstance_").replace(".ID_", ".B_WeaponInstance_"), stacks=[[P, 1]]*grants),
        "native late readiness inventory/slots/equipment differ")
    before, after = row["before_release_ready"], row["after_ready"]
    require(before["python_calls"] == int(py)*calls and before["fallback_calls"] == int(not py)*calls and before["immediate_grants"] == 0 and
        before["original_wait_fallbacks"] == 0 and before[("missing_controller", "missing_inventory", "missing_quickbar")[stage]] == int(py)*calls,
        "native wait did not enter chosen missing checkpoint/Profile")
    require(after["python_calls"] == int(py)*(calls+int(stage == 0)) and after["fallback_calls"] == int(not py)*(calls+int(stage == 0)) and
        after["original_wait_fallbacks"] == 0, "native readiness callback count/fallback differs")
    waiting, resumed = row["before_release_wait"], row["after_wait"]
    if py:
        require(waiting["stage_resumes"][stage] > 0 and waiting["stage_requests"][stage] > 0 and
            resumed["stage_resumes"][stage] > waiting["stage_resumes"][stage] and resumed["grant_forwards"]-waiting["grant_forwards"] == grants and
            resumed["fallback_resumes"] == 0 and not any(resumed["pending"]), "native delayed stage did not resume/finish Python exactly")
    else: require(resumed["resumes"] == resumed["delay_requests"] == resumed["grant_forwards"] == 0, "original BP wait entered Python scheduling")


def scope(report, *, factory_migrated=False):
    require(report["experience_callback_manually_called_by_typed_bp"] is False and report["native_experience_factory_signal_tested"] is True and
        report["experience_ready_factory_migrated"] is factory_migrated and report["pending_inventory_wait_migrated"] is True and
        report["immediate_inventory_ready_branch_migrated"] is True and report["native_wait_backend"] == "DelayUntilNextTick" and
        report["python_wait_ticker_registered"] is False, "native wait backend/scope differs")
    require(report["caller_roots"] == dict(created=1, released=1) and report["owned_experience_proxies_collected"] is True, "native wait caller/proxy cleanup differs")


def validate(report, *, factory_migrated=False):
    result = loadout_validate(report); scope(report, factory_migrated=factory_migrated); natural(report["natural_startup_readiness"], True)
    for row in report["cases"]: check_ready(row)
    require(report["owned_experience_proxies_created"] == 32 and len(report["deferred_original_cases"]) == 2, "native wait request matrix incomplete")
    for row, profile in zip(report["deferred_original_cases"], ("BlueprintFallback", "Python")):
        py = profile == "Python"; expected = counts(py=int(py), fallback=int(not py)); expected["missing_controller"] = int(py)
        require(row["profile"] == profile and row["readiness_counters"] == expected and row["script_wait_quiet_after_destroy"] is True, "native wait selected receiver/destruction differs")
        values = row["wait_counters"]
        if py:
            require(values["resumes"] > 0 and values["delay_requests"] >= values["resumes"] and values["stage_resumes"][0] == values["resumes"] and
                len(set(values["uuids"])) == 3 and values["grant_forwards"] == 0 and values["fallback_resumes"] == 0, "native latent int linkage did not repeatedly resume Python stage zero")
        else: require(values["resumes"] == values["delay_requests"] == 0, "original BP wait incorrectly entered Python latent callbacks")
        for key in ("no_inventory_grant_while_controller_missing", "owned_actor_destroyed", "no_callbacks_or_grants_after_destroy_and_engine_ticks", "original_live_proxies_preserved", "owned_startup_proxies_collected", "actor_was_not_rooted"):
            require(row[key] is True, "native wait ownership/late grant differs: "+key)
    require(report["native_deferred_transitions_tested"] is True and len(report["readiness_transition_cases"]) == len(TRANSITIONS), "native readiness transition matrix missing")
    for row, scenario in zip(report["readiness_transition_cases"], TRANSITIONS): check_transition(row, scenario)
    for index in range(0, len(TRANSITIONS), 2):
        require(report["readiness_transition_cases"][index]["native_model"] == report["readiness_transition_cases"][index+1]["native_model"], "BP/Python readiness models differ")
    return dict(result, native_latent_int_linkage_resumes=True, destroyed_owner_python_resume_stopped=True, readiness_transition_matrix_accepted=True, native_late_ready_pairs=6)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
