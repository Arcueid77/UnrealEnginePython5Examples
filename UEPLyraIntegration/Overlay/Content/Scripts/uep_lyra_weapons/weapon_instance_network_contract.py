"""Independent default-Python equipment integration atop real reload RPC tests."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.reload_magazine_network_contract import validate as validate_reload, PEERS
from uep_lyra_abilities.reload_magazine_contract import require


def validate(reports):
    reload_result = validate_reload(reports)
    server = reports["server"]; counts = {}
    for peer in ("server",)+PEERS:
        report = reports[peer]; evidence = report["equipment_integration"]
        profile = evidence["profile"]
        require(profile in ("Python", "BlueprintFallback") and profile == server["equipment_integration"]["profile"] and
            evidence["cdo_profile_selector_restored"] and evidence["fixture_cdo_profile_selector_written"] == (profile == "BlueprintFallback"),
            "equipment selected baseline/profile/fixture restore differs")
        require(evidence["read_only"] and evidence["restored"] and evidence["errors"] == [] and
            evidence["scripted_replication"] is False and evidence["animation_state_written"] is False,
            "equipment native observer/restore invalid")
        ids = {str(value) for value in server["player_ids"].values()} if peer == "server" else {str(server["player_ids"][peer])}
        require(set(evidence["initials"]) == ids, "equipment integration actual owner IDs differ")
        for player_id, initial in evidence["initials"].items():
            equip_key, tags_key = ("equips", "tag_queries") if profile == "Python" else ("fallback_equips", "fallback_tag_queries")
            require(initial["source_item_matches"] and initial["profile"] == profile and initial["native_role"] == (3 if peer == "server" else 2) and
                initial["counters"][equip_key] == initial["counters"][tags_key] == 1 and
                initial["state"]["tags"] == initial["native_cosmetic_tags"] and
                initial["state"]["linked_layer"] == initial["state"]["selected_layer"], "native equipped Python source/layer path missing")
            events = [row for row in evidence["events"] if str(row["player_id"]) == player_id and row["native_class"] == initial["native_class"]]
            require([row["equipped"] for row in events] == [True, False] and events[0]["instance"] == events[1]["instance"],
                "native equipment add/remove lifecycle did not pair exactly once")
            for row in events:
                state = row["state"]
                require(state["tags"] == row["native_cosmetic_tags"], "equipment tags differ from this peer's native character parts")
                require(row["profile"] == profile and row["native_role"] == initial["native_role"] and not state["dead_or_dying"] and
                    state["linked_layer"] == state["selected_layer"] and state["montage_playing"] == (state["montage"] is not None),
                    "native replicated equipment role/layer/montage differs")
            stats = events[-1]["counters"]
            unequip_key = "unequips" if profile == "Python" else "fallback_unequips"
            require(stats[equip_key] == stats[unequip_key] == stats[tags_key] == 1,
                "replicated equipment bypassed Python/native factory decisions")
            if profile == "Python": require(stats["layer_picks"] == stats["montage_calls"] == 2, "Python native pair calls differ")
            else: require(all(stats[key] == 0 for key in ("equips", "unequips", "tag_queries", "layer_picks", "montage_calls")), "original BP baseline ran Python business")
            if peer != "server":
                authority = [row for row in server["equipment_integration"]["events"] if str(row["player_id"]) == player_id and row["native_class"] == initial["native_class"]]
                # Dedicated servers deliberately do not spawn cosmetic child actors;
                # their native combined tags are empty. Each peer's tags were checked
                # above against its own native component, not copied across peers.
                for owner_row, server_row in zip(events, authority):
                    owner_state, server_state = owner_row["state"], server_row["state"]
                    require(all(owner_state[key] == server_state[key] for key in ("montage", "montage_playing", "dead_or_dying")),
                        "native owner/authority equipment montage state differs")
                    # Native PickBestAnimLayer consumes the peer-local tags. Female
                    # clients legitimately select a different layer from a server
                    # with no spawned cosmetic actors; actual linked==native-selected
                    # was checked for every event above.
                    if owner_state["tags"] == server_state["tags"]:
                        require(owner_state["selected_layer"] == server_state["selected_layer"], "same native tags selected different layers")
        counts[peer] = len(evidence["events"])
    return dict(status="passed", bounded_equipment_network_integration=True, actual_owners=2,
        native_reload_authority_trials=reload_result["native_authority_trials"], equipment_events=counts, remote_viewer_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
