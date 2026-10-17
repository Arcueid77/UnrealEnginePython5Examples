"""Real two-owner predicted Melee/montage cleanup; no trace/damage scope promotion."""
import argparse
import json
from pathlib import Path
from .melee_hit_montage_contract import require

TRIALS = tuple((name, profile) for profile in ("BlueprintFallback", "Python") for name in ("natural", "cancel", "profile-switch"))
PEERS = ("A", "B0")


def shutdown(value):
    stats = value["shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [], "network Melee scope leak")


def row(value, authority):
    name, profile = value["name"], value["profile"]; python = profile == "Python"; switched = name == "profile-switch" and not authority
    for key in ("native_active_observed", "native_montage_task_observed", "native_ended", "actual_scope_closed", "all_pawn_health_unchanged", "specs_unchanged", "config_unchanged"):
        require(value[key] is True, "native network Melee observation missing: "+key)
    require(value["native_root_task_observed"] is False and value["native_tasks_after"] == 0 and value["quiet_ticks"] >= 20 and value["equipment"]["montage"],
        "network no-damage montage/task/quiet proof missing")
    stats = value["stats"]; expected = dict(activations=int(python), fallback_activations=int(not python), commits=int(python), cast_failed=0,
        montage_tasks=int(python), authority_trace_entries=int(python and authority), scopes_created=int(python), scopes_closed=int(python),
        native_ends=int(python and not switched), fallback_native_ends=int(not python and not switched))
    require(all(stats.get(key, 0) == count for key, count in expected.items()), "native network activation/authority/End routing differs")
    callbacks = [stats.get(key, 0) for key in ("completed", "blend_out", "interrupted", "cancelled")]
    require(all(count in (0, 1) for count in callbacks) and sum(callbacks) <= int(python and not switched), "network montage callback duplicated/wrong Profile")
    if not authority:
        require(value["native_request_accepted"] and value["native_repeat_rejected"] and value["native_initial_montage"] == value["equipment"]["montage"], "actual owner native request/montage missing")
        if name != "natural":
            action = value["intervention"]
            require(action is not None and action["active_before"] and action["authority_confirmed"] and action["active_after"] is False and
                .07 <= action["time"] < 1., "real confirmed native Melee intervention missing")
            require(action["native_entry"] == ("ue.set_mixin_profile" if name == "profile-switch" else "GameplayAbility.K2_CancelAbility"), "native Melee intervention changed")
            if name == "profile-switch": require(action["new_profile"] != profile, "actual native Melee Profile did not change")
    return sum(callbacks)


def client(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_role"] == 2 and report["native_net_mode"] == "Client" and
        report["actual_granted_primary_instance"] and report["actual_ability_class"] == "/ShooterCore/Game/Melee/GA_Melee.GA_Melee_C", "actual native Melee client report missing")
    for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_event_replayed", "task_callbacks_replayed", "ability_granted_by_fixture", "health_or_raw_velocity_written", "trace_damage_business_migrated"):
        require(report[flag] is False, "network Melee scope overclaimed: "+flag)
    require(report["profile_restored"] and report["specs_unchanged"] and report["config_unchanged"] and report["native_pose_restored"] and
        report["native_control_restoration"]["control_rotation"], "native owner cleanup missing")
    shutdown(report); require(len(report["cases"]) == len(TRIALS), "native Melee owner matrix incomplete")
    for index, value in enumerate(report["cases"]):
        require((value["index"], value["name"], value["profile"]) == (index, *TRIALS[index]), "native owner trial order changed")
        row(value, False)


def validate(reports):
    for peer in PEERS: client(reports[peer])
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["native_net_mode"] == "DedicatedServer" and
        server["actual_granted_primary_instances"] and server["server_waited_for_client_process_exit"] and server["profiles_restored"] and server["specs_config_unchanged"],
        "native authority cleanup/exit/type proof missing")
    for flag in ("activation_event_replayed", "task_callbacks_replayed", "ability_granted_by_fixture", "health_or_raw_velocity_written", "trace_damage_business_migrated", "full_acceptance", "packaged_runtime"):
        require(server[flag] is False, "authority scope overclaimed: "+flag)
    require(len({value["run_id"] for value in reports.values()}) == 1 and reports["A"]["player_id"] != reports["B0"]["player_id"] and
        all(server["player_ids"][peer] == reports[peer]["player_id"] for peer in PEERS), "native two-owner identity/run mismatch")
    shutdown(server); require(len(server["cases"]) == 2*len(TRIALS), "native authority Melee matrix incomplete")
    for position, value in enumerate(server["cases"]):
        peer, index = PEERS[position//len(TRIALS)], position%len(TRIALS)
        require((value["target"], value["index"], value["name"], value["profile"]) == (peer, index, *TRIALS[index]) and
            value["native_role"] == 3 and value["authority_ready_sent"] and value["foreign_owner_unchanged"], "actual native authority activation/foreign isolation missing")
        owner = reports[peer]["cases"][index]; ack = value["client"]
        require(ack["peer"] == peer and ack["index"] == index and ack["run_id"] == reports[peer]["run_id"] and ack["row"] == owner,
            "authority acknowledgement not actual owner row")
        authority_callbacks = row(value, True); owner_callbacks = row(owner, False)
        require(value["equipment"]["montage"] == owner["equipment"]["montage"], "native owner/authority equipped montage differs")
        if value["profile"] == "Python" and value["name"] != "profile-switch":
            require(authority_callbacks+owner_callbacks >= 1, "both native worlds ended without any actual montage continuation")
    return dict(status="passed", actual_native_owner_requests=12, actual_native_authority_activations=12, actual_owners=2,
        natural_cancel_active_profile_cleanup_tested=True, trace_damage_business_migrated=False,
        travel_rejoin_packet_loss_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); args = parser.parse_args(); root = Path(args.directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
