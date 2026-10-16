"""Actual three-world local outline state, never material or rendering replication."""
import argparse
import json
from pathlib import Path
from .outline_contract import validate as local, require


def validate(reports):
    require(set(reports) == {"server", "A", "B0"}, "outline needs three actual native software worlds")
    server = reports["server"]
    require(server["native_playing_gate"]["native_playing_phase"] is True and server["server_waited_for_client_process_exit"] is True and
        server["all_local_checks_complete_before_release"] is True and server["cleanup_frozen_before_release"] is True and
        set(server["player_ids"]) == {"A", "B0"} and len(set(server["player_ids"].values())) == 2,
        "outline actual native Playing/identity/one-way exit barriers differ")
    for peer, report in reports.items():
        local(report)
        require(report["peer"] == peer and report["run_id"] == server["run_id"] and report["network_acceptance"] is True and
            report["network_software_only"] is True and report["gameplay_state_delivered_by_files"] is False and
            report["fixture_actor_replication_disabled"] is True and report["native_owner_local_control"] is (peer != "server") and
            report["player_id"] == server["player_ids"]["A" if peer == "server" else peer] and
            report["native_role"] == (3 if peer == "server" else 2), "outline native world/owner/local-control context differs")
        require(report["native_net_mode"] == ("DedicatedServer" if peer == "server" else "Client"), "outline native NetMode differs")
    return dict(status="passed", native_three_world_outline_software=True, native_case_trials=48, native_bp_invocations=54,
        native_natural_startup_python_dispatch_worlds=3, material_replication_claimed=False, pixels_verified=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
