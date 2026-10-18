"""Native replicated Actor/RPC/GAS/destruction evidence, never file transport."""
import argparse
import json
import math
from pathlib import Path
from .grenade_detonate_contract import CLASS, require
from uep_lyra_abilities.network_identity import key, same

PEERS = ("A", "B0")
PLAN = tuple((owner, name, profile) for owner in PEERS
             for name in ("empty-rpc", "enemy-rpc", "empty-fuse")
             for profile in ("BlueprintFallback", "Python"))
FALSE = ("full_acceptance", "packaged_runtime", "physical_input_tested", "packet_loss_tested", "travel_rejoin_tested",
         "health_properties_written", "asc_binding_repaired", "rpc_function_overridden", "body_callback_replayed",
         "gameplay_state_delivered_by_files", "damage_effect_called_by_fixture", "quantitative_flight_tested",
         "audio_playback_tested", "authored_particle_expiry_accepted", "far_field_pawn_teleports")


def accept_command(command, processed, completed):
    position, stage = command["position"], command["stage"]
    require(type(position) is int and stage in ("prepare", "spawn", "observe", "complete"), "invalid explosion scheduling command")
    require(position == len(PLAN) if stage == "complete" else 0 <= position < len(PLAN), "explosion position outside plan")
    return (position, stage) != processed and (position > completed or stage == "complete")


def common(report, mode):
    require(report["status"] == "passed" and report["error"] is None and report["native_mode"] == mode, "native explosion network report failed")
    for name in FALSE:
        require(report[name] is False, "network explosion scope overclaim: "+name)
    require(report["network_acceptance"] is True and report["observers_restored"] is True and report["remaining_projectiles"] == 0, "native Actor/observer cleanup incomplete")
    require(report["observation_errors"] == [] and len(report["cases"]) == len(PLAN), "native network explosion matrix incomplete")
    configuration = report["original_actor_configuration"]
    require(configuration["bReplicates"] and configuration["bReplicateMovement"] and not configuration["bNetLoadOnClient"], "original replicated Actor configuration differs")
    require(report["actor_configuration_preserved"] and report["actor_selector_restored"], "native replication configuration or declared profile selector not restored")


def body(event, profile, authority):
    require(event["profile"] == profile and event["class"] == CLASS and event["authority"] is authority, "wrong native explosion body/authority")
    require(event["role"] == (3 if authority else 1) and key(event["identity"]) is not None and event["identity"]["local_role"] == event["role"], "native Actor wire identity/role missing")
    require(event["rpc_flags_preserved"] and event["held_stationary_by_native_fixture"], "native RPC or declared fixture precondition differs")
    counts = event["stats"]
    py = profile == "Python"
    require(counts["python_bodies"] == int(py) and counts["fallback_bodies"] == int(not py), "selected native body count differs")
    if py:
        require(counts["cues"] == counts["hidden"] == counts["movement_stops"] == counts["authority_queries"] == 1, "native visual/authority decision sequence missing")
        require(counts["overlaps"] == int(authority) and counts["destroys"] == int(authority) and counts["trail_bindings"] == 0, "server no-render/client remote branch differs")
        if not authority:
            require(counts["traces"] == counts["effects"] == 0, "client attempted authority damage")
    if authority:
        require(event["trail_before"] is False and event["actor_destroyed_after_body"] is True, "native headless null-trail immediate destruction missing")
    else:
        require(event["actor_destroyed_after_body"] is False and event["hidden_after"] and not event["movement_active_after"], "client must await native replicated destruction after visual branch")


def validate(server, clients):
    common(server, "DedicatedServer")
    require(set(clients) == set(PEERS) and set(server["player_ids"]) == set(PEERS), "two actual native owners required")
    require(len(set(server["player_ids"].values())) == 2 and server["server_waited_for_client_process_exit"], "native owners/exits incomplete")
    for peer, report in clients.items():
        common(report, "Client")
        require(report["peer"] == peer and report["player_id"] == server["player_ids"][peer], "client owner mismatch")
    identities = []
    for index, (owner, name, profile) in enumerate(PLAN):
        row = server["cases"][index]
        require((row["position"], row["owner"], row["name"], row["profile"]) == (index, owner, name, profile), "server explosion case order differs")
        require(row["native_body_count"] == 1 and row["destroyed"] and row["other_health_unchanged"], "server native explosion/body/health witness failed")
        body(row["body"], profile, True)
        identities.append(key(row["identity"]))
        require(same(row["identity"], row["body"]["identity"]), "server observed another projectile")
        require(row["native_target_overlap"] == ([] if name != "enemy-rpc" else [row["victim_path"]]), "native explosion target isolation differs")
        if name == "enemy-rpc":
            require(row["team_comparison"] == 1 and 0 < row["health_after"] < row["health_before"] == 100., "actual nonlethal enemy GAS damage missing")
        else:
            require(row["health_before"] == row["health_after"] == 100., "empty explosion changed target health")
        require(row["native_fuse_trigger"] == (name == "empty-fuse"), "native fuse/direct RPC trigger differs")
        if name == "empty-fuse":
            require(2. <= row["body"]["age_at_body"] < 3., "original native fuse timing differs")
        for peer in PEERS:
            view = clients[peer]["cases"][index]
            require((view["position"], view["owner"], view["name"], view["profile"]) == (index, owner, name, profile), "client explosion schedule differs")
            require(view["native_body_count"] == 1 and view["replicated_actor_destroyed"] and view["quiet_ticks"] >= 8, "client RPC/destruction count incomplete")
            require(same(view["identity"], row["identity"]) and same(view["body"]["identity"], row["identity"]), "client did not observe same native replicated Actor")
            body(view["body"], profile, False)
            require(same(view["source_identity"], row["source_identity"]) and same(view["victim_identity"], row["victim_identity"]), "native source/target Pawn wire mismatch")
            require(view["source_identity"]["local_role"] == (2 if peer == owner else 1), "owner/foreign source role mismatch")
            require(math.isclose(view["health_after"], row["health_after"], abs_tol=.001) and view["other_health_unchanged"], "actual client GAS Health does not match authority")
            require(view["server_values_written_to_gameplay"] is False, "schedule payload used to simulate replication")
    require(len(set(identities)) == len(PLAN), "native projectiles reused a wire identity across distinct spawns")
    # Native hit geometry may vary slightly across ordinary pawn respawns.
    for first, second in zip(server["cases"][::2], server["cases"][1::2]):
        require(math.isclose(first["health_after"], second["health_after"], abs_tol=.25), "original/Python native damage divergence")
    return dict(status="passed", native_authority_explosions=len(PLAN), client_multicast_bodies=2*len(PLAN),
                real_owners=2, native_headless_destroy_cases=len(PLAN), full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    reports = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
    print(json.dumps(validate(reports["server"], {peer: reports[peer] for peer in PEERS})))
