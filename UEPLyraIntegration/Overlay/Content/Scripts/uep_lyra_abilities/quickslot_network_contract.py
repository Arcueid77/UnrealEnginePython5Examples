"""Native authority Quickbar/equipment + two independent client task proofs."""
import argparse
import json
from pathlib import Path
from .quickslot_contract import PLAN, require, validate as validate_client

PEERS = ("A", "B0")


def validate(reports):
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["original_inventory_restored"] and
            server["server_waited_for_client_process_exit"] and server["native_playing_gate"]["native_playing_phase"],
            "Quickslot authority phase/restore/exit proof incomplete")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
                  "inventory_properties_written", "native_rpc_bypassed", "ui_presentation_comparison_tested", "gameplay_event_replication_tested"):
        require(server[field] is False, "unsupported authority Quickslot claim: "+field)
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "Quickslot owner IDs not distinct")
    for peer in PEERS:
        client = reports[peer]; validate_client(client)
        require((client["peer"], client["run_id"], client["player_id"]) == (peer, server["run_id"], server["player_ids"][peer]),
                "Quickslot client identity differs")
        require(client["local_inventory_written"] is False and client["local_movement_written"] is False and
                client["ui_presentation_comparison_tested"] is False and client["gameplay_event_replication_tested"] is False,
                "client bypassed native authority or overclaimed UI/event replication")
    expected = [(peer, index) for peer in PEERS for index in range(len(PLAN)*2)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "native Quickslot authority matrix incomplete")
    for row in server["cases"]:
        peer, index = row["target"], row["index"]
        name, _, selected = PLAN[index//2]
        require((row["name"], row["profile"], row["expected_slot"]) == (name, ("BlueprintFallback", "Python")[index % 2], selected) and
                row["authoritative_role"] == 3 and row["other_inventory_unchanged"], "native Quickslot authority/foreign-owner isolation failed")
        ack = row["client"]
        require((ack["peer"], ack["index"], ack["run_id"]) == (peer, index, server["run_id"]), "foreign Quickslot ack")
        client_row = reports[peer]["cases"][index//2]["python" if index % 2 else "blueprint"]
        require(ack["row"] == client_row and row["authority_inventory"] == client_row["inventory"] and
                row["authority_inventory"]["active"] == selected and row["authority_inventory"]["equipment_instigator_matches"],
                "Quickslot native server equipment differs from independently checked client")
    stats = server["policy_shutdown"]
    require(stats["activations"] > 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["active_count"] == 0 and
            stats["tasks_created"] == stats["activations"]*3 and stats["errors"] == [], "authority Quickslot GAS task leak")
    return dict(status="passed", bounded_network_acceptance=True, owners=2, native_authority_trials=40,
                client_profile_pairs=20, gameplay_event_replication_tested=False, ui_presentation_comparison_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
                              for peer in ("server",)+PEERS})))
