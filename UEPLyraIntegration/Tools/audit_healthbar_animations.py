"""Read retained UMG material-parameter curves; no compile/save/gameplay."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_healthbar_animations.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
def argument(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))
stage = require_authoring_stage(argument("UEPHealthAnimationStage"), ue.convert_relative_path_to_full(ue.get_content_dir()))
reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
files = [root/"Content/UI/Hud/W_Healthbar.uasset" for root in (stage, reference)]
hashes = {str(file): hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
bp = ue.load_object(ue.find_class("WidgetBlueprint"), "/Game/UI/Hud/W_Healthbar.W_Healthbar")
report = {"status": "passed", "runtime_acceptance": False, "hashes": hashes, "animations": []}
for animation in bp.Animations:
    row = {"name": animation.get_name(), "tracks": []}
    for binding in animation.MovieScene.ObjectBindings:
        for track in binding.Tracks:
            item = {"class": track.get_class().get_name(), "path": track.get_path_name(), "properties": sorted(track.properties()), "sections": []}
            if "Sections" in track.properties():
                for section in track.Sections:
                    value = {"class": section.get_class().get_name(), "scalars": []}
                    if "ScalarParameterNamesAndCurves" in section.properties():
                        for parameter in section.ScalarParameterNamesAndCurves:
                            channel = parameter.ParameterCurve
                            value["scalars"].append({"name": str(parameter.ParameterName),
                                "frames": [int(time.Value) for time in channel.Times], "values": [float(key.Value) for key in channel.Values]})
                    item["sections"].append(value)
            row["tracks"].append(item)
    report["animations"].append(row)
for file, digest in hashes.items():
    if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
        raise RuntimeError("healthbar asset changed during read-only animation audit")
Path(argument("UEPHealthAnimationResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_HEALTH_ANIMATION_AUDIT_PASSED")
