"""Actual event -> original latent nodes -> Python decisions -> native RPC gate."""
import argparse
import json
from collections import Counter
from pathlib import Path
from .auto_respawn_helpers_contract import require, validate as helpers
from .auto_respawn_helpers_network_contract import validate as network_helpers
from .auto_respawn_listeners_contract import validate_peer as listeners_peer, validate_listener_row

DURATION, COMPLETED = "Ability.Respawn.Duration.Message", "Ability.Respawn.Completed.Message"


def check_messages(messages, owner_id, *, completion, foreign=False, duration_expected=True):
    duration = [row for row in messages if row["channel"] == DURATION]
    completed = [row for row in messages if row["channel"] == COMPLETED]
    require(len(messages) == len(duration)+len(completed) and len(duration) == (0 if foreign or not duration_expected else 1) and
        len(completed) == int(completion), "native duration/completion delivery missing or duplicated")
    for row in messages:
        require(row["player_id"] == owner_id and row["owner_matches"] is (not foreign), "native message owner/foreign identity differs")
    if duration: require(duration[0]["duration"] == 5., "native respawn payload duration differs")
    for row in completed:
        require(row["verb"] == COMPLETED and row["magnitude"] == 1. and row["target_is_null"] is True and
            row["instigator_tags"] == row["target_tags"] == row["context_tags"] == [], "native completion payload differs")


def check_peer(report, *, activation_business=False):
    listeners_peer(report, event_business=True)
    require(report["death_avatar_event_business_migrated"] is True and report["original_two_native_delay_nodes_reused"] is True and
        report["activation_reset_ui_removal_business_migrated"] is activation_business and report["duration_completion_broadcast_by_fixture"] is False,
        "wrong event batch scope or manufactured messages")
    count = len(report["cases"])*(1 if report["network_acceptance"] else 2)+len(report.get("foreign_cases", []))+len(report.get("avatar_endplay_cases", []))
    require(report["event_fixture_shutdown"] == dict(created=count, closed=count, active=0), "native event message observers leaked")


def check_row(row, name, profile, *, server=False):
    validate_listener_row(row, name, profile)
    final = "BlueprintFallback" if name == "profile-switch-during-death" and profile == "Python" else "Python" if name == "profile-switch-during-death" else profile
    for phase in ("living_query", "dead_query", "after_query"):
        require(row[phase]["should_finish_restart"] is (phase == "dead_query"), "native restart guard lifecycle differs")
    stats = row["event_counters"]
    require(stats["death_events"] == int(profile == "Python") and stats["fallback_death_events"] == int(profile == "BlueprintFallback") and
        stats["avatar_end_events"] == stats["fallback_avatar_end_events"] == 0 and
        stats["duration_messages"] == stats["long_delays_started"] == int(profile == "Python"), "actual native death event dispatch differs")
    require(stats["long_continuations"] == stats["short_continuations"] == stats["short_delays_started"] == int(final == "Python") and
        stats["fallback_long_continuations"] == stats["fallback_short_continuations"] == int(final == "BlueprintFallback"),
        "original latent completion did not traverse final Profile exactly once")
    # Both standalone and dedicated-server rows have Pawn role 3. The original
    # client ability authority mode alone cannot provide a local GameMode.
    authority = row["native_owner_role"] == 3
    require(stats["native_restarts"] == stats["native_completion_rpcs"] == int(final == "Python" and authority) and
        stats["cosmetic_completion_messages"] == int(final == "Python" and authority and not server),
        "Python changed native restart/RPC/cosmetic authority")
    require(row["event_observer_closed"] is True, "event message observer not closed")
    check_messages(row["event_messages"], row["native_player_id"], completion=not server)


def check_avatar_row(row, profile):
    require(row["profile"] == profile and row["native_type_preserved"] is True and row["native_auto_respawn_active"] is True and
        row["native_auto_respawn_still_active"] is True and row["native_owner_role"] == 3 and
        row["native_death_active_before"] is row["native_death_active_after"] is False and row["health_before"] > 0 and
        row["respawn_health"] > 0 and row["old_pawn"] != row["new_pawn"] and .1 <= row["native_elapsed"] < 7. and
        row["specs_unchanged"] is True and row["delay_unchanged"] is True,
        "actual native Avatar destruction/restart/lifetime evidence incomplete")
    require(row["specs_before"] == row["specs_after"] and row["after_query"]["owner_matches"] is True and
        row["after_query"]["dead"] is False and row["after_query"]["listener_cache"] ==
        dict(avatar_matches=True, health_matches=True, health_is_null=False), "forced native Avatar owner/cache/spec restore differs")
    original, raw = row["specs_before"], row["specs_at_restart"]
    missing = Counter(original["classes"])-Counter(raw["classes"])
    require(missing == Counter(["/Game/Weapons/GA_Weapon_AutoReload.GA_Weapon_AutoReload_C",
        "/Game/Weapons/Pistol/GA_Weapon_Reload_Pistol.GA_Weapon_Reload_Pistol_C",
        "/ShooterCore/Weapons/Pistol/GA_Weapon_Fire_Pistol.GA_Weapon_Fire_Pistol_C"]) and
        not (Counter(raw["classes"])-Counter(original["classes"])) and raw["persistent"] == original["persistent"],
        "bare native Avatar destruction changed non-equipment/persistent ability baseline")
    recovery = row["native_quickbar_recovery"]
    require(recovery["required"] is True and recovery["slots_unchanged"] is True and
        recovery["slot_before"] == recovery["slot_after"] >= 0 and len(recovery["calls"]) == 2 and
        recovery["calls"][0] >= 0 and recovery["calls"][0] != recovery["slot_before"] and
        recovery["calls"][1] == recovery["slot_before"], "native Avatar probe equipment/slot restoration incomplete")
    require(row["listener_foreign_events"] == ["endplay"] and row["listener_observer_closed"] is True and
        row["event_observer_closed"] is True and row["after_query"]["should_finish_restart"] is False,
        "forced native Avatar path delivered a fake death or leaked observer")
    stats = row["event_counters"]
    require(stats["avatar_end_events"] == int(profile == "Python") and stats["fallback_avatar_end_events"] == int(profile == "BlueprintFallback") and
        stats["death_events"] == stats["fallback_death_events"] == stats["duration_messages"] == stats["long_delays_started"] ==
        stats["long_continuations"] == stats["fallback_long_continuations"] == 0,
        "forced Avatar EndPlay incorrectly used the death/five-second path")
    for field in ("short_delays_started", "short_continuations", "native_restarts", "native_completion_rpcs", "cosmetic_completion_messages"):
        require(stats[field] == int(profile == "Python"), "forced Avatar native restart dispatch differs: "+field)
    require(stats["fallback_short_continuations"] == int(profile == "BlueprintFallback"), "original forced Avatar continuation missing")
    check_messages(row["event_messages"], row["native_player_id"], completion=True, duration_expected=False)


def validate(report, *, activation_business=False):
    result = helpers(report, event_business=True); check_peer(report, activation_business=activation_business)
    for case in report["cases"]:
        for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")): check_row(case[key], case["name"], profile)
    require(len(report["avatar_endplay_cases"]) == 2 and report["native_avatar_destroy_called_by_fixture"] is True,
        "original/Python actual native Avatar EndPlay pair required")
    for row, profile in zip(report["avatar_endplay_cases"], ("BlueprintFallback", "Python")): check_avatar_row(row, profile)
    require(report["avatar_endplay_cases"][0]["specs_at_restart"] == report["avatar_endplay_cases"][1]["specs_at_restart"],
        "BP/Python raw native Avatar equipment behavior differs before fixture recovery")
    return dict(result, death_restart_event_business_verified=True, forced_avatar_endplay_tested=True, whole_auto_respawn_migrated=False)


def validate_network(reports, *, activation_business=False):
    result = network_helpers(reports, event_business=True)
    for peer, report in reports.items():
        check_peer(report, activation_business=activation_business)
        for row in report["cases"]:
            check_row(row, row["name"], row["profile"], server=peer == "server")
            require(row["native_player_id"] == reports["server"]["player_ids"][row["target"]], "event trial native player differs")
        for row in report.get("foreign_cases", []):
            require(row["event_observer_closed"] is True, "foreign native message observer leaked")
            check_messages(row["event_messages"], reports["server"]["player_ids"][row["target"]], completion=True, foreign=True)
    return dict(result, death_restart_event_business_verified=True, foreign_reliable_completion_observed=True,
        forced_avatar_endplay_tested=False, whole_auto_respawn_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--report"); choice.add_argument("--directory"); args = parser.parse_args()
    if args.report: result = validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))
    else:
        root = Path(args.directory)
        result = validate_network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    print(json.dumps(result))
