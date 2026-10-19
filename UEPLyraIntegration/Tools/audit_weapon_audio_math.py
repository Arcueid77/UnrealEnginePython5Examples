"""Read-only static audio helper ABI, full graph/default and local-variable audit."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="audit_weapon_audio_math.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics

METHODS=("GetSideReflectionAngles","Calculate Whiz By")
PACKAGE="/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions"
RELATIVE="Plugins/GameFeatures/ShooterCore/Content/System/Audio/WeaponAudioFunctions.uasset"


def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))
def local_rows(graph):
    rows=[]
    for node in graph.Nodes:
        if node.get_class().get_name()!="K2Node_FunctionEntry":continue
        for value in node.LocalVariables:
            rows.append(dict(name=str(value.VarName),default=str(value.DefaultValue),category=str(value.VarType.PinCategory),sub_category=str(value.VarType.PinSubCategory),object=value.VarType.PinSubCategoryObject.get_path_name() if value.VarType.PinSubCategoryObject else None))
    return rows


def audit():
    stage=require_authoring_stage(arg("UEPAudioMathStage"),ue.convert_relative_path_to_full(ue.get_content_dir()));file=stage/RELATIVE;digest=hashlib.sha256(file.read_bytes()).hexdigest()
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();root=Path(arg("UEPAudioMathAuditResult")).parent
    if not ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(bp.GeneratedClass.get_cdo(),str(root/"audio-library-cdo.t3d")):raise RuntimeError("native audio-library full CDO export failed")
    rows=[]
    for graph in ue.blueprint_get_all_graphs(bp):
        rows.append(dict(name=graph.get_name(),nodes=len(graph.Nodes),hash=semantics(graph,{n.get_name() for n in graph.Nodes},set()),locals=local_rows(graph)))
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in METHODS}
    if any(not value["flags"]&0x2000 for value in signatures.values()):raise RuntimeError("original helper static ABI differs")
    if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError("read-only audio audit changed source bytes")
    return dict(status="passed",read_only=True,assets_saved=False,cpp_compile_executed=False,asset_sha256=digest,graphs=rows,signatures=signatures)


try:report=audit()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPAudioMathAuditResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_WEAPON_AUDIO_MATH_AUDIT_PASSED")
