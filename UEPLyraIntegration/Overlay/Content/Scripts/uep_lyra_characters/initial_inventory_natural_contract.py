"""Natural new-Pawn script grants plus unchanged Character clear/death ordering."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.auto_respawn_activation_contract import validate as natural
from .inventory_clear_contract import check_row
from .initial_inventory_contract import require, natural_grant


def validate(report):
    result = natural(report)
    require(report["additional_character_helper_under_test"] == "AddInitialInventory" and report["add_initial_called_by_fixture"] is False and
        report["inventory_properties_written"] is False and report["native_inventory_setup_by_fixture"] is False and
        report["whole_character_migrated"] is False, "natural loadout fixture scope differs")
    natural_grant(report["natural_startup_python_grant"])
    count = 0
    for case in report["cases"]:
        for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
            row = case[key]; check_row(row, profile); natural_grant(row["new_pawn_initial_inventory"])
            require(row["new_pawn_initial_inventory"]["last_call"]["actor"] == row["new_pawn"], "natural grant evidence belongs to another Pawn")
            count += 1
    for row in report["avatar_endplay_cases"]:
        check_row(row, row["profile"], avatar=True); natural_grant(row["new_pawn_initial_inventory"], avatar=True)
        require(row["new_pawn_initial_inventory"]["last_call"]["actor"] == row["new_pawn"], "bare Avatar grant evidence belongs to another Pawn")
        count += 1
    require(count == 10 and report["inventory_fixture_shutdown"] == dict(created=count, closed=count, active=0), "natural loadout inventory observer leak")
    return dict(result, natural_first_pawn_and_ten_replacement_python_grants=True, character_clear_regression=True, whole_character_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
