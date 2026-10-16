"""Gate the specific native Dash/death path, not broad gameplay acceptance."""
CASES = ("native-dash-duration", "native-repeat-request-rejected", "native-countdown-completed",
         "native-death-started", "invalid-health-feedback-rejected")


def require(value, reason):
    if not value:
        raise AssertionError(reason)


def validate(report):
    require(report.get("schema_version") == 1 and report.get("mode") == "native-dash-gas-death-and-invalid-health" and
            report.get("status") == "passed" and report.get("error") is None, "native Dash failed/incomplete")
    require(report.get("native_request_accepted") is True and report.get("native_dash_producer_tested") is True and
            report.get("native_death_event_tested") is True and report.get("dead_health_tested") is True and
            report.get("invalid_health_feedback_tested") is True and report.get("production_widget"), "native effects missing")
    for flag in ("full_acceptance", "network_acceptance", "lethal_damage_tested", "fixture_event_invoked",
                 "ability_or_health_properties_written", "physical_key_input_tested", "duration_broadcast_called_by_fixture",
                 "widget_tick_invoked_by_fixture", "lifecycle_event_invoked_by_fixture"):
        require(report.get(flag) is False, "unsupported native Dash claim: " + flag)
    require(report.get("ability_class") == "/ShooterCore/Game/Dash/GA_Hero_Dash.GA_Hero_Dash_C", "not the original granted Dash ability")
    require([case.get("name") for case in report.get("cases", [])] == list(CASES), "native Dash case inventory differs")
    for index in (0, 2):
        case = report["cases"][index]
        actual, original = case["python"], case["blueprint"]
        require(case["widget"] == report["production_widget"] and case["profile"] == "Python" and
                case["test_owned_lifecycle_widget"] is False and case["automatic_ticks"] > 1, "native Dash attribution differs")
        require(actual["duration"] > 0 and actual["duration"] == original["duration"] and actual["start"] == original["start"] and
                actual["visibility"] == original["visibility"] == 3 and
                abs(actual["glow"]-original["glow"]) < 0.00001 and abs(actual["fill"]-original["fill"]) < 0.00001 and
                actual["charging"] == original["charging"] is (index == 0), "native Dash BP/Python mismatch")
    require(report["cases"][1]["accepted"] is False and report["cases"][1]["duration_deliveries"] == 1, "repeated native activation changed UI")
    death = report["cases"][3]
    require(death["death_state"] in (1, 2) and death["death_callbacks"] == 1 and
            death["python"]["visibility"] == death["blueprint"]["visibility"] == 1, "native death branch not reached")
    invalid = report["cases"][4]
    require(invalid["synthetic_payload"] is True and invalid["owner_has_pawn"] is False and
            invalid["python"] == invalid["blueprint"], "invalid-health fixture differs")
    deliveries = report.get("native_failure_delivery_count")
    require(type(deliveries) is int and deliveries in (0, 1) and report.get("native_failure_producer_tested") is (deliveries == 1), "native failure producer claim differs")
    if deliveries:
        require(report["native_failure_presentation"]["visibility"] == 3, "native failure text not visible")
    for key in ("shutdown", "failure_shutdown"):
        final = report[key]
        require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and
                final["scopes_created"] > 0 and final["errors"] == [], "native UI scopes survived exit")
    pool = report["shutdown"]["pool_lifetime"]
    require(pool["active_count"] == 0 and pool["ticker_active"] is False and pool["registered"] == pool["unregistered"] and pool["errors"] == [], "pool sampler survived native gate")
    return {"status": "passed", "cases": len(CASES), "bounded_runtime_acceptance": True,
            "native_dash_producer_tested": True, "native_failure_producer_tested": deliveries == 1, "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
