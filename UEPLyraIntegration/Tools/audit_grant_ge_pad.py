"""Read defaults and native curve data only; never compile or save assets."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_grant_ge_pad.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

def argument(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))

def path(value):
    return value.get_path_name() if value is not None else None

stage = require_authoring_stage(argument("UEPGrantGEStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
relative = Path("Plugins/GameFeatures/ShooterCore/Content/Blueprint/B_GrantAbilityPad_ApplyGE.uasset")
hashes = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (stage, reference)}
if len(set(hashes.values())) != 1:
    raise RuntimeError("grant-GE stage differs from official reference before authoring")
bp = ue.load_object(ue.find_class("Blueprint"), "/ShooterCore/Blueprint/B_GrantAbilityPad_ApplyGE.B_GrantAbilityPad_ApplyGE")
cdo = bp.GeneratedClass.get_cdo()
effect = cdo.GameplayEffectToApply
report = {"status": "passed", "runtime_acceptance": False, "reference_hashes": hashes,
    "class": path(bp.GeneratedClass), "properties": sorted(cdo.properties()),
    "defaults": {"active": bool(cdo.bActive), "duration": float(cdo.Duration), "text": str(cdo.TextToDisplay),
        "effect": path(effect), "replicates": bool(cdo.get_property("bReplicates"))}, "timelines": []}
if effect is not None:
    report["defaults"]["effect_duration_policy"] = int(effect.get_cdo().DurationPolicy)
for timeline in bp.Timelines:
    row = {"name": timeline.get_name(), "length": float(timeline.TimelineLength), "tracks": []}
    for track in timeline.FloatTracks:
        curve = track.CurveFloat
        row["tracks"].append({"name": str(track.TrackName), "curve": path(curve),
            "samples": [float(curve.call_function("GetFloatValue", value)) for value in (0.0, .25, .5, .75, 1.0)]})
    report["timelines"].append(row)
for file, digest in hashes.items():
    if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
        raise RuntimeError("grant-GE input changed during read-only audit")
Path(argument("UEPGrantGEAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_GRANT_GE_AUDIT_PASSED")
