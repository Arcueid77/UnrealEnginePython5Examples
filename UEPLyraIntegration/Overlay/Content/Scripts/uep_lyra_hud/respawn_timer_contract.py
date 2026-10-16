"""Fail-closed bounded respawn UI comparison, not whole-version acceptance."""
import math
CASES = ("initial-collapsed", "typed-playerstate-duration", "foreign-pawn-ignored", "repeated-duration-restarts",
         "paused-game-time-frozen", "native-timer-completed", "completion-message-preserves-flag",
         "blueprint-profile-resume", "python-profile-resume", "resumed-message-exact-once",
         "destruct-no-late-delivery", "same-widget-native-reconstruct")


def require(value, reason):
    if not value:
        raise AssertionError(reason)


def validate(report):
    require(report.get("schema_version") == 1 and report.get("status") == "passed" and report.get("error") is None, "respawn failed/incomplete")
    require(report.get("production_widget") and report.get("synthetic_local_messages") is True and
            report.get("audio_component_tested") is True, "production/audio context missing")
    for flag in ("full_acceptance", "network_acceptance", "native_respawn_producer_tested", "fixture_widget_event_invoked", "acoustic_parity_tested"):
        require(report.get(flag) is False, "unsupported respawn claim: "+flag)
    require(report.get("material_absolute_tolerance") == 0.00001 and report.get("paused_wall_seconds", 0) >= 1.0, "tolerance/pause changed")
    require(report.get("remaining_observation") == "derived native deadline, not BP function-local storage", "BP local observation falsely attributed")
    require([case.get("name") for case in report.get("cases", [])] == list(CASES), "respawn cases missing/reordered")
    for case in report["cases"]:
        require(case.get("test_owned_lifecycle_widget") is (case["name"] in CASES[-2:]), "misattributed respawn lifecycle widget")
        actual, original = case["python"], case["blueprint"]
        require(set(actual) == set(original), "respawn state shape differs")
        for key in actual:
            if key in ("glow", "fill", "remaining"):
                require(math.isfinite(actual[key]) and math.isfinite(original[key]) and abs(actual[key]-original[key]) <= 0.00001, "respawn numeric/material differs")
            else:
                require(actual[key] == original[key], "respawn BP/Python differs: "+key)
        require(case["profile"] == ("BlueprintFallback" if case["name"] == "blueprint-profile-resume" else "Python"), "wrong respawn Profile")
    owner = report["cases"][1]["python"]
    require(owner["duration"] == 4.0 and owner["respawning"] is True and owner["visibility"] == 0 and owner["timer_active"] is True and owner["audio_valid"] is True, "respawn didn't start native timer/audio")
    complete = report["cases"][5]["python"]
    require(complete["respawning"] is False and complete["timer_active"] is False and complete["visibility"] == 1, "respawn native Outro didn't finish")
    early = report["cases"][6]["python"]
    require(early["respawning"] is True and early["timer_active"] is False and early["visibility"] == 1, "early completion rewrote original flag")
    final = report["shutdown"]
    require(report.get("lifecycle_entry") == "test-owned same-class viewport pair; production mount uses UIExtension pool" and
            report.get("reconstruct_entry") == "native same-widget AddToViewport after RemoveFromParent; test-owned remount", "native lifecycle entry missing")
    removed, remounted = (case["python"] for case in report["cases"][-2:])
    require(removed["timer_active"] is False and removed["audio_playing"] is False and
            remounted["timer_active"] is True and remounted["duration"] == 1.0 and remounted["visibility"] == 0, "native lifecycle effects missing")
    # Production initial/resumed + isolated initial/remounted = four epochs;
    # each BP counterpart is selected before its first native Construct.
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] == 4 and final["errors"] == [], "respawn scope epochs/cleanup differ")
    pool = final["pool_lifetime"]
    require(pool["active_count"] == 0 and pool["ticker_active"] is False and pool["registered"] == pool["unregistered"] and pool["errors"] == [], "shared pool observer survived shutdown")
    require(final["timer_updates"] > 3 and final["animation_completions"] > 0, "native timer/animation callbacks missing")
    return {"status": "passed", "cases": len(CASES), "bounded_runtime_acceptance": True, "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
