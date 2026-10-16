"""Local team orchestration in three worlds, not a replicated team-change proof."""
import argparse
import json
from pathlib import Path
from .team_cosmetics_contract import validate as local, require


def validate(reports):
    require(set(reports) == {"server", "A", "B0"}, "team requires server and two actual client worlds")
    server = reports["server"]
    require(server["native_playing_gate"]["native_playing_phase"] is True and server["server_waited_for_client_process_exit"] is True and
        server["all_local_checks_complete_before_release"] is True and server["cleanup_frozen_before_release"] is True and
        set(server["player_ids"]) == {"A", "B0"} and len(set(server["player_ids"].values())) == 2,
        "team native Playing/identity/one-way cleanup/exit barriers differ")
    properties = 0
    for peer, report in reports.items():
        properties += local(report)["native_device_scheduler_properties"]
        require(report["peer"] == peer and report["run_id"] == server["run_id"] and report["network_acceptance"] is True and
            report["network_software_only"] is True and report["gameplay_state_delivered_by_files"] is False and
            report["fixture_actor_replication_disabled"] is True and report["native_owner_local_control"] is (peer != "server") and
            report["native_device_subsystem_available"] is (peer != "server") and
            report["player_id"] == server["player_ids"]["A" if peer == "server" else peer] and
            report["native_role"] == (3 if peer == "server" else 2) and
            report["native_net_mode"] == ("DedicatedServer" if peer == "server" else "Client"), "team actual native world/owner context differs")
        require(report["team_change_replication_claimed"] is False and report["material_replication_claimed"] is False,
            "local team software tests cannot certify replicated changes/materials")
        for row in report["cases"]:
            owner = row["target"] == "owner"
            require(row["locally_controlled"] is (owner and peer != "server") and row["player_controlled"] is owner and
                row["platform_user_valid"] is (owner and peer != "server"), "team native platform/local/player context differs")
    return dict(status="passed", native_three_world_team_software=True, native_case_trials=48, native_bp_invocations=60,
        native_natural_startup_python_dispatch_worlds=3, native_device_scheduler_properties=properties,
        team_change_replication_claimed=False, material_replication_claimed=False, pixels_verified=False, hardware_output_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
