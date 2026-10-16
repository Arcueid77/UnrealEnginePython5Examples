"""Independent native Death server/two-viewer report gate, no Unreal import."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities.death_contract import PLAN, require

PEERS = ("A", "B0")


def cue_model(row):
    cue = row["cues"][0]
    return {key: cue[key] for key in ("raw", "normalized", "matched", "original", "source_tags", "target_tags",
        "location", "normal", "effect_level", "ability_level", "replicate_location")}


def validate_reports(server, clients):
    run = server["run_id"]
    total = len(PLAN)*2*len(PEERS)
    require(set(clients) == set(PEERS) and server["peer"] == "server" and server["server_waited_for_client_process_exit"] and
            server["native_playing_gate"]["native_playing_phase"] and server["real_lethal_gas_damage"], "native Death server/exit gate missing")
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "native Death owners not distinct")
    for peer, report in dict(server=server, **clients).items():
        require(report["status"] == "passed" and report["error"] is None and report["run_id"] == run and report["peer"] == peer,
                "native Death peer failed/foreign")
        for flag in ("full_acceptance", "packaged_runtime", "physical_input_tested", "death_event_sent_by_probe",
                     "ability_activation_called_by_probe", "callback_replay", "health_properties_written", "death_duration_written",
                     "packet_loss_tested", "travel_rejoin_tested"):
            require(report[flag] is False, "unsupported Death network claim: "+flag)
        require(len(report["cases"]) == total, "native Death network matrix incomplete")
        stats = report["policy_shutdown"]
        expected = len(PLAN)*(2 if peer == "server" else 1)
        require(stats["activations"] == stats["cameras_set"] == stats["cues_executed"] == stats["waits_created"] ==
                stats["scopes_created"] == stats["scopes_closed"] == expected and stats["active_count"] == 0 and stats["errors"] == [],
                "native Death peer policy leak/missing executions")
        if peer != "server":
            require(report["cue_observer_restored"] and report["player_id"] == server["player_ids"][peer], "Death viewer/owner mismatch")
    for position, row in enumerate(server["cases"]):
        target, index = PEERS[position//(len(PLAN)*2)], position % (len(PLAN)*2)
        name, profile = PLAN[index//2], ("BlueprintFallback", "Python")[index % 2]
        require((row["position"], row["target"], row["index"], row["name"], row["profile"]) == (position, target, index, name, profile),
                "native Death case ordering changed")
        require(row["other_owner_unchanged"] and row["health_before"] > 0 and row["health_after"] == 0 and row["native_death_started"] and
                row["native_cancelable"] is False and row["native_type_preserved"] and row["respawn_delay_restored"] and
                row["new_pawn"] != row["old_pawn"] and row["respawn_health"] > 0 and row["source_events"] == 1 and
                row["source_event"]["target"] == row["old_pawn"] and
                row["source_observer_kind"] == "native_wait_gameplay_event_on_death" and row["source_delivery_owner_active"] == [True],
                "native authority Death/respawn/owner proof missing")
        require(row["cancel_refused"] == (name == "native-cancel-refused") and row["profile_switched"] == (name == "active-profile-switch"),
                "native authority intervention missing")
        if name in ("native-timer", "native-cancel-refused"):
            require(row["fixture_respawn_delay"] > row["original_duration"] and row["native_elapsed"] >= row["original_duration"]-.15,
                    "native authority Death wait did not complete")
        elif name == "native-auto-respawn":
            require(row["fixture_respawn_delay"] == row["original_respawn_delay"] and
                    abs(row["native_elapsed"]-row["original_respawn_delay"]) < .25, "original respawn preemption differs")
        else: require(row["native_elapsed"] < row["original_duration"]-.5, "native early end/Profile teardown missing")
        if profile == "Python":
            stats = row["counters"]
            require(stats["activations"] == stats["scopes_created"] == stats["scopes_closed"] == 1 and
                    stats["waits_finished"] == int(name in ("native-timer", "native-cancel-refused")), "authority Death callback proof differs")
        for peer in PEERS:
            view = clients[peer]["cases"][position]
            require((view["position"], view["target"], view["index"], view["profile"]) == (position, target, index, profile) and
                    view["native_health_zero_seen"] and view["native_respawn_seen"] and len(view["cues"]) == 1,
                    "real replicated Death/Cue/respawn missing or duplicated")
            cue = view["cues"][0]
            require(cue["target"] == cue["source"] == view["old_pawn"] and
                    cue["raw"] == cue["normalized"] == row["source_event"]["magnitude"] and
                    cue["location"] == cue["normal"] == [0., 0., 0.] and cue["causer"] is None and cue["material"] is None and
                    cue["attach"] is None and cue["effect_level"] == cue["ability_level"] == 1 and not cue["replicate_location"],
                    "native replicated Cue payload changed")
            if peer == target:
                require(view["respawn_delay_restored"] and view["owner_activation_observed"] and view["death_camera_matched"] and view["native_type_preserved"] and
                        view["native_cancelable"] is False and view["owner_event"]["target"] == view["old_pawn"] and
                        cue["instigator"] == view["owner_event"]["instigator"] and cue["context"] == view["owner_event"]["context"] and
                        cue["source_tags"] == view["owner_event"]["source_tags"] and cue["target_tags"] == view["owner_event"]["target_tags"],
                        "native ServerInitiated owning-client path missing")
            if index % 2:
                require(cue_model(view) == cue_model(clients[peer]["cases"][position-1]), "original/Python replicated Cue models differ")
    require(server["source_scopes_created"] == server["source_scopes_closed"] == total, "native server event observer leaked")
    return dict(status="passed", bounded_network_acceptance=True, authority_trials=total, viewers=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    reports = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
    print(json.dumps(validate_reports(reports["server"], {peer: reports[peer] for peer in PEERS})))
