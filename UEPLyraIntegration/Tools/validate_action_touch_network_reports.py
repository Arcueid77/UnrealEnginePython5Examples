"""Check real two-owner local UMG evidence; do not claim message replication."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_hud.action_touch_network_protocol import PHASES, PEERS, require, validate_ack, validate_phases

root = Path(sys.argv[1])
reports = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
run_id = reports["server"]["run_id"]
for peer, report in reports.items():
    require(report["run_id"] == run_id and report["peer"] == peer and report["status"] == "passed" and report["error"] is None,
            "action-touch native peer failed")
    require(len(report["phases"]) == len(PHASES) and report["action_touch"]["errors"] == [], "action-touch phase/policy failed")
    final_touch = report["shutdown"]["action_touch_observers"]
    require(final_touch["active_count"] == 0 and final_touch["scopes_created"] == final_touch["scopes_closed"] and
            final_touch["errors"] == [], "action-touch final production subscription cleanup failed")
    require(report["shutdown"]["status"] == "passed" and report["shutdown"]["hud"]["active_widget_count"] == 0 and
            report["shutdown"]["weapon_observer"]["active_scopes"] == 0 and not report["shutdown"]["weapon_observer"]["ticker_active"],
            "action-touch native HUD shutdown leaked")
    require(report["synthetic_client_local_typed_message"] is True, "touch producer provenance missing")
    for flag in ("full_acceptance", "packaged_runtime", "physical_touch_tested", "message_network_replication_tested",
                 "native_duration_ability_producer_tested", "player_movement_or_health_written", "production_placement_tested"):
        require(report[flag] is False, "unsupported touch network claim: "+flag)
server = reports["server"]
validate_phases(server["phases"])
for peer in PEERS:
    for packet, ack in zip(server["phases"], reports[peer]["phases"]):
        validate_ack(packet, ack, peer)
print(json.dumps(dict(status="passed", phases=len(PHASES), clients=2, run_id=run_id,
    native_action_touch_two_owner_local_message_lifetime=True, gameplay_message_network_replication=False, full_acceptance=False)))
