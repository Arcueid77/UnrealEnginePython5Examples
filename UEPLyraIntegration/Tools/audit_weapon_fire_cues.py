"""Read-only Cue/audio signatures and the exact embedded weapon lookup macro."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="audit_weapon_fire_cues.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics


def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))
def pin_row(pin):return dict(name=pin.name,category=pin.category,default=pin.default_value,object=pin.default_object.get_path_name() if pin.default_object else None,links=[p.owning_node.get_name()+"."+p.name for p in pin.get_linked_to()])
def graph_row(graph):
    rows=[]
    for node in graph.Nodes:
        try:method=str(node.FunctionReference.MemberName)
        except Exception:method=None
        rows.append(dict(node=node.get_name(),cls=node.get_class().get_name(),method=method,pins=[pin_row(pin) for pin in node.node_pins()]))
    return dict(path=graph.get_path_name(),nodes=rows)


def audit():
    stage=require_authoring_stage(arg("UEPCueAuditStage"),ue.convert_relative_path_to_full(ue.get_content_dir()));ue.unregister_all_mixins();records=[];macros={}
    for weapon in ("Pistol","Rifle","Shotgun"):
        name="GCN_Weapon_"+weapon+"_Fire";relative="Plugins/GameFeatures/ShooterCore/Content/Weapons/"+weapon+"/"+name+".uasset";file=stage/relative
        before=hashlib.sha256(file.read_bytes()).hexdigest();bp=ue.load_object(Blueprint,"/ShooterCore/Weapons/"+weapon+"/"+name+"."+name);graphs=ue.blueprint_get_all_graphs(bp)
        for graph in graphs:
            for node in graph.Nodes:
                if node.get_class().get_name()=="K2Node_MacroInstance":
                    macro=node.node_get_macro_graph();macros[macro.get_path_name()]=graph_row(macro)
        records.append(dict(weapon=weapon,path=bp.get_path_name(),parent=bp.ParentClass.get_path_name(),signature=ue.describe_function(bp.GeneratedClass,"OnBurst"),
            graphs={g.get_name():dict(nodes=len(g.Nodes),sha256=semantics(g,{n.get_name() for n in g.Nodes},set())) for g in graphs},asset_sha256=before))
        if hashlib.sha256(file.read_bytes()).hexdigest()!=before:raise RuntimeError("read-only Cue audit changed source bytes")
    audio=ue.load_class("/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C")
    signatures={name:ue.describe_function(audio,name) for name in ("SendWeaponFire","SetWeaponSoundParams","EarlyReflections","WhizBy")}
    return dict(status="passed",read_only=True,assets_saved=False,cpp_compile_executed=False,records=records,macros=macros,audio_signatures=signatures)


try:report=audit()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPCueAuditResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_WEAPON_FIRE_CUE_AUDIT_PASSED")
