"""Original-BP context preflight, not a pressed-widget migration acceptance."""
import argparse
import json
from pathlib import Path

PLAN = ("inventory", "map")
CLASSES = {name: "/ShooterExplorer/Input/Abilities/GA_Toggle" + suffix + ".GA_Toggle" + suffix + "_C"
           for name, suffix in (("inventory", "Inventory"), ("map", "Map"))}
WIDGETS = dict(inventory="/ShooterExplorer/UserInterface/W_InventoryScreen.W_InventoryScreen_C",
               map="/ShooterExplorer/UserInterface/W_MapScreen.W_MapScreen_C")


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None, "original pressed-widget context failed")
    require(report["runtime_migration_acceptance"] is False and report["full_acceptance"] is False and
            report["physical_input_tested"] is False and report["fixture_granted_abilities"] == 0 and
            report["activation_handler_replayed"] is False and report["widgets_created_by_probe"] is False,
            "unsupported pressed-widget context claim")
    require(report["original_specs_restored"] and report["original_layer_restored"], "original context not restored")
    require([row["target"] for row in report["cases"]] == list(PLAN), "original context matrix incomplete")
    require(report["source_mode"] in ("OriginalBP", "PythonSmoke"), "unknown pressed-widget context source")
    for row in report["cases"]:
        for field in ("original_native_type", "native_input_activated_ability", "widget_active", "widget_owner_correct",
                      "original_menu_layer", "release_does_not_end_ability", "native_close_ended_ability", "layer_restored"):
            require(row[field] is True, "original context missing observation: " + field)
        require(row["input_injections"] >= 1 and row["widget_class"] == WIDGETS[row["target"]] and
                row["native_net_policy"] == 1 and row["native_tasks"] == 0,
                "original context type/input/LocalOnly/no-task source differs")
        require(len(row["original_instance_paths"]) == len(set(row["original_instance_paths"])) == 2 and row["native_close_calls"] >= 1,
                "do not erase the original duplicated native grants or fake closing")
    if report["source_mode"] == "PythonSmoke":
        before, after = report["policy_before"], report["policy_shutdown"]
        require(after["activations"] - before["activations"] == after["pushes_requested"] - before["pushes_requested"] ==
                after["widgets_pushed"] - before["widgets_pushed"] == 4 and after["fallback_activations"] == before["fallback_activations"] and
                after["scopes_created"] - before["scopes_created"] == after["scopes_closed"] - before["scopes_closed"] == 8 and
                after["active_count"] == 0 and after["errors"] == [], "Python smoke did not own four native activations/pushes and their scopes")
    return dict(status="passed", bounded_original_bp_context=report["source_mode"] == "OriginalBP",
                bounded_python_smoke=report["source_mode"] == "PythonSmoke", runtime_migration_acceptance=False, cases=len(PLAN))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
