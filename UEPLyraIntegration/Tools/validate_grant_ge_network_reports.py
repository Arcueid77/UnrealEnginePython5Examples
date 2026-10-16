"""Read final native reports only; never starts/imports Unreal."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_world.grant_ge_pad_network_protocol import PEERS, PLAN, require, validate_ack, validate_cases

root = Path(sys.argv[1])
reports = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
run_id = reports["server"]["run_id"]
for peer, row in reports.items():
    require(row["run_id"] == run_id and row["peer"] == peer and row["status"] == "passed" and row["error"] is None,
            "grant-GE peer report failed")
    require(len(row["cases"]) == len(PLAN) and row["players_restored"] is True and row["fixture_scope_closed"] is True and
            row["policy"]["errors"] == [], "grant-GE cases/player/fixture cleanup failed")
    require(row["shutdown"]["status"] == "passed" and row["shutdown"]["hud"]["active_widget_count"] == 0 and
            row["shutdown"]["weapon_observer"]["active_scopes"] == 0 and not row["shutdown"]["weapon_observer"]["ticker_active"],
            "grant-GE HUD/observer shutdown leak")
    for flag in ("full_acceptance", "packaged_runtime", "client_effect_prediction_tested", "client_pad_profile_parity_tested",
                 "physical_client_input_tested", "pad_replication_forced", "handler_called_by_probe", "attributes_written_by_probe"):
        require(row[flag] is False, "unsupported grant-GE claim: "+flag)
validate_cases(reports["server"]["cases"])
for peer in PEERS:
    for packet, ack in zip(reports["server"]["cases"], reports[peer]["cases"]):
        validate_ack(packet, ack, peer, "finished")
print(json.dumps({"status": "passed", "cases": 4, "clients": 2, "run_id": run_id,
    "native_grant_ge_health_and_default_cooldown": True, "full_acceptance": False}))
