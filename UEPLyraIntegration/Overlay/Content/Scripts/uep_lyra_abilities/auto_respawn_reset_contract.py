"""Independent real native Reset producer/owner/late-delay acceptance gate."""
import argparse
import json
from pathlib import Path
from .auto_respawn_helpers_contract import require
from .auto_respawn_events_contract import check_messages

PLAN = ("native-reset-live", "native-reset-repeat", "native-reset-pending-long", "native-reset-switch-pending-long")
RESET_CLASS = "/Script/LyraGame.LyraGameplayAbility_Reset"
CHANNEL = "GameplayEvent.Reset"


def check_row(row, *, server=False, owner_client=False):
    pending = "pending-long" in row["name"]
    switched = "switch" in row["name"]
    final = ("BlueprintFallback" if row["profile"] == "Python" else "Python") if switched else row["profile"]
    require(row["native_reset_class"] == RESET_CLASS and row["native_reset_existing_specs"] == 1 and
        row["trigger_entry"] == "SendGameplayEventToActor(GameplayEvent.RequestReset)" and row["native_reset_requests"] == 1,
        "real existing native Reset ability producer missing")
    require(row["old_pawn"] != row["new_pawn"] and row["health_before"] > 0 and row["health_after"] > 0 and
        row["death_after"] == 0 and row["native_type_preserved"] is True and row["delay_unchanged"] is True and
        row["specs_before"] == row["specs_after"] and row["auto_active_before"] is row["auto_active_after"] and
        row["final_profile"] == final and row["runtime_ended"] is False and row["reset_proxy_active"] is True and
        row["ui_valid_before"] is (not server) and row["ui_valid_after"] is row["ui_valid_before"],
        "native Reset state/Profile/UI/spec restoration differs")
    messages = row["reset_messages"]
    require(len(messages) == 1 and messages[0] == dict(channel=CHANNEL, player_id=row["player_id"], owner_matches=True),
        "typed native Reset payload owner missing/duplicated")
    check_messages(row["event_messages"], row["player_id"], completion=not server, duration_expected=pending)
    require(row["elapsed_game_seconds"] >= (5.7 if pending else .3), "Reset observed before original pending deadline")
    stats, ev = row["activation_counters"], row["event_counters"]
    require(stats["native_reset_starts"] == stats["native_reset_cancelled"] == stats["removed"] == stats["fallback_removed"] ==
        stats["end_cleanups"] == stats["fallback_end_cleanups"] == 0, "Reset duplicated or ended its ability-owned lifetime")
    require(stats["reset_messages"] == stats["resets_handled"] == int(final == "Python") and stats["foreign_resets"] == 0 and
        stats["fallback_reset_messages"] == int(final == "BlueprintFallback"), "native Reset Profile handler dispatch differs")
    require(ev["long_continuations"]+ev["fallback_long_continuations"] == int(pending) and
        ev["short_continuations"]+ev["fallback_short_continuations"] == 1 and
        ev["native_restarts"] == ev["native_completion_rpcs"] == int(final == "Python" and not owner_client) and
        ev["cosmetic_completion_messages"] == int(final == "Python" and not server and not owner_client), "pending old delay caused duplicate native restart/completion")
    require(row["observer_closed"] is True and row["original_delay_written"] is False and row["callbacks_replayed"] is False,
        "Reset fixture leaked or fabricated a callback")


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_reset_producer_tested"] is True and
        report["reset_broadcast_by_fixture"] is False and report["full_auto_respawn_acceptance"] is False and
        report["original_profile_restored"] is True and report["original_specs_restored"] is True,
        "bounded native Reset acceptance scope/restoration incomplete")
    expected = [(name, profile) for name in PLAN for profile in ("BlueprintFallback", "Python")]
    require([(row["name"], row["profile"]) for row in report["cases"]] == expected, "native Reset original/Python matrix incomplete")
    for row in report["cases"]: check_row(row)
    require(report["observer_shutdown"] == dict(created=8, closed=8, active=0), "native Reset observer scopes leaked")
    for index in range(0, len(report["cases"]), 2):
        a, b = report["cases"][index:index+2]
        require(a["specs_at_restart"] == b["specs_at_restart"], "original/Python raw Reset ability model differs")
    return dict(status="passed", native_reset_producer_tested=True, pairs=4, full_auto_respawn_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
