"""Expected native loadout semantics, including original unslotted extras."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from .emote_audio_contract import CLASS
from .quickbar_input_contract import DEFINITIONS

P, R, S = DEFINITIONS
PAIRS = (("empty", (), False), ("one", (P,), False), ("three", (P, R, S), False),
    ("duplicate", (P, P), False), ("overflow", (P, R, S, P), False), ("occupied-first", (R,), True))
PLAN = [(name, profile, definitions, occupied) for name, definitions, occupied in PAIRS for profile in ("BlueprintFallback", "Python")]


def expected(index):
    name, profile, definitions, occupied = PLAN[index]
    slots = [P if occupied else None, None, None]
    for number, definition in enumerate(definitions):
        if number < 3 and slots[number] is None: slots[number] = definition
    active = 0 if definitions else -1
    selected = slots[active] if active >= 0 else None
    return dict(items=sorted([P]+list(definitions)), slots=slots, active=active, definition=selected,
        equipment_class=selected.replace("/ID_", "/B_WeaponInstance_").replace(".ID_", ".B_WeaponInstance_") if selected else None,
        stacks=sorted([[definition, 1] for definition in [P]+list(definitions)]))


def natural_grant(value, *, avatar=False):
    require(value["python_calls"] >= 1 and value["fallback_calls"] == 0 and value["grant_calls"] == value["slot_add_attempts"] ==
        value["slot_zero_requests"] == 1, "new Pawn did not naturally execute exactly one Python loadout grant")
    last = value["last_call"]
    require(last["profile"] == "Python" and last["authority"] is True and last["role"] == 3 and last["configured_definitions"] == [P],
        "natural Python loadout type/authority/configuration differs")
    before, after = last["before"], last["after"]
    require(len(after["items"]) == len(before["items"])+1 and [item["definition"] for item in after["items"]] == ([P, P] if avatar else [P]) and
        len(before["items"]) == int(avatar) and after["active"] == 0 and after["slots"][0] is not None and not any(after["slots"][1:]),
        "natural loadout item/slot delta differs")
    if avatar: require(before["slots"] == after["slots"] and before["items"][0] in after["items"], "bare Avatar did not preserve original native slot/item")


def check_trial(row, index):
    name, profile, definitions, occupied = PLAN[index]
    require((row["name"], row["profile"], row["configured_definitions"], row["occupied_first"]) ==
        (name, profile, list(definitions), occupied), "loadout case/configuration order differs")
    require(row["native_character_class"] == CLASS and row["bp_reference_call"] is True and row["native_model"] == expected(index) and
        row["original_item_retained"] is True and row["new_items_are_new_identities"] is True and
        sorted(item["definition"] for item in row["added_items"]) == sorted(definitions) and
        len({item["path"] for item in row["added_items"]}) == len(definitions), "native loadout grant/slot/equipment/original identity differs")
    counts = row["counters"]
    require(counts["python_calls"] == int(profile == "Python") and counts["fallback_calls"] == int(profile == "BlueprintFallback") and
        counts["grant_calls"] == counts["slot_add_attempts"] == (len(definitions) if profile == "Python" else 0) and
        counts["slot_zero_requests"] == int(profile == "Python" and bool(definitions)) and
        all(counts[key] == 0 for key in ("authority_noops", "missing_controller_noops", "missing_inventory_noops", "missing_quickbar_noops")),
        "loadout did not enter exactly selected authority Profile/native operations")
    require(row["configuration_profile_cdo_restored"] is True and row["original_inventory_identities_restored"] is True,
        "loadout trial did not restore exact native state")


def validate(report):
    require(report["status"] == "passed" and not report.get("error") and len(report["cases"]) == len(PLAN), "loadout report/case matrix incomplete")
    natural_grant(report["natural_startup_python_grant"])
    for index, row in enumerate(report["cases"]): check_trial(row, index)
    for index in range(0, len(PLAN), 2): require(report["cases"][index]["native_model"] == report["cases"][index+1]["native_model"], "original/Python loadout differs")
    require(report["original_inventory_identities_restored"] is True and report["configuration_profile_cdo_restored"] is True,
        "loadout final configuration/original identities not restored")
    for key in ("inventory_properties_written", "python_handler_replayed", "whole_character_migrated", "full_acceptance", "replication_tested"):
        require(report[key] is False, "loadout report overclaims "+key)
    return dict(status="passed", native_bp_call_pairs=6, natural_first_pawn_python_grant=True,
        native_overflow_and_occupied_slot_extras_preserved=True, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
