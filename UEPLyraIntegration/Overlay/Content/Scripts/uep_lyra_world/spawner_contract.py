"""Strict real-player spawner proof; selected original pickup data only."""
import argparse
import json
import math
from pathlib import Path

CASES = ("weapon-new-default-cooldown", "weapon-full-slots", "weapon-duplicate-refill", "weapon-duplicate-full",
         "weapon-new-during-reload", "weapon-reload-guard-disabled", "weapon-duplicate-new-instance",
         "ability-heal-default-cooldown", "ability-full-health")

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def choose_unowned_weapon(owned):
    for name in ("Pistol","Rifle","Shotgun"):
        if "/ShooterCore/Weapons/"+name+"/ID_"+name+".ID_"+name+"_C" not in owned:
            return name
    raise RuntimeError("native fresh-grant fixture requires an unowned original weapon definition")

def equal(a,b):
    if isinstance(a,dict) and isinstance(b,dict):
        return a.keys() == b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(tuple,list)) and isinstance(b,(tuple,list)):
        return len(a) == len(b) and all(equal(x,y) for x,y in zip(a,b))
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b)<.01
    return a == b

def validate(report):
    require(report["status"] == "passed" and len(report["cases"]) == len(CASES), "spawner native matrix incomplete")
    for flag in ("full_acceptance","network_acceptance","packaged_runtime","handler_called_by_probe","give_weapon_called_by_probe",
                 "timeline_driven_by_probe","cooldown_duration_overridden","ammo_properties_written","inventory_properties_written",
                 "health_properties_written","postgame_native_branch_tested","culture_switch_tested"):
        require(report[flag] is False, "unsupported spawner claim: "+flag)
    require(report["actors_created"] == report["actors_destroyed"] == 18 and report["collision_scopes_created"] == report["collision_scopes_closed"] == 18,
            "spawner fixture actor/collision scope leak")
    require(report["message_scope_closed"] is True and report["message_helper_unrooted"] is True and report["original_player_restored"] is True,
            "spawner player/message cleanup incomplete")
    restore = report["player_restore"]
    require(restore["inventory_identity_equal"] and restore["position_error"] < .01 and restore["aim_error"] < .01 and
            restore["movement"] == restore["expected_movement"] and abs(restore["health"]-restore["expected_health"]) < .01,
            "spawner native player restore differs")
    for index,(row,name) in enumerate(zip(report["cases"],CASES)):
        require(row["name"] == name and row["same_class"] is True and row["passed"] is True and equal(row["python"],row["blueprint"]),
                "spawner original BP/Python differs")
        for side in ("python","blueprint"):
            result = row[side]
            require(result["physical_events"] == ["begin","end"] and result["cooldown_duration"] == 10.0,
                    "spawner physical collision/default pickup data missing")
            require(result["fixture_inventory_rollback"] is True and result["reload_tag_removed"] is True,
                    "spawner per-trial native rollback failed")
            expected_delta = 1 if index in (0,4,5,6) else 0
            expected_available = index in (1,3,8)
            expected_health = report["maximum_health"] if index in (7,8) else report["initial_player_health"]
            require(result["item_delta"] == expected_delta and result["available_after_pickup"] is expected_available and
                    abs(result["health"]-expected_health)<.01, "spawner native grant/rejection/heal outcome differs")
            if index == 2:
                require(result["spare_delta"] == 5,"spawner native spare refill differs")
            if name in (CASES[0],CASES[7]):
                require(result["cooldown_completed"] is True and result["curve_matches"] is True and result["respawn_light"] is True,
                        "spawner native default timer/curve/respawn missing")
            if name == CASES[0]:
                require(result["magazine_after"] == result["magazine_before"]-1 and result["native_equipment_matches"] is True,
                        "spawner newly granted native weapon did not actually fire")
            if name == CASES[3]:
                require(result["failure_messages"] == ["Spare Ammo Full"] and result["failure_owner_matches"] is True,
                        "spawner native failure RPC/message missing")
        if name in (CASES[0],CASES[7]):
            require(set(row["observed_cooldowns"]) == {"Python","BlueprintFallback"} and
                    all(9.8 <= t <= 11.0 for t in row["observed_cooldowns"].values()), "spawner default ten-second cooldown differs")
        stats = row["python_counters"]
        require(stats["constructions"] == 1 and stats["begins"] == 1 and stats["ability_gives" if name.startswith("ability") else "weapon_gives"] == 1,
                "Python spawner business bypassed/replayed")
    require(report["policy_shutdown"]["errors"] == [], "Python spawner policy failed")
    return {"status":"passed","bounded_runtime_acceptance":True,"cases":len(CASES),"network_acceptance":False}

if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
