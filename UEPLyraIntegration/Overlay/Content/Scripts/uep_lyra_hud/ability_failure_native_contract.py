"""Pure real-GAS failure UI proof; native engine execution remains external."""
import json
from pathlib import Path
import sys

CASES = ("native-full-magazine-reload-rejected", "native-same-reason-repeat",
         "native-latent-animation-completed", "native-pending-profile-cleanup")
FALSE_CLAIMS = ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_key_input_tested",
                "synthetic_message_broadcast", "failure_handler_called_by_probe", "health_or_ammo_properties_written",
                "ability_or_cost_defaults_changed", "dead_health_branch_tested")
FOREIGN_CASE = "native-real-other-local-controller-filtered"


def require(value, message):
    if not value:
        raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None, "native failure runtime failed")
    require(report["native_ability_producer_tested"] is True and report["native_source_verified"] is True and
            report["original_inventory_unchanged"] is True and report["original_health_unchanged"] is True,
            "native GAS source/state proof missing")
    foreign = report.get("real_foreign_controller_tested", False)
    names = list(CASES[:-1]) + ([FOREIGN_CASE] if foreign else []) + [CASES[-1]]
    require([row["name"] for row in report["cases"]] == names, "native failure matrix incomplete")
    for field in FALSE_CLAIMS:
        require(report[field] is False, "unsupported native failure claim: "+field)
    for index in (0, 1):
        row = report["cases"][index]
        require(row["native_asc_accepted"] is False and row["native_deliveries"] == 1 and row["same_class"] is True and
                row["native_opaque_text_equal"] is True and row["native_payload_owner_correct"] is True and
                row["native_failure_tags"] == ["Ability.ActivateFail.MagazineFull"], "native failure producer provenance differs")
        require(row["python"] == row["blueprint"] and row["python"]["text"] == "Already Full of Ammo" and
                row["python"]["visibility"] == 3, "native failure BP/Python presentation differs")
    require(report["cases"][1]["python_intros_delta"] == 0, "native repeated reason restarted Python toast")
    expiry = report["cases"][2]
    require(expiry["python"] == expiry["blueprint"] and expiry["python"]["visibility"] == 1 and
            expiry["native_delay_callbacks"] >= 1 and expiry["elapsed_seconds"] >= 1., "native failure completion bypassed")
    if foreign:
        require(report["synthetic_native_slate_user_bootstrap"] is True and report["native_slate_user_index"] == 1,
                "secondary native Slate user fixture provenance missing")
        row = report["cases"][3]
        require(row["native_second_local_player"] is True and row["native_player_ids_distinct"] is True and
                row["native_asc_accepted"] is False and row["target_native_deliveries"] == 1 and
                row["first_owner_deliveries"] == 0 and row["first_owner_foreign_deliveries"] == 1 and
                row["first_owner_state_unchanged"] is True and row["first_original_bp_state_unchanged"] is True and
                row["native_payload_owner_correct"] is True, "real other Controller filtering proof missing")
        require(report["native_secondary_player_removed"] is True and report["secondary_inventory_health_unchanged"] is True,
                "secondary native local player/state not restored")
    cleanup = report["cases"][-1]
    require(cleanup["state_unchanged"] is True and cleanup["no_pending_animations"] is True and
            cleanup["old_python_scope_closed"] is True and cleanup["original_proxy_inactive"] is True,
            "native failure pending work survived Profile switch")
    final = report["shutdown"]
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and
            final["tickers_created"] == final["tickers_closed"] and final["errors"] == [], "native failure scopes leaked")
    return dict(status="passed", cases=len(names), native_ability_failure_producer=True, real_other_controller=foreign, full_acceptance=False)


if __name__ == "__main__":
    print(json.dumps(validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig")))))
