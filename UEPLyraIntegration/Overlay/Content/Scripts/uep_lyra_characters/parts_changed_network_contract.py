"""Real FastArray state and native delegates on two mixed-profile BP instances."""
import argparse
import json
from pathlib import Path
from .parts_changed_contract import CLASS, check_operation, require

PLAN = []
for name, initial, switch in (("mixed", dict(A="BlueprintFallback", B0="Python"), False),
    ("mixed-reversed", dict(A="Python", B0="BlueprintFallback"), False),
    ("switch-between-add-remove", dict(A="BlueprintFallback", B0="Python"), True)):
    for operation in ("add", "remove", "remove-again"):
        profiles = {peer: ("Python" if profile == "BlueprintFallback" else "BlueprintFallback") if switch and operation != "add" else profile for peer, profile in initial.items()}
        PLAN.append((name, operation, profiles))


def validate(reports):
    require(set(reports) == {"server", "A", "B0"}, "native parts need authority and two real clients")
    server = reports["server"]; ids = server["player_ids"]
    require(set(ids) == {"A", "B0"} and len(set(ids.values())) == 2 and server["native_playing_gate"]["native_playing_phase"] is True and
        server["server_waited_for_client_process_exit"] is True and server["all_cleanup_frozen_before_release"] is True,
        "native parts identity/Playing/cleanup/server-last exit barriers differ")
    for peer, report in reports.items():
        require(report["status"] == "passed" and not report.get("error") and report["peer"] == peer and report["run_id"] == server["run_id"] and
            report["player_ids"] == ids and report["native_net_mode"] == ("DedicatedServer" if peer == "server" else "Client") and
            report["network_acceptance"] is True and report["native_world_net_mode_observed"] is True and
            report["native_part_fastarray_replication"] is True and report["local_part_producer_called"] is (peer == "server") and
            len(report["cases"]) == len(PLAN), "native parts actual worlds/local producer/case matrix differs")
        if peer != "server": require(report["player_id"] == ids[peer], "native parts actual client identity differs")
        require(set(report["natural_startup_python_dispatch"]) == {"A", "B0"}, "natural receiver startup missing an actual Pawn")
        for value in report["natural_startup_python_dispatch"].values():
            require(value["fallback_calls"] == 0 and (value["python_calls"] == 0 if peer == "server" else value["python_calls"] >= 1),
                "natural native part renderer/no-renderer callback boundary differs")
        for index, (case, plan) in enumerate(zip(report["cases"], PLAN)):
            name, operation, profiles = plan
            require(case["position"] == index and set(case["actors"]) == {"A", "B0"}, "native parts command/actual Pawn matrix incomplete")
            for target, row in case["actors"].items():
                own = peer == target
                check_operation(row, profile=profiles[target], active=operation != "remove-again", found=True, user=own, callbacks=0 if peer == "server" else 1)
                require(row["retained_class"] == CLASS and row["native_role"] == (3 if peer == "server" else 2 if own else 1) and
                    row["locally_controlled"] is own and row["platform_user_valid"] is own and row["native_team_query"]["part_of_team"] is True,
                    "native mixed-instance type/role/control/platform/team context differs")
                require(row["part_entries"] == row["original_part_entries"]+int(operation == "add") and
                    row["temporary_actors"] == int(peer != "server" and operation == "add"), "native replicated entry/spawn/remove result differs")
        for index in range(3):
            for target in ("A", "B0"):
                a, b = (report["cases"][offset+index]["actors"][target] for offset in (0, 3))
                require(a["visual"] == b["visual"] and [item["color"] for item in a["native_device_properties"]] ==
                    [item["color"] for item in b["native_device_properties"]], "original/Python actual replicated cosmetic state differs")
        cleanup = report["cleanup"]
        require(cleanup["original_parts_and_visual_profiles_restored"] == dict(A=True, B0=True) and cleanup["original_inventory_restored"] is True and
            cleanup["cdo_profile_restored"] is True and cleanup["owned_temporary_actors_destroyed"] is True,
            "native parts original entry/Actor identity/visual/Profile/CDO/inventory scope not restored")
        events, markers, roots = (0, 0, 0) if peer == "server" else (12, 30, 36)
        require(cleanup["delegate_fixture_shutdown"] == dict(created=1, closed=1, bindings_created=2, bindings_closed=2, active=0, deliveries=events, errors=[]) and
            cleanup["native_observation_markers"] == markers and cleanup["native_observation_markers_removed"] is True and
            cleanup["device_roots_created"] == cleanup["device_roots_released"] == roots, "native parts delegate/device marker/root scope differs")
        for key in ("gameplay_state_delivered_by_files", "component_delegate_broadcast_by_fixture", "callback_replayed", "parts_properties_written",
            "all_parts_removed_by_fixture", "pixels_verified", "hardware_output_tested", "whole_character_migrated", "full_acceptance"):
            require(report[key] is False, "native parts replication report overclaims "+key)
    return dict(status="passed", native_authority_part_operations=18, native_client_actor_observations=36,
        native_replicated_part_callback_entries=24, native_device_properties=12, same_bp_mixed_instance_profiles_verified=True,
        native_part_fastarray_replication=True, full_acceptance=False, pixels_verified=False, hardware_output_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
