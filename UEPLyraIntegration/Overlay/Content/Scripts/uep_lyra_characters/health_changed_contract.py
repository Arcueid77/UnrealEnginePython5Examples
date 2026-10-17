"""Independent native GAS health/delegate/AI-stimulus acceptance, not call counts alone."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from .emote_audio_contract import CLASS

NAMES = ("player-self", "player-foreign", "ai-self", "ai-foreign", "ai-foreign-healing")
PLAN = [(name, profile) for name in NAMES for profile in ("BlueprintFallback", "Python")]
COUNTERS = ("python_calls", "fallback_calls", "authority_noops", "instigator_noops", "self_noops", "controller_noops", "damage_reports")


def check_case(row, expected, *, authority, actor_keys):
    name, profile = expected; target = "AI" if name.startswith("ai-") else ("B0" if name.startswith("player-B0") else "A")
    require((row["name"], row["profile"], row["target"]) == (name, profile, target) and set(row["actors"]) == set(actor_keys), "native health plan/actors differs")
    require(row["native_gas_producer_called"] is authority, "client mutated health or authority omitted actual GAS producer")
    for key, actor in row["actors"].items():
        selected = profile if key == target else ("Python" if profile == "BlueprintFallback" else "BlueprintFallback")
        active, py = key == target, selected == "Python"
        require(actor["profile"] == selected and actor["authority"] is authority and actor["native_role"] in ((3,) if authority else (1, 2)), "native health profile/authority/role differs")
        delegates = actor["delegates"]
        require(len(delegates) == int(active) and all(item["component_matches"] is True and item["owner_matches"] is True for item in delegates), "native health independent delegate count/payload differs")
        expected_counts = dict.fromkeys(COUNTERS, 0)
        if active:
            expected_counts["python_calls" if py else "fallback_calls"] = 1
            if py:
                guard = "authority_noops" if not authority else ("instigator_noops" if name == "ai-non-playerstate" else ("self_noops" if name.endswith("self") else ("damage_reports" if target == "AI" else "controller_noops")))
                expected_counts[guard] = 1
            old = actor["original_health"]-(5. if name == "ai-foreign-healing" else 0.)
            amount = -3. if name == "ai-foreign-healing" else 5.
            require(abs(delegates[0]["old"]-old) < .01 and abs(delegates[0]["new"]-(old-amount)) < .01 and abs(actor["health"]-(old-amount)) < .01,
                "native GAS/delegate/observed health mismatch")
            if authority:
                require(delegates[0]["instigator"] == row["native_source_instigator"] and row["source_instigator_is_playerstate"] is (name != "ai-non-playerstate"),
                    "native delegate instigator differs from real GAS context/cast branch")
            else: require(delegates[0]["instigator"] is None, "client replica invented an authority effect-context instigator")
        else: require(abs(actor["health"]-actor["original_health"]) < .01, "passive native Actor health changed")
        require(actor["counters"] == expected_counts, "selected health receiver guard/counter mismatch")
    report_event = authority and name in ("ai-foreign", "ai-foreign-healing")
    require(len(row["native_stimuli"]) == int(report_event) and row["native_ai_perception_memory"] is report_event,
        "native AI stimulus/memory missing, duplicated or delivered on a forbidden branch")
    if report_event:
        stimulus = row["native_stimuli"][0]; amount = -3. if name.endswith("healing") else 5.
        require(row["native_ai_perception_memory_stimulus"] == stimulus, "actual native perception memory does not match actual multicast")
        require(stimulus["source"] == row["source_pawn"] and stimulus["strength"] == amount and stimulus["location"] == row["source_location"] and
            stimulus["hit_location"] == [0., 0., 0.] and stimulus["tag"] == "None" and stimulus["sense"] == "/Script/AIModule.AISense_Damage", "native AI stimulus source/raw amount/location/defaults differ")
        if profile == "Python":
            actual = row["actors"][target]["last_report"]
            require(actual["amount"] == amount and actual["instigator"] == row["source_pawn"] and actual["location"] == row["source_location"] and actual["hit_location"] == [0., 0., 0.], "Python native damage-report inputs differ from independent stimulus")
    else: require(row["native_ai_perception_memory_stimulus"] is None, "forbidden branch left native AI perception memory")


def cleanup_gate(report, keys, *, owned):
    cleanup = report["cleanup"]
    for key in ("health_restored", "original_profiles_restored", "original_inventory_restored", "cdo_profile_restored"):
        require(cleanup[key] is True, "native health cleanup failed: "+key)
    observer = cleanup["observer"]; bindings = len(keys)+int(owned)
    require(observer["created"] == observer["closed"] == 1 and observer["bindings_created"] == observer["bindings_closed"] == bindings and
        observer["active"] == 0 and observer["errors"] == [], "native health observer ownership/detach failed")
    if owned:
        require(report["owned_fixture_cleanup"]["owned_pawn_controller_playerstate_producer_destroyed"] is True and
            report["owned_fixture_cleanup"]["original_bot_producer_list_preserved"] is True, "owned native AI fixture survived or original bot list changed")
    for key in ("callback_replayed", "health_properties_written", "sense_report_called_by_fixture", "component_delegate_broadcast_by_fixture",
        "gameplay_state_delivered_by_files", "pixels_verified", "physical_input_tested", "packaged_runtime", "whole_character_migrated", "full_acceptance"):
        require(report[key] is False, "native health report overclaims "+key)


def validate(report):
    require(report["status"] == "passed" and not report.get("error") and report["retained_character_class"] == CLASS and len(report["cases"]) == len(PLAN), "native health standalone incomplete")
    require(report["native_net_mode"] == "Standalone", "health standalone is not actual native standalone")
    for row, expected in zip(report["cases"], PLAN): check_case(row, expected, authority=True, actor_keys=("A", "AI"))
    cleanup_gate(report, ("A", "AI"), owned=True)
    require(report["cleanup"]["observer"]["sense_deliveries"] == 4, "standalone native damage sense delivery total differs")
    require(report["cleanup"]["observer"]["health_deliveries"] == 22, "standalone primary/prime/restore native health delivery total differs")
    return dict(status="passed", native_gas_health_trials=len(PLAN), independent_native_ai_stimuli=4, native_receiver_and_authority_guards=True, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
