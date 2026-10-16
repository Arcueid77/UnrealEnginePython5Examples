"""Fail-closed external gate for the original native two-owner interaction trial."""
import argparse
import hashlib
import json
import math
from pathlib import Path

SIT = "/ShooterExplorer/Interact/GA_Interaction_Sit.GA_Interaction_Sit_C"
FALSE = ("full_acceptance", "packaged_runtime", "hardware_input_tested", "enhanced_input_pipeline_tested",
         "replicated_duration_message_tested", "synthetic_duration_broadcast", "python_handler_replayed",
         "activation_handler_replayed", "production_widget_reachability_tested")


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def models(left, right):
    require(set(left) == set(right), "interaction UI model shape differs")
    for key in left:
        if key in ("duration", "start", "percent"):
            require(math.isfinite(left[key]) and math.isfinite(right[key]) and abs(left[key]-right[key]) < .00001,
                    "native interaction numeric BP/Python difference")
        else:
            require(left[key] == right[key], "native interaction UI BP/Python difference")


def validate(reports):
    require(set(reports) == {"server", "A", "B0"}, "three original-world peers required")
    for peer, report in reports.items():
        require(report["schema_version"] == 1 and report["status"] == "passed" and report["error"] is None and
                report["peer"] == peer, "original interaction peer failed")
        for field in FALSE:
            require(report[field] is False, "unsupported original interaction claim: "+field)
        require(report["native_interaction_producer_tested"] is True and report["original_world_restored"] is True and
                report["test_owned_ui_pair"] is True, "native original producer/fixture provenance missing")
        require(len(report["cases"]) == (2 if peer == "server" else 1), "original interaction matrix incomplete")
        final = report["shutdown"]
        require(final["active_count"] == 0 and not final["errors"] and
                final["scopes_created"] == final["scopes_closed"], "interaction UI listeners leaked")
    require(reports["A"]["player_id"] != reports["B0"]["player_id"], "interaction owner IDs not distinct")
    require(reports["server"].get("server_waited_for_client_process_exit") is True,
            "server exit was not held until client processes completed")
    for index, target in enumerate(("A", "B0")):
        row = reports[target]["cases"][0]
        require(reports["server"]["cases"][index] == row, "server/owner interaction evidence differs")
        require(row["case_index"] == index and row["target"] == target and row["passed"] is True and
                row["same_class"] is True and row["native_api"] == "TriggerInteraction" and row["original_sit_class"] == SIT,
                "native interaction source/identity differs")
        require(row["original_interactor_count"] == 2 and row["original_native_options"] >= 1 and
                row["native_duration_deliveries"] == 1 and row["automatic_ticks"] >= 3,
                "original grants/native discovery/delivery/tick proof missing")
        first = row["first_observed"]
        require(first["native_sit_instances"] >= 1, "original GAS Sit instance missing")
        models(first["python"], first["blueprint"])
        require(abs(first["python"]["duration"]-.5) < .00001 and first["python"]["visibility"] == 0,
                "native original half-second countdown not visibly observed")
        models(row["final_python"], row["final_blueprint"])
        require(row["final_python"]["visibility"] == 1 and row["final_python"]["percent"] >= 1., "native countdown incomplete")
    return dict(status="passed", native_original_interaction_producer=True, owners=2, cases=2,
                full_acceptance=False, enhanced_input_pipeline_tested=False, replicated_message_bus_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--original-default-audit", required=True)
    parser.add_argument("--prior-combined", required=True)
    args = parser.parse_args()
    root = Path(args.directory)
    report = validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    original = json.loads(Path(args.original_default_audit).read_text(encoding="utf-8-sig"))
    combined = json.loads(Path(args.prior_combined).read_text(encoding="utf-8-sig"))
    require(original["status"] == combined["status"] == "passed", "prior source/asset evidence failed")
    hashes = dict(original["reference_hashes"])
    for entry in combined["input_hashes"]:
        if any(name in entry["path"] for name in ("W_AbilityProgress", "BP_UEPGameplayMessages")) and entry["path"].endswith(".uasset"):
            hashes[entry["path"]] = entry["sha256"]
    require(len(hashes) >= 14, "original producer and UI/transport hashes incomplete")
    for file, expected in hashes.items():
        require(hashlib.sha256(Path(file).read_bytes()).hexdigest().upper() == expected.upper(), "interaction asset changed: "+file)
    report["unchanged_original_and_ui_asset_hashes"] = len(hashes)
    print(json.dumps(report))
