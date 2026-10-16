"""Bounded quickbar UI gate; retain explicit initialization/input gaps."""
import math

CASES = ("native-production-slots", "typed-owner-slots", "foreign-owner-ignored", "empty-slot-message",
         "repeated-native-slot-restore", "invalid-index-preserves-slot", "external-named-query-python",
         "blueprint-profile-resume", "python-profile-resume", "native-mouse-axis-entry",
         "destruct-no-late-delivery", "same-widget-native-reconstruct")


def validate(report):
    def require(value, reason):
        if not value:
            raise AssertionError(reason)
    require(report.get("status") == "passed" and report.get("error") is None, "quickbar run failed/incomplete")
    require(len(report["production_widgets"]) == 3 and len(set(report["production_widgets"])) == 3, "three production slots missing")
    for flag in ("full_acceptance", "network_acceptance", "native_inventory_properties_written", "fixture_lifecycle_event_invoked",
                 "physical_mouse_tested", "native_weapon_switch_tested", "bp_initialization_parity_tested"):
        require(report.get(flag) is False, "unsupported quickbar claim: "+flag)
    require(report.get("external_named_query_migrated") is True, "named query not migrated")
    require(report.get("baseline_init_policy") == "default Python initialization, then BP Profile and explicit listener resume" and
            report.get("mouse_reply_observation") == "native EventReply type; internal handled bit not reflected", "quickbar fixture boundary missing")
    require([case["name"] for case in report["cases"]] == list(CASES), "quickbar case inventory missing/reordered")
    for case in report["cases"]:
        require(case["test_owned_lifecycle_widget"] is (case["name"] in CASES[-2:]), "wrong quickbar lifecycle attribution")
        require(len(case["slots"]) == (1 if case["name"] in ("invalid-index-preserves-slot",)+CASES[-2:] else 3), "quickbar slot evidence missing")
        for row in case["slots"]:
            require(row["python"] == row["blueprint"] and math.isfinite(row["python"]["numeric"]), "quickbar BP/Python differs")
            require(row["profile"] == ("BlueprintFallback" if case["name"] == "blueprint-profile-resume" else "Python"), "wrong quickbar Profile")
    require(all(row["python"]["empty"] is True for row in report["cases"][3]["slots"]), "empty payload not observed")
    final, pool = report["shutdown"], report["shutdown"]["pool_lifetime"]
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] == 12 and
            final["errors"] == [] and final["external_named_query_migrated"] is True and final["named_query_calls"] > 0, "quickbar scope cleanup/query evidence missing")
    require(final["ticks"] > 0 and final["slot_messages"] > 6 and final["mouse_calls"] == 1, "native quickbar entries missing")
    require(pool["active_count"] == 0 and pool["ticker_active"] is False and pool["registered"] == pool["unregistered"] and pool["errors"] == [], "shared pool watch survived quickbar exit")
    return {"status": "passed", "cases": len(CASES), "bounded_runtime_acceptance": True,
            "external_named_query_migrated": True, "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
