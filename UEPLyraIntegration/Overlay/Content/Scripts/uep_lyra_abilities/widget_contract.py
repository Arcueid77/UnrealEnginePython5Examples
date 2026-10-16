"""Native OnGive/OnRemove and real UIExtension entry counts, not handle IsValid."""
import argparse
import json
from pathlib import Path
from .jump_contract import require

PLAN = (("jump", 1), ("jump-no-widget", 0), ("shared-empty", 0), ("shared-two", 2))


def validate(report):
    require(report["status"] == "passed" and report["error"] is None, "ability UI native report failed")
    require(report["native_gas_grant_remove"] is True and report["actual_extension_point_count"] >= 1 and
            report["cdo_defaults_restored"] is True and report["original_ability_specs_restored"] is True,
            "ability UI lifecycle/source/restoration missing")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested",
                  "ability_callbacks_replayed", "assets_saved", "native_ui_pool_written"):
        require(report[field] is False, "unsupported UI lifecycle claim: "+field)
    require(len(report["cases"]) == len(PLAN)*2, "ability UI grant matrix incomplete")
    for row, (name, count, profile) in zip(report["cases"],
            ((name, count, profile) for name, count in PLAN for profile in ("BlueprintFallback", "Python"))):
        require((row["name"], row["profile_at_grant"]) == (name, profile) and row["native_type_preserved"] and
                row["specs_added"] == 1 and row["specs_restored"] and row["cdo_restored"],
                "ability grant bypassed native profile/type/spec lifecycle")
        require(row["entries_added"] == count*report["actual_extension_point_count"] and
                row["entries_unchanged_after_profile_switch"] and row["entries_restored_after_remove"],
                "native UI entries leaked, deduplicated or removed at Profile switch")
        require(row["profile_at_remove"] == ("Python" if profile == "BlueprintFallback" else "BlueprintFallback"),
                "UI cleanup did not cross profile ownership")
    require(report["jump_observer_closed"] and report["policy_shutdown"]["active_count"] == 0 and
            report["policy_shutdown"]["errors"] == [], "ability UI shutdown leaked")
    return dict(status="passed", bounded_runtime_acceptance=True, cases=len(PLAN)*2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
