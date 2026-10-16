"""Validate completed three-process real-owner launcher evidence only."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_world.launcher_network_protocol import PLAN, PEERS, require, validate_ack, validate_cases

root = Path(sys.argv[1])
reports = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
run_id = reports["server"]["run_id"]
for peer, row in reports.items():
    require(row["run_id"] == run_id and row["peer"] == peer and row["status"] == "passed" and row["error"] is None,
            "launcher peer report failed")
    require(len(row["cases"]) == len(PLAN) and row["players_restored"] is True and row["launch_observer_closed"] is True and
            row["policy"]["errors"] == [], "launcher player/observer/policy cleanup failed")
    require(row["shutdown"]["status"] == "passed" and row["shutdown"]["hud"]["active_widget_count"] == 0 and
            row["shutdown"]["weapon_observer"]["active_scopes"] == 0 and not row["shutdown"]["weapon_observer"]["ticker_active"],
            "launcher native HUD/observer shutdown leak")
    for flag in ("full_acceptance", "packaged_runtime", "pad_replication_forced", "handler_called_by_probe",
                 "launch_called_by_probe", "velocity_or_gravity_written", "attributes_written_by_probe",
                 "physical_client_input_tested", "client_pad_profile_parity_tested", "cue_visual_parity_tested"):
        require(row[flag] is False, "unsupported launcher network claim: "+flag)
server = reports["server"]
require(server["actors_created"] == server["actors_destroyed"] == 12 and
        server["scopes_created"] == server["scopes_closed"] == 12, "launcher native fixture leak")
require(set(server["server_restore_evidence"]) == set(PEERS), "launcher native restore observation missing")
for evidence in server["server_restore_evidence"].values():
    require(evidence["position_error"] < .01 and evidence["mode"] == evidence["expected_mode"] and
            evidence["custom_mode"] == evidence["expected_custom_mode"] and
            abs(evidence["health"]-evidence["expected_health"]) < .01, "launcher native restore observation differs")
validate_cases(server["cases"])
for peer in PEERS:
    for packet, ack in zip(server["cases"], reports[peer]["cases"]):
        validate_ack(dict(packet, positions=packet["restore_positions"]), ack, peer, "restored")
print(json.dumps({"status": "passed", "cases": len(PLAN), "clients": 2, "run_id": run_id,
    "native_launcher_real_owner_physics_replication": True, "full_acceptance": False}))
