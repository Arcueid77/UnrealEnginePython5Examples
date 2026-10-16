"""Read original teleporter CDO/signatures only; never compile/save assets."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="audit_teleporter.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))

def serial(value):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if isinstance(value,(list,tuple)):return [serial(v) for v in value]
    if hasattr(value,"get_path_name"):return value.get_path_name()
    if all(hasattr(value,k) for k in ("x","y","z")):return [float(getattr(value,k)) for k in ("x","y","z")]
    return str(value)

def audit():
    stage=require_authoring_stage(arg("UEPTeleporterStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    relative=Path("Plugins/GameFeatures/ShooterCore/Content/Blueprint/B_Teleport.uasset")
    hashes={str(root/relative):hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (stage,reference)}
    if len(set(hashes.values()))!=1:raise RuntimeError("teleporter audit requires original inputs")
    bp=ue.load_object(ue.find_class("Blueprint"),"/ShooterCore/Blueprint/B_Teleport.B_Teleport");cdo=bp.GeneratedClass.get_cdo()
    fields=("ReceiverOnly","TeleporterHeight","TeleporterWidth","TeleporterEdgeWidth","TeleporterNumPlanes","TeleporterSpread",
        "TeleporterPhase","TeleporterInwardMotion","TeleporterBrigtness","bForceDirection","LaunchOnTeleport","LaunchMultiplier",
        "KeepReleativeEntryUponExit","TeleportingTarget","TeleporterDestination","ReceivingPawn","Overlapping Pawn","bReplicates")
    report={"status":"passed","runtime_acceptance":False,"reference_hashes":hashes,"assets":[{
        "asset":bp.get_path_name(),"class":bp.GeneratedClass.get_path_name(),"properties":sorted(cdo.properties()),
        "defaults":{name:serial(cdo.get_property(name)) for name in fields if name in cdo.properties()},
        "signatures":{name:ue.describe_function(bp.GeneratedClass,name) for name in
            ("Set Teleporter Destination","Teleport Audio for Pawn","Teleport Audio for Grenade","UserConstructionScript")}}]}
    for file,digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=digest:raise RuntimeError("teleporter changed during read-only audit")
    return report

try:report=audit()
except Exception:report={"status":"failed","error":traceback.format_exc()}
Path(arg("UEPTeleporterAuditResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
ue.log("UEP_TELEPORTER_AUDIT_"+report["status"].upper())
if report["status"]!="passed":raise RuntimeError(report["error"])
