"""Read completed pad reports; live/native work remains the external driver."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_world.effect_pad_network_protocol import PLAN, PEERS, require, validate_ack, validate_server_cases


def validate(root):
    reports = {peer: json.loads((root / (peer + ".json")).read_text(encoding="utf-8-sig"))
               for peer in ("server",) + PEERS}
    run_id = reports["server"]["run_id"]
    for peer, report in reports.items():
        require(report["run_id"] == run_id and report["peer"] == peer and report["status"] == "passed", "Wrong/incomplete pad report")
        require(len(report["cases"]) == len(PLAN) and report["fixture_delegates_closed"], "Missing pad cases/cleanup")
        require(report["native_health_replication"] and not report["client_effect_prediction_verified"]
                and not report["physical_client_input_tested"] and not report["pad_replication_forced"]
                and not report["overlap_handlers_called_by_probe"] and not report["attributes_written_by_probe"]
                and not report["full_acceptance"], "Pad report proof boundary changed")
        shutdown = report["shutdown"]
        require(shutdown["status"] == "passed" and shutdown["hud"]["active_widget_count"] == 0, "Pad HUD did not close")
        require(shutdown["weapon_observer"]["active_scopes"] == 0 and not shutdown["weapon_observer"]["ticker_active"],
                "Pad weapon observers retained")
    validate_server_cases(reports["server"]["cases"])
    for peer in PEERS:
        for packet, ack in zip(reports["server"]["cases"], reports[peer]["cases"]):
            validate_ack(packet, ack, peer)
    return {"status": "passed", "cases": len(PLAN), "clients": len(PEERS), "run_id": run_id,
            "server_zero_ui": reports["server"]["hud"]["construct_count"] == 0,
            "full_acceptance": False}


if __name__ == "__main__":
    print(json.dumps(validate(Path(sys.argv[1])), indent=2))
