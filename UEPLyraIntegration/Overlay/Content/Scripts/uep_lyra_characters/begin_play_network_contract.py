"""Natural actual BeginPlay on both authority and owner network Pawns."""
import argparse
import json
from pathlib import Path
from .visibility_network_contract import server_gate as visibility_server, client_gate as visibility_client, validate as visibility_validate
from .begin_play_contract import scope, counts
from .initial_inventory_contract import require


def server_gate(report):
    result = visibility_server(report, begin_play_migrated=True); scope(report)
    require(report["fixture_cdo_profile_modified_on_network"] is False, "natural network startup cannot claim CDO fixture was unmodified")
    require(set(report["natural_startup_begin_play"]) == {"A", "B0"}, "native BeginPlay authority owners missing")
    for value in report["natural_startup_begin_play"].values(): counts(value, "Python")
    return result


def client_gate(report):
    result = visibility_client(report, begin_play_migrated=True); scope(report); counts(report["natural_startup_begin_play"], "Python")
    require(report["fixture_cdo_profile_modified_on_network"] is False, "natural client startup changed test CDO profile")
    return result


def validate(reports):
    result = visibility_validate(reports, begin_play_migrated=True); server_gate(reports["server"])
    for peer in ("A", "B0"): client_gate(reports[peer])
    return dict(result, native_network_begin_play=True, fixture_cdo_profile_modified_on_network=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
