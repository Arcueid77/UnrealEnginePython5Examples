"""Two-owner native authority damage plus two replicated viewer observations."""
import argparse
import json
import math
from pathlib import Path
from .melee_trace_contract import PLAN, direction_matches_trace
from .melee_hit_montage_contract import require

PEERS = ("A", "B0")
TOTAL = 2*len(PLAN)


def client(report):
    require(report["status"] == "passed" and report["error"] is None and report["peer"] in PEERS and
        report["native_role"] == 2 and report["native_net_mode"] == "Client", "real native owner/viewer report missing")
    for name in ("activation_event_replayed", "callback_replay", "health_properties_written", "ability_granted_by_fixture", "full_acceptance", "packaged_runtime", "physical_input_tested", "packet_loss_tested", "travel_rejoin_tested"):
        require(report[name] is False, "owner scope overclaimed: "+name)
    for name in ("profile_restored", "specs_config_unchanged", "cue_observer_restored", "activation_observers_restored", "observer_scope_closed", "native_floor_archetype_observed"):
        require(report[name] is True, "owner cleanup missing: "+name)
    require(report["native_control_restoration"]["control_rotation"] and report["observation_errors"] == [], "owner control/observation failure")
    require(len(report["requests"]) == len(PLAN) and len(report["views"]) == TOTAL, "owner/viewer native matrix incomplete")
    require(report["shutdown"]["active_count"] == 0 and report["shutdown"]["errors"] == [] and
        report["shutdown"]["scopes_created"] == report["shutdown"]["scopes_closed"] == 5, "owner native montage scope leak")
    for index, row in enumerate(report["requests"]):
        scenario, profile = PLAN[index]
        require((row["index"], row["scenario"], row["profile"]) == (index, scenario, profile) and row["native_request_accepted"] and
            row["native_activation_observed"] and row["native_montage_observed"] and row["native_ended"] and row["native_tasks_after"] == 0,
            "actual native owner ASC activation/montage/End missing")
        require(row["trace_queries"] == row["trace_fallbacks"] == 0, "non-authority owner performed trace business")
        require(row["native_ability_authority"] is False and row["native_activation_mode"] == 2, "actual native owner prediction mode missing")
    for position, row in enumerate(report["views"]):
        peer, index = PEERS[position//len(PLAN)], position%len(PLAN); scenario, profile = PLAN[index]; applied = scenario == "hostile"
        require((row["position"], row["source_peer"], row["index"], row["scenario"], row["profile"]) == (position, peer, index, scenario, profile), "native viewer case identity differs")
        require(row["quiet_ticks"] >= 20 and row["own_health_unchanged"] and row["foreign_ability_idle"] and row["observer_scope_closed"], "native viewer quiet/isolation cleanup failed")
        require(row["target_identity_unique"] is True, "native viewer target identity was ambiguous")
        # The original authority-only Cue retains GAS's local-client-key echo
        # suppression. Both receive Health; only the non-predicting viewer gets
        # this multicast Cue. Do not invent a local cosmetic replay for parity.
        expected_cues = int(applied and peer != report["peer"])
        require(row["native_health_delta"] == (100. if applied else 0.) and len(row["cues"]) == expected_cues, "real replicated native Health/Cue or native prediction filtering differs")
        if applied:
            require(len(row["health_events"]) == 1 and row["health_events"][0]["old"] == 100. and row["health_events"][0]["new"] == 0., "native replicated Health delegate missing")
        if expected_cues:
            cue = row["cues"][0]
            require(cue["source_player_id"] == row["source_player_id"] and cue["original"] == "GameplayCue.Weapon.Melee.Hit" and
                cue["location"] == cue["normal"] == [0., 0., 0.] and cue["source"] is None, "replicated original owner/default Cue differs")
        if not applied: require(row["health_events"] == [], "rejected network trace changed replicated Health")
    return True


def validate(server, viewers):
    require(server["status"] == "passed" and server["error"] is None and server["native_net_mode"] == "DedicatedServer" and
        set(viewers) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "two real native owners/authority missing")
    for peer in PEERS:
        client(viewers[peer]); require(viewers[peer]["player_id"] == server["player_ids"][peer], "native owner identity does not match authority")
    for name in ("server_waited_for_client_process_exit", "profiles_restored", "specs_config_unchanged", "activation_observers_restored", "fixtures_destroyed", "observer_scope_closed"):
        require(server[name] is True, "authority cleanup missing: "+name)
    require(server["observation_errors"] == [] and server["shutdown"]["active_count"] == 0 and server["shutdown"]["errors"] == [] and
        server["shutdown"]["scopes_created"] == server["shutdown"]["scopes_closed"] == 10, "authority observation/scope leak")
    require(len(server["cases"]) == TOTAL, "authority trace matrix incomplete")
    for position, row in enumerate(server["cases"]):
        peer, index = PEERS[position//len(PLAN)], position%len(PLAN); scenario, profile = PLAN[index]; python = profile == "Python"; applied = scenario == "hostile"
        require((row["position"], row["source_peer"], row["index"], row["scenario"], row["profile"]) == (position, peer, index, scenario, profile), "authority case identity differs")
        for name in ("native_activation_observed", "native_montage_observed", "native_ended", "foreign_owner_unchanged", "specs_config_unchanged", "observer_scope_closed"):
            require(row[name] is True, "authority native observation missing: "+name)
        require(row["native_role"] == 3 and row["native_tasks_after"] == 0 and row["quiet_ticks"] >= 20 and row["native_health_delta"] == (100. if applied else 0.), "authority native Health/End differs")
        pre = row["preflight"]
        require(pre["hit"] == (scenario != "miss"), "native authority capsule fixture differs")
        if scenario != "miss": require(pre["target"] == row["target"] and pre["target_asc_valid"] == (scenario != "invalid-asc"), "native authority target/ASC differs")
        if scenario in ("friendly", "occluded", "hostile"):
            require(pre["team_comparison"] == (0 if scenario == "friendly" else 1), "native authority team differs")
            require(row["target_immunity_count_at_activation"] == 0, "native target was not combat-ready after respawn")
        if scenario in ("occluded", "hostile"): require(pre["occluded"] == (scenario == "occluded"), "native authority occlusion differs")
        counts = row["trace_stats"]
        expected = dict(queries=int(python), fallback_queries=int(not python), misses=int(python and scenario == "miss"), invalid_asc=int(python and scenario == "invalid-asc"),
            nondifferent_team=int(python and scenario == "friendly"), occluded=int(python and scenario == "occluded"), root_tasks=int(python and applied), effects=int(python and applied), cues=int(python and applied))
        require(counts == expected and len(row["root_tasks"]) == int(applied), "native authority trace ownership/root witness differs")
        for viewer in PEERS:
            require(row["viewers"][viewer] == viewers[viewer]["views"][position], "native viewer/authority ack records differ")
            require(row["viewers"][viewer]["target_player_name"] == row["target_player_name"], "native viewer bound a different replicated target")
        if applied:
            root = row["root_tasks"][0]
            original = row["original_config"]
            require(direction_matches_trace(root,pre,original) and root["additive"] and root["gravity"] and root["finish_mode"] == 0 and root["curve"] is None and root["finish_velocity"] == [0.,0.,0.] and root["clamp"] == 1000. and
                math.isclose(root["duration"], original["Duration"], abs_tol=1e-6) and math.isclose(root["strength"], original["Strength"]*pre["distance"]/original["Distance"], abs_tol=.01), "native original root options/formula missing")
            require(row["stored_effect_context"]["has_hit"] and row["stored_effect_context"]["hit_actor"] is None and row["stored_effect_context"]["distance"] == 0., "native empty hit context changed")
            require(len(row["health_events"]) == 1 and row["health_events"][0]["old"] == 100. and row["health_events"][0]["new"] == 0., "actual native authority Health delegate missing")
        else: require(row["health_events"] == [], "rejected authority trace changed native Health")
    return dict(status="passed", native_authority_trials=TOTAL, actual_owning_clients=2, native_owner_requests=TOTAL,
        replicated_viewer_trials=2*TOTAL, native_hostile_damage_trials=4, full_acceptance=False, packet_loss_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); args = parser.parse_args(); root = Path(args.directory)
    read = lambda name: json.loads((root/(name+".json")).read_text(encoding="utf-8-sig"))
    print(json.dumps(validate(read("server"), {peer: read(peer) for peer in PEERS})))
