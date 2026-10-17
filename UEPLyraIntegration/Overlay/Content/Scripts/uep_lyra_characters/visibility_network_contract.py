"""Natural InitState visibility on actual authority/owner network Pawns."""
import argparse
import json
from pathlib import Path
from .possessed_network_contract import server_gate as possession_server, client_gate as possession_client, validate as possession_validate
from .visibility_contract import scope, natural
from .initial_inventory_contract import require


def server_gate(report, *, begin_play_migrated=False):
    result = possession_server(report, begin_play_migrated=begin_play_migrated); scope(report)
    require(report["network_visibility_repeat_destroy_matrix_tested"] is False, "startup-only network lane cannot certify visibility repeat/destroy matrix")
    require(set(report["natural_startup_visibility"]) == {"A", "B0"}, "authority native visibility owners missing")
    for row in report["natural_startup_visibility"].values(): natural(row["counters"], row["actor"], row["hidden"])
    return result


def client_gate(report, *, begin_play_migrated=False):
    result = possession_client(report, begin_play_migrated=begin_play_migrated); scope(report)
    require(report["network_visibility_repeat_destroy_matrix_tested"] is False, "startup-only client lane cannot certify visibility repeat/destroy matrix")
    row = report["natural_startup_visibility"]; natural(row["counters"], row["actor"], row["hidden"])
    return result


def validate(reports, *, begin_play_migrated=False):
    result = possession_validate(reports, begin_play_migrated=begin_play_migrated); server_gate(reports["server"], begin_play_migrated=begin_play_migrated)
    for peer in ("A", "B0"): client_gate(reports[peer], begin_play_migrated=begin_play_migrated)
    return dict(result, native_network_startup_visibility=True, network_visibility_repeat_destroy_matrix_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
