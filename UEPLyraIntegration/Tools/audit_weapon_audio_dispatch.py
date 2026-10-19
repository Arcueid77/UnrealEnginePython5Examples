"""Read-only void static ABI, ammo macro and native audio/tap preset interfaces."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="audit_weapon_audio_dispatch.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

METHODS=("SendWeaponFire","SetWeaponSoundParams","DebugPrintTap","Calculate Tap Properties")


def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))
def graph_rows(graph):
    rows=[]
    for node in graph.Nodes:
        try:method=str(node.FunctionReference.MemberName)
        except Exception:method=None
        pins=[dict(name=p.name,category=p.category,sub_category=p.sub_category,object=p.sub_category_object.get_path_name() if p.sub_category_object else None,
            default=p.default_value,default_object=p.default_object.get_path_name() if p.default_object else None,links=[v.owning_node.get_name()+"."+v.name for v in p.get_linked_to()]) for p in node.node_pins()]
        rows.append(dict(node=node.get_name(),cls=node.get_class().get_name(),method=method,pins=pins))
    return rows


def audit():
    require_authoring_stage(arg("UEPAudioDispatchStage"),ue.convert_relative_path_to_full(ue.get_content_dir()));ue.unregister_all_mixins();bp=ue.load_object(Blueprint,"/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions")
    macros={}
    for graph in ue.blueprint_get_all_graphs(bp):
        if graph.get_name()!="SetWeaponSoundParams":continue
        for node in graph.Nodes:
            if node.get_class().get_name()=="K2Node_MacroInstance":
                macro=node.node_get_macro_graph()
                if "LyraGetWeaponAmmo" in macro.get_path_name():macros[macro.get_path_name()]=graph_rows(macro)
    preset=ue.load_class("/Script/Synthesis.SubmixEffectTapDelayPreset");audio=ue.find_class("AudioComponent")
    return dict(status="passed",read_only=True,assets_saved=False,cpp_compile_executed=False,
        signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in METHODS},macros=macros,
        preset_signatures={name:ue.describe_function(preset,name) for name in ("AddTap","GetTap","SetTap","RemoveTap")},
        audio_parameters=[name for name in audio.get_cdo().properties() if "Parameter" in name],
        tap_fields=list(ue.find_struct("TapDelayInfo")().fields()))


try:report=audit()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPAudioDispatchAuditResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_WEAPON_AUDIO_DISPATCH_AUDIT_PASSED")
