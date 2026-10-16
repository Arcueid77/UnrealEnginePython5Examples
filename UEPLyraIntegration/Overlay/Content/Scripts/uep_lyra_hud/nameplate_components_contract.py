"""Gate native component/BP comparisons, without claiming the whole batch."""
import math

CASES = ("production-local-manager-and-sources", "original-bp-discovery-parity",
         "native-character-source-add", "native-pawn-source-add", "targeted-discovery",
         "original-duplicate-descriptor-policy", "source-profile-resume", "manager-profile-resume",
         "native-source-endplay-remove", "native-nonlocal-manager-destroy", "native-baseline-manager-endplay")


def validate(report):
    if report.get("schema_version") != 1 or report.get("status") != "passed" or report.get("error") is not None:
        raise RuntimeError("nameplate component run incomplete")
    for name in ("full_acceptance", "network_acceptance", "packaged_runtime", "fixture_lifecycle_event_invoked",
                 "native_health_team_inventory_written", "projection_parity_tested", "legacy_policy_silently_fixed"):
        if report.get(name) is not False:
            raise RuntimeError("unsupported component claim: " + name)
    if report.get("actual_production_manager") is not True or report.get("native_indicator_membership_read") is not True:
        raise RuntimeError("production/native membership evidence missing")
    cases = report.get("cases", [])
    if [row.get("name") for row in cases] != list(CASES):
        raise RuntimeError("component case inventory differs")
    for row in cases:
        if row.get("passed") is not True or row.get("same_class") is not True:
            raise RuntimeError("component case did not pass")
        if row.get("python") != row.get("blueprint"):
            raise RuntimeError("original component BP comparison differs")
    if not all(report.get(name) is True for name in ("native_source_endplay", "native_nonlocal_destroy",
           "native_baseline_endplay", "legacy_duplicate_confirmed", "fixture_only_orphans_cleaned")):
        raise RuntimeError("component lifetime/legacy behavior proof missing")
    if type(report.get("elapsed_seconds")) not in (int, float) or not math.isfinite(report["elapsed_seconds"]):
        raise RuntimeError("invalid component elapsed time")
    for key in ("source_shutdown", "manager_shutdown"):
        state = report.get(key, {})
        if state.get("active_count") != 0 or state.get("errors") != []:
            raise RuntimeError("component callbacks retained at shutdown")
        for opened, closed in (("scopes_created", "scopes_closed"), ("helpers_rooted", "helpers_unrooted")):
            if type(state.get(opened)) is not int or state[opened] <= 0 or state[opened] != state.get(closed):
                raise RuntimeError("component scope/helper lifetime unbalanced")
    return {"status": "passed", "case_count": len(CASES), "bounded_runtime_acceptance": True, "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
