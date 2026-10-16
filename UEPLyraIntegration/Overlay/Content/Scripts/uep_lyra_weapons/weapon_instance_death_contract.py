"""Independent actual Death and dead-equipment skip gate; not synthetic proof."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.death_contract import validate as validate_death, require


def validate(report):
    death = validate_death(report)
    require(report["equipment_observer_profiles_restored"] and report["equipment_observation_errors"] == [] and
        report["fixture_native_empty_slot_switch"] and not report["equipment_lifecycle_replayed"] and
        not report["equipment_animation_state_written"] and not report["natural_destroy_unequip_tested"],
        "dead equipment observer/fixture scope invalid")
    for row in report["cases"]:
        for side, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
            evidence = row[side]["equipment_death"]
            require(evidence["profile"] == profile and evidence["source_item_matches"] and evidence["fixture_profile_restored"] and
                evidence["native_empty_slot"] and evidence["respawn_inventory_model_restored"] and
                evidence["respawn_inventory_model"] == evidence["original_inventory_model"], "dead equipment source/Profile/respawn restore invalid")
            require(len(evidence["events"]) == 1 and "/Weapons/Pistol/B_WeaponInstance_Pistol." in evidence["native_class"], "dead native pistol lifecycle/type not observed")
            event = evidence["events"][0]
            require(event["profile"] == profile and event["before"]["dead_or_dying"] and event["before"] == event["after"],
                "dead unequip changed native animation state or was not truly dead")
            counts = event["counters"]
            require(counts["equips"] == counts["tag_queries"] == counts["layer_picks"] == counts["layers_linked"] == counts["montage_calls"] == 0,
                "dead unequip selected/linked/played an animation")
            require(counts["unequips"] == counts["dead_unequips_skipped"] == int(side == "python") and
                counts["fallback_unequips"] == int(side == "blueprint"), "dead original/Python routing differs")
    policy = report["equipment_policy_shutdown"]
    require(policy["errors"] == [] and policy["active_count"] == policy["script_subscriptions_created"] == 0, "dead equipment policy error/leak")
    return dict(status="passed", bounded_dead_equipment_pairs=death["pairs"], native_death_respawn=True,
        fixture_native_empty_slot_switch=True, natural_destroy_unequip_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
