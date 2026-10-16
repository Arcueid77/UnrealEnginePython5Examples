"""Independent real two-owner ServerInitiated spawn acceptance; no native import."""
import argparse
import json
from pathlib import Path
from .spawn_effect_contract import require

PEERS = ("A", "B0")
NETWORK_PLAN = ("natural-duration", "montage-interrupt", "native-cancel", "external-native-end", "active-profile-switch", "repeat", "foreign-input-lock")


def validate_row(row, name, profile, authority):
    require(row["name"] == name and row["profile"] == profile and row["native_role"] == (3 if authority else 2) and
        row["native_type_preserved"] and row["native_source_avatar_matches"] and row["health_unchanged"], "native spawn role/type/source/health invalid")
    require(row["effect_at_start"] == 1 and row["immune_at_start"] and row["movement_locked_at_start"] and
        row["native_montage_playing_observed"] and row["native_ability_ended"] and row["effects_after_end"] == row["tasks_after_end"] == 0 and
        not row["immune_after_end"] and row["movement_after_end"] == (name == "foreign-input-lock") and
        row["foreign_lock_released_restores_baseline"] and row["original_player_restored"] and row["no_late_business_mutation"],
        "native spawn replicated effect/montage/input cleanup differs")
    duration = row["montage_length"]
    require(abs(duration-2.75) < .001 and row["input_fraction"] == .75 and not row["native_pause_observed"], "original spawn defaults/network scope changed")
    early = name in ("native-cancel", "external-native-end", "active-profile-switch")
    require((row["native_elapsed"] < duration-.5) if early else (duration-.35 <= row["native_elapsed"] < duration+.5), "native network spawn End timing differs")
    if not early and name != "foreign-input-lock":
        require(row["unlock_elapsed"] is not None and abs(row["unlock_elapsed"]-duration*.75) < .35, "native network spawn unlock timing differs")
    require(row["profile_teardown_ended_ability"] == (authority and name == "active-profile-switch"), "authority Profile teardown/owner native End path invalid")
    if authority: require(row["interrupt_left_ability_active"] == (name == "montage-interrupt") and
        row["other_owner_unchanged"] and row["actual_owner_rpc_start_observed"], "authority/real owner readiness or isolation failed")
    else: require(row["local_ability_activation_called"] is False, "client must not activate ServerInitiated spawn directly")
    stats = row["counters"]
    if profile == "Python":
        require(stats["activations"] == stats["scopes_created"] == stats["scopes_closed"] == stats["effects_applied"] == stats["effects_removed"] ==
            stats["movement_locks"] == stats["movement_unlocks"] == 1 and stats["tasks_created"] == 3 and
            stats["native_ends"] == int(not (authority and name == "active-profile-switch")), "network spawn Python ownership not balanced")
    else:
        require(stats["fallback_activations"] == 1 and stats["fallback_native_ends"] == int(not (authority and name == "active-profile-switch")) and
            stats["activations"] == stats["tasks_created"] == stats["scopes_created"] == 0, "network original BP path bypassed or duplicated")


def validate(reports):
    server = reports["server"]
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2 and
        server["fixture_authority_native_activation"] and set(server["native_input_locks_suspended"]) == set(PEERS) and
        all(type(value) is int and 0 <= value <= 16 for value in server["native_input_locks_suspended"].values()) and
        server["server_waited_for_client_process_exit"] and server["native_playing_gate"]["native_playing_phase"] and
        server["native_input_locks_restored"] == server["native_input_locks_suspended"], "native spawn owners/Playing/input-stack/exit barrier invalid")
    expected = [(peer, index, name, profile) for peer in PEERS for index, (name, profile) in enumerate(
        (name, profile) for name in NETWORK_PLAN for profile in ("BlueprintFallback", "Python"))]
    require(len(server["cases"]) == len(expected), "native spawn authority matrix incomplete")
    for peer, report in reports.items():
        require(report["status"] == "passed" and report["error"] is None and report["run_id"] == server["run_id"] and report["peer"] == peer and
            report["original_player_restored"] and report["original_ability_specs_restored"] and report["original_fraction_restored"] and
            report["native_default_on_spawn_observed"] and report["native_policy"] == [2, 1, 2], "native spawn peer baseline/restore failed")
        for flag in ("full_acceptance", "packaged_runtime", "activation_handler_replayed", "task_callbacks_replayed", "health_properties_written",
            "animation_assets_modified", "original_montage_or_effect_written", "native_rpc_bypassed", "gameplay_state_delivered_by_files", "packet_loss_tested", "travel_rejoin_tested", "physical_input_tested"):
            require(report[flag] is False, "unsupported native spawn network claim: "+flag)
        stats = report["policy_shutdown"]
        require(stats["errors"] == [] and stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"], "native network spawn scope leak")
        if peer != "server":
            require(report["player_id"] == server["player_ids"][peer] and not report["local_ability_activation_called"], "native spawn owner ID/local activation invalid")
            positions = [position for position, (target, index, name, profile) in enumerate(expected) if target == peer]
            require([row["position"] for row in report["cases"]] == positions and
                [row["position"] for row in report["foreign_cases"]] == [position for position in range(len(expected)) if position not in positions] and
                all(row["original_state_unchanged"] for row in report["foreign_cases"]), "native spawn own/foreign observations incomplete")
    for position, (peer, index, name, profile) in enumerate(expected):
        row = server["cases"][position]
        require((row["position"], row["target"], row["index"]) == (position, peer, index), "native spawn authority order invalid")
        initial = server["native_initials"][peer]
        require(initial["default_python_on_spawn"] and initial["native_role"] == 3 and initial["player_id"] == server["player_ids"][peer], "authority default spawn/source invalid")
        validate_row(row, name, profile, True)
        owner = reports[peer]["cases"][index]
        require(owner["index"] == index, "owner native spawn index invalid")
        validate_row(owner, name, profile, False)
    return dict(status="passed", bounded_native_network_acceptance=True, actual_owners=2, native_authority_trials=len(expected),
        direct_client_activation=False, gameplay_state_delivered_by_files=False, network_pause_tested=False,
        network_fraction_boundaries_tested=False, immediate_handoff_network_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
