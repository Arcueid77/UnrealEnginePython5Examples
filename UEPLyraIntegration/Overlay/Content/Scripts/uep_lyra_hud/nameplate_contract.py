"""Pure bounded nameplate report gate, including declared test limitations."""
import math

CASES = ("production-native-indicator-binding", "name-string-text", "native-health-read",
         "team-red-material", "team-blue-material", "owner-name-hidden", "enemy-name-hidden",
         "visibility-no-implicit-restore", "blueprint-profile-resume", "python-profile-resume",
         "repeated-bind-exact-once", "native-indicator-unregister", "viewport-native-destruct",
         "viewport-native-remount")
COUNTERS = ("binds", "unbinds", "init_callbacks", "health_callbacks", "death_callbacks", "team_callbacks",
            "scopes_created", "scopes_closed", "team_proxies_created", "team_proxies_cancelled", "init_bound", "init_unbound", "init_owner_released")


def validate(report):
    if report.get("schema_version") != 1 or report.get("status") != "passed" or report.get("error") is not None:
        raise RuntimeError("nameplate run is incomplete")
    if any(report.get(name) is not False for name in ("full_acceptance", "packaged_runtime", "physical_input_tested",
        "native_damage_producer_tested", "native_team_reassignment_tested", "native_projection_parity_tested")):
        raise RuntimeError("unsupported nameplate acceptance claim")
    if (report.get("actual_production_widget") is not True or report.get("original_bp_baseline") is not True or
            report.get("isolated_viewport_lifecycle") is not True or report.get("business_migration_complete") is not False):
        raise RuntimeError("nameplate fixture scope missing")
    cases = report.get("cases")
    if not isinstance(cases, list) or [row.get("name") for row in cases] != list(CASES):
        raise RuntimeError("nameplate case inventory differs")
    for row in cases:
        if row.get("passed") is not True or row.get("class_preserved") is not True:
            raise RuntimeError("nameplate case did not pass")
        candidate, baseline = row.get("python"), row.get("blueprint")
        if not isinstance(candidate, dict) or not isinstance(baseline, dict) or candidate != baseline:
            raise RuntimeError("nameplate original BP comparison differs")
        percent = candidate.get("health_progress")
        if type(percent) not in (int, float) or not math.isfinite(percent) or not 0 <= percent <= 1:
            raise RuntimeError("nameplate health observation invalid")
        if type(candidate.get("visibility")) is not int or candidate["visibility"] not in range(5):
            raise RuntimeError("nameplate visibility invalid")
        if not isinstance(candidate.get("name"), str) or not isinstance(candidate.get("health_resource"), str):
            raise RuntimeError("nameplate material/name observation missing")
    if report.get("native_unbind_observed") is not True or report.get("no_late_delivery") is not True:
        raise RuntimeError("nameplate native unregister/lifetime proof missing")
    final = report.get("shutdown", {})
    for name in COUNTERS:
        if type(final.get(name)) is not int or final[name] < 0:
            raise RuntimeError("invalid nameplate shutdown counter")
    if final.get("active_count") != 0 or final.get("active_widgets") != [] or final.get("errors") != []:
        raise RuntimeError("nameplate retained bindings/errors")
    for created, closed in (("scopes_created", "scopes_closed"), ("team_proxies_created", "team_proxies_cancelled")):
        if final[created] != final[closed] or final[created] == 0:
            raise RuntimeError("unbalanced or unexercised nameplate binding kind")
    if final["init_unbound"] == 0 or final["init_bound"] != final["init_unbound"] + final["init_owner_released"]:
        raise RuntimeError("unbalanced or unexercised nameplate init-state lifetime")
    if final["init_callbacks"] < 1 or final["team_callbacks"] < 1:
        raise RuntimeError("native immediate callback proof missing")
    return {"status": "passed", "bounded_runtime_acceptance": True, "case_count": len(CASES), "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
