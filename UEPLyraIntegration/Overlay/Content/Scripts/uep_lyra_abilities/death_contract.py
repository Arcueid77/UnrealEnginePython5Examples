"""Real lethal GAS -> original/Python death -> cue/native delay/respawn proof."""
import argparse
import json
from pathlib import Path

PLAN = ("native-auto-respawn", "native-timer", "native-cancel-refused", "external-native-end", "active-profile-switch")


def require(condition, message):
    if not condition: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["real_lethal_gas_damage"] is True and
            report["cue_observer_restored"] is True, "native lethal death/cue observation failed")
    for name in ("full_acceptance", "network_acceptance", "packaged_runtime", "death_event_sent_by_probe", "activation_handler_replayed",
                 "task_callbacks_replayed", "health_properties_written", "death_duration_written", "animation_assets_modified"):
        require(report[name] is False, "unsupported native death claim: "+name)
    require([row["name"] for row in report["cases"]] == list(PLAN), "native death matrix incomplete")
    for row in report["cases"]:
        for side in ("blueprint", "python"):
            value = row[side]
            require(value["health_before"] > 0 and value["health_after_damage"] == 0 and value["native_death_started"] and
                    value["native_type_preserved"] and value["native_cancelable"] is False and
                    value["death_camera_matched"] and value["new_pawn"] != value["old_pawn"] and
                    value["respawn_health"] > 0 and value["respawn_input_ready"] and value["source_events"] == value["cue_deliveries"] == 1,
                    "native damage/death/camera/cue/respawn proof missing")
            require(value["respawn_delay_restored"] and value["original_respawn_delay"] > 0,
                    "native respawn fixture did not restore the original per-instance delay")
            source, cue = value["source_event"], value["cue"]
            require(source["target"] == value["old_pawn"] and cue["target"] == cue["source"] == source["target"] and
                    cue["instigator"] == source["instigator"] and cue["context"] == source["context"] and
                    cue["source_tags"] == source["source_tags"] and cue["target_tags"] == source["target_tags"] and
                    cue["raw"] == cue["normalized"] == source["magnitude"], "native death event/cue payload lost across Python")
            require(cue["location"] == cue["normal"] == [0., 0., 0.] and cue["causer"] is None and cue["material"] is None and
                    cue["attach"] is None and cue["effect_level"] == cue["ability_level"] == 1 and cue["replicate_location"] is False,
                    "native death Cue unconnected/default pins changed")
            require(value["cancel_refused"] == (row["name"] == "native-cancel-refused") and
                    value["profile_switched"] == (row["name"] == "active-profile-switch"), "death intervention not exercised")
            if row["name"] in ("native-timer", "native-cancel-refused"):
                require(value["fixture_respawn_delay"] > value["original_duration"], "timer completion was preempted by the respawn fixture")
                require(value["native_elapsed"] >= value["original_duration"]-.15, "death native timer ended early")
            elif row["name"] == "native-auto-respawn":
                require(value["fixture_respawn_delay"] == value["original_respawn_delay"] < value["original_duration"] and
                        abs(value["native_elapsed"]-value["original_respawn_delay"]) < .25,
                        "original native respawn preemption not exercised")
            else: require(value["native_elapsed"] < value["original_duration"]-.5, "external native end/Profile teardown did not finish death")
        require(row["blueprint"]["cue"]["matched"] == row["python"]["cue"]["matched"] and
                row["blueprint"]["cue"]["original"] == row["python"]["cue"]["original"], "death Cue routing tags differ")
        stats = row["python"]["counters"]
        require(stats["activations"] == stats["cameras_set"] == stats["cues_executed"] == stats["waits_created"] ==
                stats["scopes_created"] == stats["scopes_closed"] == 1, "death Python native camera/cue/wait scope count differs")
        require(stats["waits_finished"] == int(row["name"] in ("native-timer", "native-cancel-refused")) and
                stats["native_ends"] == int(row["name"] != "active-profile-switch"), "death native end/delay callback count differs")
    stats = report["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [] and
            report["source_scopes_created"] == report["source_scopes_closed"] == len(PLAN)*2, "native death/source observer leak")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(PLAN), real_lethal_gas_damage=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
