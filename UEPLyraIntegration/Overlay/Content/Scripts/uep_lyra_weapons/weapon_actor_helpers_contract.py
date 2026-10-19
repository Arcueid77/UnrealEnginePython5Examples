"""Independent native helper output/parent inheritance evidence checks."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

CLASSES = tuple("/ShooterCore/Weapons/"+name+"/B_"+name+".B_"+name+"_C" for name in ("Pistol", "Rifle", "Shotgun"))
PROFILES = ("BlueprintFallback", "Python")
FAKE_CASES = (("negative",-2,0.,False), ("zero",0,0.,False), ("hit",2,0.,True), ("miss",2,0.,False), ("cone",3,5.,True))
OWNERS = ("none", "player", "bot", "unpossessed")
TEAMS = (-1, 2, 300)


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_mode"] == "Standalone", "native weapon helper run failed")
    for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "audio_playback_tested", "real_firing_tested", "health_properties_written", "official_assets_modified", "child_blueprints_modified"):
        require(report[key] is False, "weapon helper scope overclaim: "+key)
    for key in ("actual_child_actor_recursion", "production_classes_restored", "test_actors_destroyed", "all_original_pawn_health_unchanged"):
        require(report[key] is True, "native helper witness/cleanup missing: "+key)
    require(len(report["fake_cases"]) == 30 and len(report["stencil_cases"]) == 72 and len(report["color_cases"]) == 18 and len(report["audio_cases"]) == 12, "native helper matrix incomplete")
    require(Counter((r["class"],r["profile"],r["name"]) for r in report["fake_cases"]) == Counter((c,p,n) for c in CLASSES for p in PROFILES for n,_,_,_ in FAKE_CASES), "weapon fake trace class/profile coverage differs")
    require(Counter((r["class"],r["profile"],r["owner"],r["team"]) for r in report["stencil_cases"]) == Counter((c,p,o,t) for c in CLASSES for p in PROFILES for o in OWNERS for t in TEAMS), "weapon stencil class/owner coverage differs")
    require(Counter((r["class"],r["profile"],r["asset_valid"],r["opt_in"]) for r in report["color_cases"]) == Counter((c,p,a,o) for c in CLASSES for p in PROFILES for a,o in ((False,True),(True,False),(True,True))), "weapon material class/profile coverage differs")
    require(Counter((r["class"],r["profile"],r["existing"]) for r in report["audio_cases"]) == Counter((c,p,e) for c in CLASSES for p in PROFILES for e in (False,True)), "weapon audio class/profile coverage differs")
    for row in report["fake_cases"]:
        require(row["class"] in CLASSES and row["profile"] in PROFILES and row["parent_dispatch_verified"], "actual weapon child did not route through parent")
        number = max(row["number"], 0)
        expected = number if row["wall_enabled"] else 0
        require(len(row["positions"]) == len(row["normals"]) == len(row["surfaces"]) == 1+expected, "native fake-hit arrays/count differ")
        require(row["positions"][0] == row["seed"] and row["normals"][0] == [0.,0.,1.] and row["surfaces"][0] == 0, "original impact seed changed")
        for point, normal, surface in zip(row["positions"][1:], row["normals"][1:], row["surfaces"][1:]):
            require(all(math.isfinite(value) for value in point+normal) and abs(point[0]-row["wall_front_x"]) < .01, "native trace did not hit actual wall")
            require(abs(normal[0]+1.) < .001 and abs(normal[1])+abs(normal[2]) < .001 and surface == 0, "native hit normal/surface differs")
            transverse = math.hypot(point[1]-row["start"][1], point[2]-row["start"][2])
            require(transverse <= math.tan(math.radians(row["angle"]))*(point[0]-row["start"][0])+.02, "fake native hit left original spread cone")
        if row["profile"] == "Python": require(row["delta"]["traces"] == number and row["delta"]["hits"] == expected, "native Python trace routing differs")
    for row in report["stencil_cases"]:
        expected = 0 if row["owner"] in ("player", "bot") else max(0, min(255, row["team"]))
        require(row["parent_dispatch_verified"] and row["child_components"] >= 1 and len(row["values"]) >= 3, "native inherited stencil/child recursion missing")
        require(all(value == expected for value in row["values"]) and row["depth_flags_unchanged"], "actual native stencil result or flags differ")
    for row in report["color_cases"]:
        expected = [.2,.4,.6,1.] if row["asset_valid"] and row["opt_in"] else [.8,.8,.8,1.]
        require(row["parent_dispatch_verified"] and len(row["colors"]) == 2 and row["child_mesh_included"], "native recursive material witness missing")
        require(all(all(abs(a-b) < .0001 for a,b in zip(color,expected)) for color in row["colors"]), "actual native team material color differs")
    for row in report["audio_cases"]:
        require(row["parent_dispatch_verified"] and (row["input_component_retained"] if row["existing"] else row["output_is_null"]), "native audio component reuse/null branch differs")
        if row["profile"] == "Python":
            require(row["delta"]["audio_spawns"] == int(not row["existing"]) and row["delta"]["audio_triggers"] == int(row["existing"]), "native audio API branch differs")
    return dict(status="passed", actual_weapon_child_classes=3, native_helper_cases=132, inherited_parent_methods=4, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
