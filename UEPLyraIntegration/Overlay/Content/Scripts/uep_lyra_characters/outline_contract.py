"""Native material/interface state only; no pixel/rendering or replication claim."""
import argparse
import json
import math
from pathlib import Path
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from .emote_audio_contract import CLASS
PARENT = "/Game/Effects/Materials/PostProcess/MPP_Outline_Inst.MPP_Outline_Inst"

SEED_TEAM, SEED_COLOR = 42., [.125, .25, .5, .75]
PAIRS = (("create", "new", 1, [1., 0., 0., 1.], 1, "owner"),
    ("update", "attached", 2, [0., 0., 1., 1.], 1, "owner"),
    ("detached", "detached", 7, [0., 1., 0., 1.], 1, "owner"),
    ("repeat", "new", 3, [.5, .5, .5, 1.], 2, "owner"),
    ("negative", "new", -1, [.25, .75, 1., 1.], 1, "owner"),
    ("hdr", "new", 5, [-.25, 2., .3, .5], 1, "owner"),
    ("unpossessed-new", "new", 1, [1., 0., 0., 1.], 1, "unpossessed"),
    ("unpossessed-existing", "attached", 8, [0., 1., 1., 1.], 1, "unpossessed"))
PLAN = [(name, profile, kind, team, color, calls, target) for name, kind, team, color, calls, target in PAIRS for profile in ("BlueprintFallback", "Python")]


def near(actual, expected):
    return type(actual) in (int, float) and math.isfinite(actual) and abs(actual-expected) <= 1e-6


def validate(report):
    require(report["status"] == "passed" and not report.get("error") and len(report["cases"]) == len(PLAN), "outline report/matrix incomplete")
    require(report["retained_character_class"] == CLASS and report["native_unpossessed_actor_created_destroyed"] is True and
        report["native_unpossessed_actor_local_control"] is False, "outline native Actor identity/control/lifetime differs")
    startup = report["natural_startup_python_dispatch"]
    require(startup["python_calls"] >= 1 and startup["fallback_calls"] == 0, "natural original BP startup did not enter Python outline policy")
    if report["native_owner_local_control"]:
        require(startup["materials_created"] == startup["blendables_added"] == 1 and startup["scalar_updates"] == startup["vector_updates"] >= 1 and
            report["natural_startup_material_exists"] is True, "natural local outline material was not created by Python")
    else:
        require(startup["materials_created"] == startup["blendables_added"] == startup["scalar_updates"] == startup["vector_updates"] == 0 and
            startup["nonlocal_noops"] == startup["python_calls"], "natural nonlocal outline startup changed native material state")
    for index, row in enumerate(report["cases"]):
        name, profile, kind, team, color, calls, target = PLAN[index]
        local = report["native_owner_local_control"] if target == "owner" else False
        exists = local or kind != "new"
        require((row["name"], row["profile"], row["kind"], row["team"], row["color"], row["calls"], row["target"]) ==
            (name, profile, kind, team, color, calls, target) and row["locally_controlled"] is local and row["bp_reference_call"] is True,
            "outline BP-call plan/local control differs")
        require(row["material_exists"] is exists and row["same_material_across_repeats"] is True and row["native_gc_held_reference_survived"] is True and
            row["native_probe_class_cdo_survived_gc"] is True,
            "outline material/reference/native GC differs")
        if exists:
            require(row["native_material_class"] == "/Script/Engine.MaterialInstanceDynamic" and row["material_parent"] == PARENT and
                near(row["scalar"], float(team) if local else SEED_TEAM) and len(row["vector"]) == 4 and
                all(near(a, b) for a, b in zip(row["vector"], color if local else SEED_COLOR)), "outline native material parameters differ")
        else: require(row["scalar"] is row["vector"] is None, "nonlocal outline invented a material parameter result")
        attached = kind == "attached" or (local and kind == "new")
        require(row["blendable_count"] == int(attached) and row["blendable_references_match"] is True and row["blendable_weights"] == ([1.] if attached else []),
            "native camera interface blendable/detached policy differs")
        counts = row["counters"]
        require(counts["python_calls"] == (calls if profile == "Python" else 0) and counts["fallback_calls"] == (calls if profile == "BlueprintFallback" else 0) and
            counts["nonlocal_noops"] == (calls if profile == "Python" and not local else 0) and
            counts["materials_created"] == counts["blendables_added"] == int(profile == "Python" and local and kind == "new") and
            counts["scalar_updates"] == counts["vector_updates"] == (calls if profile == "Python" and local else 0), "outline selected dispatch/native operation counts differ")
        require(row["original_field_camera_profile_restored"] is True, "outline trial original state not restored")
    for index in range(0, len(PLAN), 2):
        a, b = report["cases"][index:index+2]
        for key in ("material_exists", "scalar", "vector", "blendable_count", "blendable_weights"):
            require(a[key] == b[key], "original/Python outline state differs")
    require(report["original_actor_camera_profile_cdo_inventory_restored"] is True and report["fixture_material_roots_created"] == report["fixture_material_roots_released"] and
        report["fixture_probe_class_roots_created"] == report["fixture_probe_class_roots_released"] and
        report["native_original_material_references_valid_after_gc"] is True, "outline cleanup/native references/root balance differs")
    for key in ("pixels_verified", "outline_rendering_verified", "material_replication_claimed", "whole_character_migrated", "full_acceptance", "production_roots_objects"):
        require(report[key] is False, "outline report overclaims "+key)
    return dict(status="passed", native_bp_call_pairs=8, native_material_camera_interface_software=True, native_held_reference_gc=True,
        pixels_verified=False, material_replication_claimed=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
