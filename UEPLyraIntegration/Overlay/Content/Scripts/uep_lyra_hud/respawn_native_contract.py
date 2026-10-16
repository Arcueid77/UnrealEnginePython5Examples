"""Specific original native respawn acceptance, not lethal/network coverage."""
import math


def validate(report):
    def require(value, reason):
        if not value:
            raise AssertionError(reason)
    require(report.get("status") == "passed" and report.get("error") is None and report.get("mode") == "native-gas-auto-respawn", "native respawn failed/incomplete")
    seconds = report.get("native_duration_seconds")
    require(report.get("native_respawn_producer_tested") is True and report.get("native_player_restart_tested") is True and
            report.get("production_widget") and type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0, "native producer/restart missing")
    for flag in ("full_acceptance", "network_acceptance", "synthetic_local_messages", "lethal_damage_tested",
                 "ability_or_health_properties_written", "duration_or_completion_broadcast_called_by_fixture", "fixture_widget_event_invoked", "acoustic_parity_tested"):
        require(report.get(flag) is False, "unsupported native respawn claim: "+flag)
    require([case["name"] for case in report["cases"]] == ["native-death-started", "native-respawn-duration", "native-player-restarted"], "native respawn case inventory differs")
    require(report["cases"][0]["death_state"] in (1, 2), "native death not reached")
    duration = report["cases"][1]
    for case in report["cases"][1:]:
        actual, original = case["python"], case["blueprint"]
        require(actual.keys() == original.keys(), "native respawn state keys differ")
        for key in actual:
            if key in ("duration", "start", "remaining", "numeric", "glow", "fill"):
                require(all(type(state[key]) in (int, float) and math.isfinite(state[key]) for state in (actual, original)) and
                        abs(actual[key]-original[key]) <= 0.00001, "native respawn numeric differs: "+key)
            else:
                require(actual[key] == original[key], "native respawn state differs: "+key)
    require(duration["profile"] == "Python" and duration["python"]["duration"] == duration["blueprint"]["duration"] == report["native_duration_seconds"] and
            duration["python"]["visibility"] == duration["blueprint"]["visibility"] == 0 and
            duration["python"]["timer_active"] is True and duration["python"]["audio_valid"] is True, "native duration UI differs")
    restart = report["cases"][2]
    require(restart["old_pawn"] and restart["new_pawn"] and restart["old_pawn"] != restart["new_pawn"] and
            type(restart["health"]) in (int, float) and math.isfinite(restart["health"]) and restart["health"] > 0 and
            type(restart["native_completion_deliveries"]) is int and restart["native_completion_deliveries"] == 1 and
            restart["python"]["visibility"] == restart["blueprint"]["visibility"] == 1 and
            restart["python"]["timer_active"] is False and restart["blueprint"]["timer_active"] is False, "native respawn effect missing")
    final = report["shutdown"]
    require(final["active_count"] == 0 and final["scopes_created"] > 0 and final["scopes_created"] == final["scopes_closed"] and final["errors"] == [], "native respawn scopes survived exit")
    pool = final["pool_lifetime"]
    require(pool["active_count"] == 0 and pool["ticker_active"] is False and pool["registered"] == pool["unregistered"] and pool["errors"] == [], "native pool watcher survived exit")
    return {"status": "passed", "cases": 3, "bounded_runtime_acceptance": True, "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
