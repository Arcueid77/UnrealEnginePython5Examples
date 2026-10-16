"""Require real native GAS owner/server proof, shutdown and rollback reports."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_world.heal_ability_network_protocol import PEERS, PLAN, FALSE_CLAIMS, require, validate_ack, validate_cases

root = Path(sys.argv[1])
reports = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
run_id = reports["server"]["run_id"]
for peer, report in reports.items():
    require(report["run_id"] == run_id and report["peer"] == peer and report["status"] == "passed" and report["error"] is None,
            "heal native peer failed")
    require(len(report["cases"]) == len(PLAN), "heal native peer matrix incomplete")
    for flag in FALSE_CLAIMS:
        require(report[flag] is False, "unsupported heal network claim: "+flag)
    require(report["native_inventory_equipment_ability_grant"] is True and report["native_owner_asc_activation"] is True and
            report["client_aim_restored"] is True, "heal native source/request/aim proof missing")
    final = report["shutdown"]["heal_ability_observers"]
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and
            final["timers_created"] == final["timers_cleared"] and final["errors"] == [], "heal native shutdown leaked")
    require(report["shutdown"]["status"] == "passed" and report["shutdown"]["hud"]["active_widget_count"] == 0 and
            report["shutdown"]["weapon_observer"]["active_scopes"] == 0, "heal native HUD shutdown leaked")
server = reports["server"]
require(set(server["native_players_restored"]) == set(PEERS) and all(server["native_players_restored"].values()),
        "heal server players not restored")
validate_cases(server["cases"])
for peer in PEERS:
    for packet, ack in zip(server["cases"], reports[peer]["cases"]):
        validate_ack(packet, ack, peer, "observe")
print(json.dumps(dict(status="passed", cases=len(PLAN), clients=2, run_id=run_id,
    native_heal_equipment_owner_prediction_and_replication=True, full_acceptance=False)))
