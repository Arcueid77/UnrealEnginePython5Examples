"""Character authority clear, native replication, unchanged foreign inventory."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.auto_respawn_activation_contract import validate_network as natural
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from .inventory_clear_contract import check_row


def validate(reports):
    result = natural(reports)
    for peer, report in reports.items():
        require(report["character_clear_business_migrated"] is True and report["other_character_business_migrated"] is False,
            "network Character helper business scope differs")
        for key in ("character_clear_called_by_fixture", "inventory_properties_written", "native_inventory_setup_by_fixture", "signal_payload_owner_claimed", "character_profile_switch_tested"):
            require(report[key] is False, "unsupported network Character claim: "+key)
        for row in report["cases"]:
            check_row(row, row["profile"], authority=peer == "server")
            if peer == "server":
                foreign = row["server_foreign_inventory"]
                require(foreign["before"] == foreign["after"], "native Character clear changed foreign authority inventory")
        for row in report.get("foreign_cases", []):
            foreign = row["foreign_character_inventory"]
            require(foreign["before"] == foreign["after"], "native Character clear changed foreign client inventory")
        count = len(report["cases"])
        require(report["inventory_fixture_shutdown"] == dict(created=count, closed=count, active=0), "network Character inventory scopes leaked")
    return dict(result, character_native_bp_helper_two_owner_verified=True, whole_character_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
