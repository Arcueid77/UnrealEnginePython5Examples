"""Read-only GameplayCue widget family, signature and full CDO audit."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="audit_cue_widgets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics

ASSETS={'base': ('/Game/GameplayCueNotifies/GCNL_Widget_Base.GCNL_Widget_Base', 'Content/GameplayCueNotifies/GCNL_Widget_Base.uasset'), 'match': ('/ShooterCore/GameplayCues/GCNL_MatchDecided.GCNL_MatchDecided', 'Plugins/GameFeatures/ShooterCore/Content/GameplayCues/GCNL_MatchDecided.uasset'), 'waiting': ('/ShooterCore/GameplayCues/GCNL_WaitingForPlayers.GCNL_WaitingForPlayers', 'Plugins/GameFeatures/ShooterCore/Content/GameplayCues/GCNL_WaitingForPlayers.uasset'), 'match_widget': ('/ShooterCore/GameplayCues/W_MatchDecided_Message.W_MatchDecided_Message', 'Plugins/GameFeatures/ShooterCore/Content/GameplayCues/W_MatchDecided_Message.uasset'), 'waiting_widget': ('/ShooterCore/GameplayCues/W_WaitingForPlayers_Message.W_WaitingForPlayers_Message', 'Plugins/GameFeatures/ShooterCore/Content/GameplayCues/W_WaitingForPlayers_Message.uasset'), 'damage': ('/Game/GameplayCueNotifies/GCNL_Character_DamageTaken.GCNL_Character_DamageTaken', 'Content/GameplayCueNotifies/GCNL_Character_DamageTaken.uasset')}


def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))
def graph_rows(graph):
    rows=[]
    for node in graph.Nodes:
        method=None;event=None;variable=None;owner=None
        try:method=str(node.FunctionReference.MemberName)
        except Exception:pass
        try:variable=str(node.VariableReference.MemberName)
        except Exception:pass
        try:owner=node.FunctionReference.MemberParent.get_path_name()
        except Exception:pass
        try:event=str(node.CustomFunctionName) if node.get_class().get_name()=="K2Node_CustomEvent" else str(node.EventReference.MemberName)
        except Exception:
            try:event=str(node.CustomFunctionName)
            except Exception:pass
        rows.append(dict(node=node.get_name(),cls=node.get_class().get_name(),method=method,event=event,variable=variable,function_owner=owner,pins=[dict(name=p.name,direction=p.direction,
            category=p.category,sub_category=p.sub_category,object=p.sub_category_object.get_path_name() if p.sub_category_object else None,
            default=p.default_value,default_object=p.default_object.get_path_name() if p.default_object else None,
            links=[v.owning_node.get_name()+"."+v.name for v in p.get_linked_to()]) for p in node.node_pins()]))
    return rows


def audit():
    stage=require_authoring_stage(arg("UEPCueWidgetsStage"),ue.convert_relative_path_to_full(ue.get_content_dir()));root=Path(arg("UEPCueWidgetsAuditResult")).parent
    official=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent;assets={}
    for label,(package,relative) in ASSETS.items():
        file=stage/relative;original=official/relative;digest=hashlib.sha256(file.read_bytes()).hexdigest()
        if digest!=hashlib.sha256(original.read_bytes()).hexdigest():raise RuntimeError("fresh original cue-widget asset required: "+label)
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,package);ue.unregister_all_mixins();graphs=ue.blueprint_get_all_graphs(bp);rows={g.get_name():graph_rows(g) for g in graphs}
        names={name for name,nodes in rows.items() if name!="UserConstructionScript" and any(n["cls"]=="K2Node_FunctionEntry" for n in nodes)}
        (root/(label+"-graphs.json")).write_text(json.dumps(rows,indent=2),encoding="utf-8")
        names.update(n["event"] for graph in rows.values() for n in graph if n["event"] not in (None,"None","") and n["cls"] in ("K2Node_Event","K2Node_CustomEvent"))
        signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in names}
        export=root/(label+"-cdo.t3d")
        if not ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(bp.GeneratedClass.get_cdo(),str(export)):raise RuntimeError("full cue-widget CDO export failed")
        if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError("read-only cue-widget audit changed bytes")
        assets[label]=dict(package=package,relative=relative,asset_sha256=digest,parent=bp.ParentClass.get_path_name(),graphs=rows,signatures=signatures,
            graph_hashes={g.get_name():semantics(g,{n.get_name() for n in g.Nodes},set()) for g in graphs},cdo_export_sha256=hashlib.sha256(export.read_bytes()).hexdigest())
    return dict(status="passed",read_only=True,assets_saved=False,cpp_compile_executed=False,assets=assets)


try:report=audit()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPCueWidgetsAuditResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_CUE_WIDGETS_AUDIT_PASSED")
