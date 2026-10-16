"""Original BP -> same retained Character helper -> Python native operation gate."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from uep_lyra_abilities.auto_respawn_activation_contract import validate as natural
from uep_lyra_abilities.auto_respawn_reset_contract import validate as reset

CLASS = "/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin_C"


def definitions(state): return sorted(item["definition"] for item in state["items"])


def check_row(row, profile, *, authority=True, avatar=False):
    value = row["character_inventory"]; stats = value["counters"]
    require(value["profile"] == profile and value["old_character"] == row["old_pawn"] and value["new_character_class"] == CLASS and
        value["new_character_profile"] == "Python" and value["observer_closed"] is True, "retained Character identity/Profile/observer differs")
    before, after = value["before"], value["after"]
    require(before["controller_valid"] is before["quickbar_valid"] is before["inventory_valid"] is True and
        after["controller_valid"] is after["quickbar_valid"] is after["inventory_valid"] is True and
        definitions(before) == definitions(after) and before["active"] == after["active"] >= 0 and
        len(before["slots"]) == len(after["slots"]), "native Character inventory/slot model not restored")
    calls = stats["python_calls"]+stats["fallback_calls"]
    if avatar:
        require(calls == 0 and before == after and value["last_call"] is None,
            "bare Avatar destruction must not fabricate a Character death/Reset helper call")
        raw, cleanup = value["raw_after_before_fixture_cleanup"], value["native_orphan_cleanup"]
        old = {item["path"]: item for item in before["items"]}; current = {item["path"]: item for item in raw["items"]}
        extra = [item for path, item in current.items() if path not in old]
        require(all(current.get(path) == item for path, item in old.items()) and len(extra) == 1 and
            extra[0]["definition"] == "/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C" and extra[0]["path"] not in raw["slots"] and
            raw["slots"] == before["slots"] and raw["active"] == before["active"] and
            cleanup == dict(required=True, removed_items=extra), "bare native Avatar raw inventory/owned orphan cleanup differs")
        return
    require(value["native_orphan_cleanup"] == dict(required=False, removed_items=[]) and value["raw_after_before_fixture_cleanup"] == after,
        "natural death must not use fixture inventory cleanup")
    require(calls == 1 and stats["python_calls"] == int(profile == "Python") and stats["fallback_calls"] == int(profile == "BlueprintFallback"),
        "original BP did not call only the selected Character helper once")
    last = value["last_call"]
    require(last["actor"] == value["old_character"] and last["profile"] == profile and last["authority"] is authority and
        (last["native_role"] == 3 if authority else last["native_role"] in (1, 2)), "native Character helper authority/dispatch evidence differs")
    if authority:
        empty = value["native_empty_before_new_pawn"]
        require(empty is not None and not any(empty["slots"]) and not empty["items"] and empty["active"] == -1,
            "independent native empty inventory was not observed before replacement Pawn")
        require(not any(last["after"]["slots"]) and not last["after"]["items"] and last["after"]["active"] == -1 and
            last["before"] == before and bool(last["before"]["items"]), "Character helper native clear result differs")
        require(stats["slots_removed"] == (len(before["slots"]) if profile == "Python" else 0) and
            stats["items_removed"] == (len(before["items"]) if profile == "Python" else 0), "native slot/item removal calls differ")
        require(before["items"] != after["items"], "native respawn reused removed item identities unexpectedly")
        require(value["native_signals"], "actual native inventory/QuickBar notifications missing")
    else:
        require(stats["slots_removed"] == stats["items_removed"] == 0 and last["before"] == last["after"],
            "client Character helper bypassed native authority")


def validate(report):
    result = natural(report)
    require(report["character_clear_business_migrated"] is True and report["other_character_business_migrated"] is False,
        "helper-only Character migration scope differs")
    for key in ("character_clear_called_by_fixture", "inventory_properties_written", "native_inventory_setup_by_fixture", "signal_payload_owner_claimed", "character_profile_switch_tested"):
        require(report[key] is False, "unsupported Character helper fixture claim: "+key)
    count = 0
    for case in report["cases"]:
        for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
            check_row(case[key], profile); count += 1
    for row in report["avatar_endplay_cases"]: check_row(row, row["profile"], avatar=True); count += 1
    require(report["inventory_fixture_shutdown"] == dict(created=count, closed=count, active=0), "Character inventory observers leaked")
    return dict(result, character_clear_inventory_native_bp_ingress=True, whole_character_migrated=False)


def validate_reset(report):
    result = reset(report)
    require(report["character_clear_business_migrated"] is True and report["other_character_business_migrated"] is False,
        "Reset Character helper migration scope differs")
    for key in ("character_clear_called_by_fixture", "inventory_properties_written", "native_inventory_setup_by_fixture", "signal_payload_owner_claimed", "character_profile_switch_tested"):
        require(report[key] is False, "unsupported Character Reset fixture claim: "+key)
    for row in report["cases"]: check_row(row, row["profile"])
    require(report["inventory_fixture_shutdown"] == dict(created=8, closed=8, active=0), "Character Reset inventory observers leaked")
    return dict(result, character_clear_native_reset_bp_ingress=True, whole_character_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True); parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    print(json.dumps((validate_reset if args.reset else validate)(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
