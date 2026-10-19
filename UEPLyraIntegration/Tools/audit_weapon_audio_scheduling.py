"""Read-only remaining static audio scheduling graphs and authored local defaults."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="audit_weapon_audio_scheduling.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics

METHODS=("WhizBy","EarlyReflections")
RELATIVE="Plugins/GameFeatures/ShooterCore/Content/System/Audio/WeaponAudioFunctions.uasset"


def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))
def graph_rows(graph):
    rows=[]
    for node in graph.Nodes:
        try:method=str(node.FunctionReference.MemberName)
        except Exception:method=None
        pins=[dict(name=p.name,direction=p.direction,category=p.category,sub_category=p.sub_category,object=p.sub_category_object.get_path_name() if p.sub_category_object else None,
            default=p.default_value,default_object=p.default_object.get_path_name() if p.default_object else None,links=[v.owning_node.get_name()+"."+v.name for v in p.get_linked_to()]) for p in node.node_pins()]
        rows.append(dict(node=node.get_name(),cls=node.get_class().get_name(),method=method,pins=pins))
    return rows


def audit():
    stage=require_authoring_stage(arg("UEPAudioSchedulingStage"),ue.convert_relative_path_to_full(ue.get_content_dir()));path=stage/RELATIVE;digest=hashlib.sha256(path.read_bytes()).hexdigest()
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,"/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions");ue.unregister_all_mixins();graphs={g.get_name():g for g in ue.blueprint_get_all_graphs(bp)}
    rows={name:graph_rows(graphs[name]) for name in METHODS};macros={};locals={}
    for name in METHODS:
        locals[name]=[dict(name=str(v.VarName),default=str(v.DefaultValue),category=str(v.VarType.PinCategory),sub_category=str(v.VarType.PinSubCategory)) for n in graphs[name].Nodes if n.get_class().get_name()=="K2Node_FunctionEntry" for v in n.LocalVariables]
        for node in graphs[name].Nodes:
            if node.get_class().get_name()=="K2Node_MacroInstance":
                macro=node.node_get_macro_graph();macros[macro.get_path_name()]=graph_rows(macro)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise RuntimeError("read-only scheduling audit changed library bytes")
    return dict(status="passed",read_only=True,assets_saved=False,cpp_compile_executed=False,asset_sha256=digest,graphs=rows,macros=macros,local_defaults=locals,
        signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in METHODS},original_graph_hashes={name:semantics(graphs[name],{n.get_name() for n in graphs[name].Nodes},set()) for name in METHODS})


try:report=audit()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPAudioSchedulingAuditResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_WEAPON_AUDIO_SCHEDULING_AUDIT_PASSED")
