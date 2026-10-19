"""Native cached FX Actor creation/reuse/data/order and inherited Fire checks."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .weapon_actor_helpers_contract import CLASSES, PROFILES, require

CASES = ("cold", "reuse", "replace-impact", "fake")
FIELDS = ("WeaponFire", "Weapon Impacts", "Weapon Decals")
FX = ("/Game/Effects/Blueprints/B_WeaponFire.B_WeaponFire_C", "/Game/Effects/Blueprints/B_WeaponImpacts.B_WeaponImpacts_C", "/Game/Effects/Blueprints/B_WeaponDecals.B_WeaponDecals_C")


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_mode"] == "Standalone", "native weapon Fire run failed")
    for field in ("full_acceptance","network_acceptance","packaged_runtime","audio_playback_tested","pixels_tested","real_gas_firing_tested","health_properties_written","begin_play_migrated"):
        require(report[field] is False, "weapon Fire scope overclaim: "+field)
    for field in ("test_actors_destroyed","original_pawn_health_unchanged","fx_observers_removed","original_fx_signatures_restored","production_parent_binding_preserved"):
        require(report[field] is True, "native Fire witness/cleanup missing: "+field)
    require(report["observation_errors"] == [], "native FX observer failed")
    require(Counter((r["class"],r["profile"],r["name"]) for r in report["cases"]) == Counter((c,p,n) for c in CLASSES for p in PROFILES for n in CASES), "native Fire class/profile matrix incomplete")
    for row in report["cases"]:
        require(row["parent_dispatch_verified"] and len(row["events"]) == 3 and tuple(event["class"] for event in row["events"]) == FX, "native FX order/parent dispatch differs")
        for index,event in enumerate(row["events"]):
            require(event["attached_to_weapon_mesh"] and event["positions"] == row["positions"] and event["normals"] == row["normals"] and event["surfaces"] == row["surfaces"], "actual native FX data/attachment differs")
            if index == 0:
                require(event["mesh_is_weapon_mesh"] and all(event["enable_flags"]), "native weapon fire spawn inputs differ")
            if index == 1:
                require(event["muzzle"] == row["muzzle"] and event["distance_threshold"] == 500., "native impact spawn/muzzle input differs")
        require(len(row["positions"]) == len(row["normals"]) == len(row["surfaces"]) == (3 if row["name"] == "fake" else row["input_count"]), "native Fire input/fake arrays differ")
        if row["name"] == "cold": require(not any(row["same_cached"]), "cold Fire unexpectedly reused FX")
        elif row["name"] == "replace-impact": require(row["same_cached"] == [True,False,True], "invalid impact cache did not recreate only that Actor")
        else: require(all(row["same_cached"]), "valid FX cache was recreated")
        if row["profile"] == "Python":
            require(row["delta"]["fx_calls"] == 3 and row["delta"]["spawns"] == (3 if row["name"] == "cold" else 1 if row["name"] == "replace-impact" else 0), "Python native FX dispatch/spawn count differs")
            require(row["delta"]["fake_calls"] == int(row["name"] == "fake"), "original optional fake-helper branch differs")
    return dict(status="passed",native_child_fire_calls=24,native_original_fx_entries=72,full_acceptance=False)


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
