"""Independent native FastArray/two-viewer proof; no Unreal runtime import."""
import argparse
import json
from pathlib import Path
from .cosmetic_contract import PLAN, MANNY, QUINN, require

PEERS = ("A", "B0")


def validate_reports(server, clients):
    require(set(clients) == set(PEERS) and server["server_waited_for_client_process_exit"] and
        server["native_playing_gate"]["native_playing_phase"] and len(set(server["player_ids"].values())) == 2,
        "native cosmetic server/owner/exit gates incomplete")
    total = len(server["cases"])
    require(48 <= total <= 144 and set(server["owners"]) == set(PEERS), "native cosmetic network trials incomplete")
    for peer, report in dict(server=server, **clients).items():
        require(report["status"] == "passed" and report["error"] is None and report["peer"] == peer and report["run_id"] == server["run_id"],
            "native cosmetic peer failed/foreign")
        for flag in ("full_acceptance", "packaged_runtime", "animation_assets_modified", "part_arrays_written", "part_actors_spawned_by_python",
                     "native_replication_bypassed", "beginplay_handler_replayed", "rng_seed_or_result_written", "packet_loss_tested", "travel_rejoin_tested"):
            require(report[flag] is False, "unsupported native cosmetic claim: "+flag)
        require(len(report["cases"]) == total and report["policy_shutdown"]["errors"] == [], "native cosmetic peer incomplete/error")
        if peer != "server":
            require(report["player_id"] == server["player_ids"][peer] and
                report["observer_scopes_created"] == report["observer_scopes_closed"] == total, "native cosmetic viewer leak/owner mismatch")
    owner_trials = {}
    for peer in PEERS:
        report = server["owners"][peer]
        require(report["original_player_restored"] and [row["name"] for row in report["cases"]] == [name for name, parts in PLAN],
            "authority cosmetic owner matrix/rollback incomplete")
        for row, (_, parts) in zip(report["cases"], PLAN):
            for side in ("blueprint", "python"):
                value = row[side]
                require(value["chosen_class"] == parts[value["native_actor_count"] % len(parts)], "native cosmetic deterministic choice differs")
            require(row["blueprint"]["chosen_class"] == row["python"]["chosen_class"], "original/Python native cosmetic choices differ")
        random = report["random_trials"]
        require(16 <= len(random) <= 64 and len(random) % 2 == 0, "native random cosmetic matrix incomplete")
        for profile in ("BlueprintFallback", "Python"):
            require({row["chosen_class"] for row in random if row["profile"] == profile} == {MANNY, QUINN}, "native random branch untested")
        owner_trials[peer] = [value for row in report["cases"] for value in (row["blueprint"], row["python"])]+random
    ordered = owner_trials["A"]+owner_trials["B0"]
    require(len(ordered) == total, "authority cosmetic flat/owner matrices differ")
    for position, row in enumerate(server["cases"]):
        require(row == ordered[position] and row["position"] == position and row["other_owner_unchanged"] and row["native_type_preserved"] and
                row["native_owner_preserved"] and row["native_beginplay_observed"] and row["native_cleanup_restored_original_ids"] and
                row["profile_roundtrip_preserved_part"], "native authority type/part/lifecycle/foreign-owner proof missing")
        part = row["native_part"]
        require(part["cls"] == row["chosen_class"] and part["collision_mode"] == 0 and part["actor"] is None and part["child"] is None,
            "dedicated server cosmetic configuration/presentation boundary changed")
        key = "selections" if row["kind"] == "selection" else "random_selections"
        require(row["counters"][key] == int(row["profile"] == "Python"), "native cosmetic Profile did not execute once")
        for peer in PEERS:
            view = clients[peer]["cases"][position]; part = view["native_part"]
            require((view["position"], view["target"], view["index"]) == (position, row["target"], row["index"]) and
                view["native_add_delegate_seen"] and view["native_delegate_deliveries"] >= 2 and view["native_cleanup_restored_original_ids"] and
                part["cls"] == part["actor_class"] == row["chosen_class"] and part["actor"] and part["child"] and
                part["collision_mode"] == 0 and part["actor_collision"] is False and part["attached_pawn"] == view["pawn"],
                "actual native FastArray/child-actor/delegate/cleanup not proven on both clients")
    return dict(status="passed", bounded_network_acceptance=True, authority_trials=total, viewers=2,
        random_sequence_replay_claimed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    rows = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
    print(json.dumps(validate_reports(rows["server"], {peer: rows[peer] for peer in PEERS})))
