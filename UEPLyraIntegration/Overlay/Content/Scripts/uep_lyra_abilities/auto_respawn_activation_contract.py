"""Full policy natural regression; explicit lifecycle/Reset gate remains separate."""
import argparse
import json
from pathlib import Path
from .auto_respawn_helpers_contract import require
from .auto_respawn_events_contract import validate as events, validate_network as network_events


def check_peer(report):
    require(report["activation_natural_regression_only"] is True and report["full_auto_respawn_acceptance"] is False,
        "natural startup/regression cannot certify Reset/end/removal lifecycle")
    startup = report["activation_startup"]
    profile = report["activation_startup_profile"]
    require(profile in ("Python", "BlueprintFallback"), "explicit original startup Profile missing")
    prefix = "" if profile == "Python" else "fallback_"
    require(startup.get(prefix+"added", 0) == 1 and startup.get(prefix+"avatar_set", 0) >= 1,
        "actual natural OnAbilityAdded/AvatarSet dispatch not observed")
    if not report["network_acceptance"]:
        require(startup.get(prefix+"activated", 0) >= 1, "actual standalone OnSpawn activation not observed")


def check_row(row, name, profile):
    final = "BlueprintFallback" if name == "profile-switch-during-death" and profile == "Python" else "Python" if name == "profile-switch-during-death" else profile
    stats = row["activation_counters"]
    require(stats[("" if final == "Python" else "fallback_")+"avatar_set"] >= 1 and
        stats["native_reset_starts"] == stats["removed"] == stats["fallback_removed"] ==
        stats["end_cleanups"] == stats["fallback_end_cleanups"] == 0,
        "natural respawn duplicated listener registration or ended native ability")
    for phase in ("living_query", "dead_query", "after_query"):
        state = row[phase]["activation_state"]
        require(state["listening"] is True and state["proxy_active"] is True and state["ended"] is False,
            "native ability-owned reset listener not retained across natural lifecycle/Profile: "+phase)


def validate(report):
    result = events(report, activation_business=True); check_peer(report)
    for case in report["cases"]:
        for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")): check_row(case[key], case["name"], profile)
    return dict(result, actual_activation_startup_observed=True, full_auto_respawn_acceptance=False,
        reset_end_removal_lifecycle_verified=False)


def validate_network(reports):
    result = network_events(reports, activation_business=True)
    for report in reports.values():
        check_peer(report)
        for row in report["cases"]: check_row(row, row["name"], row["profile"])
    return dict(result, actual_activation_startup_observed=True, full_auto_respawn_acceptance=False,
        reset_end_removal_lifecycle_verified=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--report"); group.add_argument("--directory"); args = parser.parse_args()
    if args.report: result = validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))
    else:
        root = Path(args.directory)
        result = validate_network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    print(json.dumps(result))
