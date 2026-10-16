"""Independent two-owner native authority + client movement report gate."""
import argparse
import json
import math
from pathlib import Path
from .jump_contract import PLAN, require, validate as validate_client

PEERS = ("A", "B0")


def validate(reports):
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and
            server["server_waited_for_client_process_exit"] is True, "authority Jump report/exit barrier failed")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "ability_activation_called_by_probe",
                  "callback_replay", "authoritative_movement_written", "packet_loss_tested", "travel_rejoin_tested"):
        require(server[field] is False, "unsupported network Jump claim: "+field)
    ids = server["player_ids"]
    require(server["native_playing_gate"]["native_playing_phase"] is True and
            len(server["native_playing_gate"]["stable_authority_pawns"]) == 2, "Jump captured transient Warmup pawns")
    require(set(ids) == set(PEERS) and len(set(ids.values())) == 2, "native Jump owners not distinct")
    for peer in PEERS:
        client = reports[peer]
        validate_client(client)
        require(client["peer"] == peer and client["player_id"] == ids[peer] and client["run_id"] == server["run_id"] and
                client["packet_loss_tested"] is False and client["travel_rejoin_tested"] is False,
                "native Jump client identity/claim differs")
    expected = [(peer, index) for peer in PEERS for index in range(len(PLAN)*2)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "authority Jump matrix incomplete/reordered")
    for row in server["cases"]:
        index, peer = row["index"], row["target"]
        profile = ("BlueprintFallback", "Python")[index % 2]
        require((row["name"], row["profile"]) == (PLAN[index//2], profile) and row["authoritative_role"] == 3 and
                row["native_active_observed"] and row["authority_final_inactive"] and row["authority_final_grounded"] and
                row["other_owner_stayed_idle"] and math.isfinite(row["max_authority_rise"]) and row["max_authority_rise"] > 20.,
                "authority Jump native activation/physics/foreign-owner isolation missing")
        ack = row["client"]
        require((ack["peer"], ack["index"], ack["run_id"]) == (peer, index, server["run_id"]), "foreign Jump ack")
        pair = reports[peer]["cases"][index//2]
        side = pair["blueprint" if index % 2 == 0 else "python"]
        require(ack["row"] == side, "authority ack does not match independently checked client result")
        stats = row["authority_counters"]
        for field in ("activations", "states_created", "releases_created", "scopes_created", "scopes_closed"):
            require(stats[field] == int(profile == "Python"), "authority did not run the selected BP/Python task policy")
    stats = server["policy_shutdown"]
    require(stats["activations"] == stats["scopes_created"] == stats["scopes_closed"] == 14 and
            stats["active_count"] == 0 and stats["errors"] == [], "authority native Jump shutdown leaked")
    return dict(status="passed", bounded_network_acceptance=True, owners=2, native_authority_trials=28,
                client_profile_pairs=14, packet_loss_tested=False, travel_rejoin_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
                              for peer in ("server",)+PEERS})))
