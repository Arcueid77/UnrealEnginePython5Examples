"""Real native events -> selected script -> native inventory/respawn evidence."""
import argparse
import json
from pathlib import Path
from .inventory_clear_contract import check_row
from uep_lyra_abilities.auto_respawn_activation_contract import validate as natural, validate_network as network
from uep_lyra_abilities.auto_respawn_reset_contract import validate as reset_gate
from uep_lyra_abilities.auto_respawn_helpers_contract import require

COUNTERS = ("death_python", "death_fallback", "reset_python", "reset_fallback", "clear_forwards")


def header(report):
    require(report["character_clear_business_migrated"] is True and report["character_lifecycle_events_migrated"] is True and
        report["other_remaining_character_business_migrated"] is False and "other_character_business_migrated" not in report,
        "event migration cannot retain the contradictory old helper-only scope claim")
    for key in ("character_events_called_by_fixture", "character_clear_called_by_fixture", "inventory_properties_written",
            "native_inventory_setup_by_fixture", "signal_payload_owner_claimed", "character_profile_switch_tested"):
        require(report[key] is False, "unsupported lifecycle fixture action: "+key)


def event_row(row, profile, *, authority=True, avatar=False, reset=False):
    check_row(row, profile, authority=authority, avatar=avatar)
    value = row["character_lifecycle"]; expected = {key: 0 for key in COUNTERS}
    if not avatar:
        expected[("reset" if reset else "death")+("_python" if profile == "Python" else "_fallback")] = 1
        expected["clear_forwards"] = int(profile == "Python")
    require(value["old_character"] == row["old_pawn"] and value["profile"] == profile and value["pod_only_after_actor_destruction"] is True and
        value["counters"] == expected and value["last_event"] == (None if avatar else "K2_OnReset" if reset else "K2_OnDeathFinished"),
        "native Character event/selected forward count/old-Actor POD scope differs")


def validate(report, *, reset=False):
    result = (reset_gate if reset else natural)(report); header(report); count = 0
    if reset:
        for row in report["cases"]: event_row(row, row["profile"], reset=True); count += 1
    else:
        for case in report["cases"]:
            for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
                event_row(case[key], profile); count += 1
        for row in report["avatar_endplay_cases"]: event_row(row, row["profile"], avatar=True); count += 1
    require(report["inventory_fixture_shutdown"] == dict(created=count, closed=count, active=0), "native lifecycle inventory scopes leaked")
    return dict(result, native_cpp_character_event_to_selected_python_and_inventory=True, native_reset_event_tested=reset,
        callbacks_replayed=False, whole_character_migrated=False)


def validate_network(reports):
    result = network(reports)
    for peer, report in reports.items():
        header(report)
        for row in report["cases"]:
            event_row(row, row["profile"], authority=peer == "server")
            if peer == "server":
                for key in ("server_foreign_inventory", "server_foreign_character_lifecycle"):
                    require(row[key]["before"] == row[key]["after"], "native lifecycle changed foreign authority "+key)
        for row in report.get("foreign_cases", []):
            for key in ("foreign_character_inventory", "foreign_character_lifecycle"):
                require(row[key]["before"] == row[key]["after"], "native lifecycle changed foreign client "+key)
        count = len(report["cases"])
        require(report["inventory_fixture_shutdown"] == dict(created=count, closed=count, active=0), "network lifecycle inventory observers leaked")
    return dict(result, native_cpp_character_death_event_two_owner_verified=True, callbacks_replayed=False, whole_character_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--report"); group.add_argument("--directory"); parser.add_argument("--reset", action="store_true"); args = parser.parse_args()
    if args.directory:
        root = Path(args.directory); result = validate_network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    else: result = validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")), reset=args.reset)
    print(json.dumps(result))
