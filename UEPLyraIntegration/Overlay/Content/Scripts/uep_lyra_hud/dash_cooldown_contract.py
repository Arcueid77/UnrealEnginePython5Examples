"""Fail-closed gate for the bounded production Dash/original-BP differential."""

CASES = ("initial-ready", "typed-owner-duration", "foreign-owner-ignored",
         "repeated-duration-restarts", "paused-game-time-frozen", "native-countdown-completed",
         "blueprint-profile-resume", "python-profile-resume", "resumed-owner-exact-once",
         "destruct-no-late-delivery", "same-widget-native-reconstruct")


def require(value, reason):
    if not value:
        raise AssertionError(reason)


def validate(report):
    import math
    require(report.get("schema_version") == 1 and report.get("status") == "passed" and report.get("error") is None, "Dash runtime failed/incomplete")
    require(isinstance(report.get("production_widget"), str) and bool(report["production_widget"]), "production Dash not reached")
    for flag in ("full_acceptance", "network_acceptance", "native_dash_producer_tested", "dead_health_tested",
                 "widget_tick_invoked_by_fixture", "lifecycle_event_invoked_by_fixture"):
        require(report.get(flag) is False, "unsupported Dash claim: " + flag)
    require(report.get("compiled_vm_transport") is True, "compiled transport missing")
    require(report.get("material_absolute_tolerance") == 0.00001, "material tolerance changed")
    require(report.get("reconstruct_entry") == "native same-widget AddToViewport after RemoveFromParent; test-owned remount", "native remount evidence missing")
    require(report.get("lifecycle_entry") == "test-owned same-class viewport pair; production mount uses UIExtension pool", "lifecycle ownership not declared")
    require(report.get("paused_wall_seconds", 0) >= 1.0, "real pause missing")
    require([case.get("name") for case in report.get("cases", [])] == list(CASES), "Dash case inventory differs")
    for case in report["cases"]:
        if case["name"] == "destruct-no-late-delivery":
            require(case.get("messages_before") == case.get("messages_after") and type(case.get("messages_before")) is int, "late Dash message delivered")
            continue
        actual, original = case.get("python", {}), case.get("blueprint", {})
        lifecycle = case["name"] == "same-widget-native-reconstruct"
        require(case.get("test_owned_lifecycle_widget") is lifecycle and isinstance(case.get("widget"), str), "case ownership not declared")
        require((case["widget"] == report["production_widget"]) is not lifecycle, "production/lifecycle widget attribution differs")
        require(set(actual) == set(original) == {"duration", "start", "charging", "visibility", "glow", "fill", "active_animation", "inactive_animation"}, "Dash state shape differs")
        for key in actual:
            if key in ("glow", "fill"):
                require(isinstance(actual[key], (int, float)) and isinstance(original[key], (int, float)) and
                        math.isfinite(actual[key]) and math.isfinite(original[key]) and abs(actual[key]-original[key]) <= 0.00001, "Dash material differs")
            else:
                require(actual[key] == original[key], "Dash visual/model differs: " + key)
        require(type(case.get("automatic_ticks")) is int and case["automatic_ticks"] >= 0, "automatic Tick evidence missing")
        profile = "BlueprintFallback" if case["name"] == "blueprint-profile-resume" else "Python"
        require(case.get("profile") == profile, "Dash Profile differs")
    for name, charging, duration in (("typed-owner-duration", True, 4.0), ("repeated-duration-restarts", True, 2.5),
                                     ("native-countdown-completed", False, 2.5), ("same-widget-native-reconstruct", True, 1.0)):
        state = next(case["python"] for case in report["cases"] if case["name"] == name)
        require(state["charging"] is charging and state["duration"] == duration, "Dash effect missing: " + name)
    final = report.get("shutdown", {})
    pool = final.get("pool_lifetime", {})
    require(pool.get("source") == "read-only-native-UIExtension-active-entry-membership" and
            pool.get("active_count") == 0 and pool.get("ticker_active") is False and
            type(pool.get("registered")) is int and pool.get("registered") == pool.get("unregistered") and
            pool.get("errors") == [], "Dash pool sampler retained callbacks/references")
    require(type(final.get("scopes_created")) is int and final["scopes_created"] >= 4 and
            final.get("scopes_closed") == final["scopes_created"] and final.get("active_count") == 0 and
            final.get("errors") == [] and final.get("health_binds") == final.get("health_unbinds") and
            final.get("health_binds", 0) > 0, "Dash final scope/health cleanup incomplete")
    return {"status": "passed", "cases": len(CASES), "bounded_runtime_acceptance": True, "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
