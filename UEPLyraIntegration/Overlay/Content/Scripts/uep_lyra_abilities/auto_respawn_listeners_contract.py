"""Independent listener ownership/lifetime gate over the actual helper lane."""
import argparse
import json
from pathlib import Path
from .auto_respawn_helpers_contract import require, validate as validate_helpers
from .auto_respawn_helpers_network_contract import validate as validate_network_helpers

PROBE_FIELDS = ("first_clear_health_null", "first_clear_retains_avatar", "alternate_bind_matches",
    "repeat_bind_matches", "cross_profile_clear_health_null", "restored_bind_matches", "native_lifetime_unchanged")


def validate_listener_row(row, name, profile):
    require(set(row["listener_probe"]) == set(PROBE_FIELDS) and all(row["listener_probe"][field] is True for field in PROBE_FIELDS),
        "native listener clear/rebind/cross-Profile probe incomplete")
    for phase in ("living_query", "dead_query", "after_query"):
        cache = row[phase]["listener_cache"]
        require(cache["avatar_matches"] is True and cache["health_matches"] is (phase != "dead_query") and
            cache["health_is_null"] is (phase == "dead_query"), "native listener cached ownership differs: "+phase)
    require(row["listener_foreign_events"] == ["death", "endplay"] and row["listener_observer_closed"] is True,
        "exact listener removal lost/duplicated a foreign native subscriber or leaked fixture")
    stats = row["listener_counters"]
    final = "BlueprintFallback" if name == "profile-switch-during-death" and profile == "Python" else "Python" if name == "profile-switch-during-death" else profile
    initial_prefix, final_prefix = ("" if profile == "Python" else "fallback_"), ("" if final == "Python" else "fallback_")
    require(stats[initial_prefix+"clear_calls"] >= 1 and stats[final_prefix+"bind_calls"] >= 1 and stats[final_prefix+"clear_calls"] >= 1,
        "original native death/avatar events did not dispatch selected listener Profile")
    if final == "Python":
        require(stats["avatar_binds"] >= 1 and stats["health_binds"] >= 1, "Python did not bind actual new Pawn/Health delegates")


def validate_peer(report, *, event_business=False):
    require(report["death_listener_orchestration_migrated"] is True and report["timer_restart_business_migrated"] is event_business and
        report["foreign_native_delegate_delivery_tested"] is True and report["synthetic_delegate_broadcast"] is False,
        "wrong listener-only scope or manufactured delegate delivery")
    closed = report["listener_fixture_shutdown"]
    expected = len(report["cases"])*(1 if report["network_acceptance"] else 2)
    if event_business: expected += len(report.get("avatar_endplay_cases", []))
    require(closed == dict(created=expected, closed=expected, active=0), "native listener fixture scopes leaked/incomplete")


def validate(report):
    result = validate_helpers(report); validate_peer(report)
    for case in report["cases"]:
        for field, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
            validate_listener_row(case[field], case["name"], profile)
    return dict(result, listener_orchestration_verified=True, whole_auto_respawn_migrated=False)


def validate_network(reports):
    result = validate_network_helpers(reports)
    for report in reports.values():
        validate_peer(report)
        for row in report["cases"]: validate_listener_row(row, row["name"], row["profile"])
    return dict(result, listener_orchestration_verified=True, whole_auto_respawn_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--report"); choice.add_argument("--directory"); args = parser.parse_args()
    if args.report: result = validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))
    else:
        root = Path(args.directory)
        result = validate_network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    print(json.dumps(result))
