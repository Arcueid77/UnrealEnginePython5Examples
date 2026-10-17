"""Cross-BP references in three native worlds, not replicated PlayerInfo delivery."""
import argparse
import json
from pathlib import Path
from .team_observer_network_contract import PLAN
from .legacy_player_info_contract import require, check_row, check_scope, check_cleanup


def validate(server, a, b):
    require(server["server_waited_for_client_process_exit"] is True and server["all_cleanup_frozen_before_release"] is True and len(set(server["player_ids"].values())) == 2, "legacy server-last identity/cleanup incomplete")
    for peer, report in (("server", server), ("A", a), ("B0", b)):
        authority = peer == "server"
        require(report["status"] == "passed" and not report.get("error") and report["peer"] == peer and report["run_id"] == server["run_id"] and
            report["native_net_mode"] == ("DedicatedServer" if authority else "Client") and len(report["cases"]) == len(PLAN), "legacy peer/mode/matrix incomplete")
        for row, expected in zip(report["cases"], PLAN):
            name, target, calls, profile = expected
            require((row["name"], row["target"], row["calls"], row["profile"]) == expected and row["native_role"] == (3 if authority else (2 if peer == target else 1)), "legacy Actor identity/role differs")
            check_row(row, profile=profile, calls=calls, user=target == peer)
        check_cleanup(report["cleanup"], network=True, authority=authority); check_scope(report)
        if not authority: require(report["player_id"] == server["player_ids"][peer], "legacy local identity differs")
    return dict(status="passed", typed_bp_legacy_calls=36, same_bp_two_instances_three_worlds=True, real_repnotify_ingress_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate(*(json.loads((root/(name+".json")).read_text(encoding="utf-8-sig")) for name in ("server", "A", "B0")))))
