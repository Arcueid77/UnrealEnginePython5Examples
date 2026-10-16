"""Read retained launcher defaults/signatures; never compile or save assets."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "audit_launchers.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))

def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "get_path_name"):
        return value.get_path_name()
    return str(value)

def audit():
    stage = require_authoring_stage(arg("UEPLauncherStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes, rows = {}, []
    for name in ("B_Launcher", "B_Launcher_Push", "B_Launcher_Up"):
        relative = Path("Plugins/GameFeatures/ShooterCore/Content/Blueprint")/(name+".uasset")
        for root in (stage, reference):
            file = root/relative
            hashes[str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
        if hashes[str(stage/relative)] != hashes[str(reference/relative)]:
            raise RuntimeError("audit requires original, unconfigured launcher: "+name)
        bp = ue.load_object(ue.find_class("Blueprint"), "/ShooterCore/Blueprint/"+name+"."+name)
        cdo = bp.GeneratedClass.get_cdo()
        defaults = {}
        for field in ("Light Color", "Light Intensity", "Light Attenuation", "Glow Intensity", "SphereRadius", "Gameplay Tag",
                      "OverlappingPawn", "Target", "XYBounds", "ZBounds", "Multiplier", "UpOverride", "Use Target",
                      "Do Not Activate on Fall Entry", "MinimumVerticalVelocityAllowed", "bReplicates"):
            if field in cdo.properties():
                defaults[field] = serial(cdo.get_property(field))
        locals_ = []
        for graph in bp.FunctionGraphs:
            for node in graph.Nodes:
                if node.get_class().get_name() == "K2Node_FunctionEntry":
                    locals_.append({"graph": graph.get_name(), "variables": [
                        {"name": str(v.VarName), "default": str(v.DefaultValue)} for v in node.LocalVariables]})
        rows.append({"asset": name, "class": bp.GeneratedClass.get_path_name(), "defaults": defaults,
                     "locals": locals_, "properties": sorted(cdo.properties())})
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("launcher changed during read-only audit")
    return {"status": "passed", "runtime_acceptance": False, "reference_hashes": hashes, "assets": rows}

try:
    report = audit()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(arg("UEPLauncherAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_LAUNCHER_AUDIT_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
