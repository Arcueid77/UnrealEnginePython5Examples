"""Predicted ability -> native moving projectile -> explosion/destruction."""
import argparse
import json
import math
from pathlib import Path
from .grenade_detonate_contract import CLASS, require
from uep_lyra_abilities.network_identity import key, same

PEERS = ("A", "B0")
PLAN = tuple((peer, profile) for peer in PEERS for profile in ("BlueprintFallback", "Python"))
FALSE = ("full_acceptance", "packaged_runtime", "physical_input_tested", "packet_loss_tested", "travel_rejoin_tested",
         "health_properties_written", "asc_binding_repaired", "rpc_function_overridden", "body_callback_replayed",
         "gameplay_state_delivered_by_files", "projectile_spawned_by_fixture", "projectile_movement_written_by_fixture",
         "projectile_timer_changed_by_fixture", "detonate_requested_by_fixture", "projectile_destroyed_by_fixture",
         "pawn_teleports", "audio_playback_tested", "quantitative_trajectory_equivalence_accepted")


def reset_peers(owner, health):
    """Normal respawn prepares cost for the owner and heals prior real damage."""
    require(owner in PEERS and set(health) == set(PEERS), "reset preparation requires both actual owners")
    return tuple(peer for peer in PEERS if peer == owner or health[peer] != 100.)


def accept_command(command, processed, completed):
    position, stage = command["position"], command["stage"]
    require(type(position) is int and stage in ("prepare", "activate", "complete"), "invalid natural-throw scheduling command")
    require(position == len(PLAN) if stage == "complete" else 0 <= position < len(PLAN), "natural-throw position outside plan")
    return (position, stage) != processed and (position > completed or stage == "complete")


def common(report, mode):
    require(report["status"] == "passed" and report["error"] is None and report["native_mode"] == mode, "native natural-throw report failed")
    for field in FALSE: require(report[field] is False, "natural-throw scope overclaim: "+field)
    for field in ("network_acceptance", "observers_restored", "ability_observers_restored", "ability_profiles_restored",
                  "actor_selector_restored", "actor_configuration_preserved"):
        require(report[field] is True, "native natural-throw cleanup missing: "+field)
    require(report["observation_errors"] == [] and report["remaining_projectiles"] == 0 and len(report["cases"]) == len(PLAN), "native natural-throw matrix/cleanup incomplete")


def flight(row, authority, profile):
    require(row["native_begin_count"] == row["native_body_count"] == 1 and row["destroyed"] and row["quiet_ticks"] >= 8, "native projectile lifecycle incomplete")
    event = row["body"]
    require(event["class"] == CLASS and event["profile"] == profile and event["authority"] is authority and event["role"] == (3 if authority else 1), "wrong native moving projectile role/profile")
    require(event["rpc_flags_preserved"] and same(row["identity"], event["identity"]), "native moving projectile RPC/wire identity differs")
    require(row["trajectory"]["samples"] >= 3 and row["trajectory"]["distinct_positions"] >= 3 and row["trajectory"]["max_displacement"] > 25., "native projectile did not actually fly")
    require(row["trajectory"]["active_movement_samples"] >= 1 and row["begin"]["movement_active"], "native projectile movement was disabled")
    require(event["fixture_held_stationary"] is False, "natural flight replaced with stationary actor fixture")
    py = profile == "Python"
    require(event["stats"]["python_bodies"] == int(py) and event["stats"]["fallback_bodies"] == int(not py), "native body dispatch differs")
    if authority:
        require(event["trigger"] in ("native-fuse", "native-enemy-hit") and event["actor_destroyed_after_body"] and not event["trail_before"], "native authority trigger/no-render destruction missing")
        if event["trigger"] == "native-fuse":
            require(event["fuse_remaining_before"] <= 0. and event["age_at_body"] >= 2., "fixture replaced original 2s fuse")
        else:
            require(event["hit_comparison"] == 1 and not event["fuse_exists_before"], "native enemy hit did not cancel fuse")
    else:
        require(event["trigger"] in ("client-pending-fuse", "client-fuse-due", "native-enemy-hit"), "unclassified native client body source")
        if event["trigger"] == "client-pending-fuse": require(event["fuse_exists_before"] and event["fuse_remaining_before"] > 0., "pending local fuse evidence differs")
        elif event["trigger"] == "client-fuse-due": require(event["fuse_remaining_before"] <= 0., "due local fuse evidence differs")
        else: require(event["hit_comparison"] == 1 and not event["fuse_exists_before"], "native local enemy-Hit branch differs")
        require(event["hidden_after"] and not event["movement_active_after"] and not event["actor_destroyed_after_body"], "client native visual branch differs")
        if py: require(event["stats"]["overlaps"] == event["stats"]["traces"] == event["stats"]["effects"] == 0, "client applied authority damage")


def activation(row, profile, authority):
    require(row["profile"] == profile and row["authority"] is authority and row["mode"] == (0 if authority else 2), "actual authority/predicted GAS activation missing")
    require(row["source_role"] == (3 if authority else 2) and row["native_begin_delta"] == int(authority), "projectile was not spawned solely by original authority ability")
    require(row["active_after"] is False and row["stats"]["python_calls"] == int(profile == "Python") and row["stats"]["fallback_calls"] == int(profile == "BlueprintFallback"), "selected native activation/End count differs")
    if profile == "Python":
        require(row["stats"]["projectiles"] == int(authority) and row["stats"]["commits"] == row["stats"]["native_ends"] == 1, "actual native ability spawn/commit/End chain missing")


def validate(server, clients, native_logs):
    common(server, "DedicatedServer")
    require(set(clients) == set(PEERS) and len(set(server["player_ids"].values())) == 2 and server["server_waited_for_client_process_exit"], "two actual owners/real exits required")
    for peer, report in clients.items():
        common(report, "Client")
        require(report["player_id"] == server["player_ids"][peer] and report["control_rotation_restored"], "native owner/control restoration missing")
    require(set(native_logs) == {"server", *PEERS}, "native per-peer RPC log evidence required")
    ids = []
    for index, (owner, profile) in enumerate(PLAN):
        row = server["cases"][index]
        require((row["position"], row["owner"], row["profile"]) == (index, owner, profile), "authority natural throw plan differs")
        require(row["native_aim_sync"] and row["activation_requests"] == 0 and len(row["activations"]) == 1, "server bypassed the predicted client request")
        activation(row["activations"][0], profile, True)
        flight(row, True, profile)
        require(same(row["body"]["instigator_identity"], row["source_identity"]), "native authority throw lost its real instigator")
        require(row["source_identity"]["local_role"] == 3, "throw source is not authoritative on server")
        ids.append(key(row["identity"]))
        guid = row["identity"]["wire_id"]
        outgoing = native_logs["server"].get(guid)
        require(outgoing is not None and outgoing["actor"] == row["identity"]["object_path"] and outgoing["position"] == index and len(outgoing["sent_lines"]) == 2, "actual reliable broadcast to two connections unproven")
        for peer in PEERS:
            view = clients[peer]["cases"][index]
            require((view["position"], view["owner"], view["profile"]) == (index, owner, profile), "client natural throw plan differs")
            require(same(view["identity"], row["identity"]) and same(view["source_identity"], row["source_identity"]), "native natural projectile/source wire mismatch")
            require(view["source_identity"]["local_role"] == (2 if peer == owner else 1), "native owning/foreign source role differs")
            flight(view, False, profile)
            received = native_logs[peer].get(guid)
            require(received is not None and received["actor"] == view["identity"]["object_path"] and received["native_guid"] == guid and
                    received["position"] == index and len(received["received_lines"]) == len(received["cleanup_lines"]) == 1,
                    "actual native per-Actor RPC receive/GUID destruction correlation missing")
            require(same(view["body"]["instigator_identity"], row["source_identity"]), "client native throw Instigator differs")
            require(view["activation_requests"] == int(peer == owner) and len(view["activations"]) == int(peer == owner), "foreign owner activated or own client request absent")
            if peer == owner:
                require(view["native_request_accepted"], "native owning ASC rejected throw")
                activation(view["activations"][0], profile, False)
            for target in PEERS:
                actual, expected = view["player_health_after"][target], row["player_health_after"][target]
                require(same(actual["identity"], expected["identity"]) and math.isfinite(actual["health"]) and
                        math.isclose(actual["health"], expected["health"], abs_tol=.001), "native player Health replication differs after natural throw")
    require(len(set(ids)) == len(PLAN), "distinct normal ability spawns reused a native wire identity")
    return dict(status="passed", actual_predicted_client_throws=4, native_authority_ability_spawns=4,
                naturally_moving_network_replicas=8, actual_native_explosions=4, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    reports = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
    from .grenade_rpc_log_evidence import parse
    native_logs = {peer: parse((root/(peer+".log")).read_text(encoding="utf-8-sig"), server=peer == "server") for peer in ("server",)+PEERS}
    result = validate(reports["server"], {peer: reports[peer] for peer in PEERS}, native_logs)
    (root/"native-rpc-log-proof.json").write_text(json.dumps(dict(result=result, peers=native_logs), indent=2), encoding="utf-8")
    print(json.dumps(result))
