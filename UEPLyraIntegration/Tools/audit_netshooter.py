"""Read-only prototype dependency chain, full defaults and native interfaces."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint

script=globals().get("__file__") or next(value for value in sys.argv if Path(value).name=="audit_netshooter.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name):return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))
def obj(value):return value.get_path_name() if hasattr(value,"get_path_name") else value
def export(value,file):
    if not ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(value,str(file)):raise RuntimeError("native prototype export failed")


def audit():
    stage=require_authoring_stage(arg("UEPNetShooterStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()));root=Path(arg("UEPNetShooterAuditResult")).parent
    ue.unregister_all_mixins();rows=[]
    for name in ("B_NetShooter","GA_WeaponNetShooter"):
        package="/ShooterCore/Weapons/NetShooter_PROTO/"+name
        bp=ue.load_object(Blueprint,package+"."+name);ue.unregister_all_mixins();cdo=bp.GeneratedClass.get_cdo()
        export(cdo,root/(name+"-cdo.t3d"))
        fields=("NumberOfWeb","DistanceTrace","OffsetImpact","LifeTime","bReplicates","bReplicateMovement","Start") if name=="B_NetShooter" else ("Location","Direction","OffsetGCN","CharacterFireMontage","AutoRate","FireDelayTimeSecs","InstancingPolicy","NetExecutionPolicy")
        methods=("ReceiveHit","SpawnComponents","OverlapRays") if name=="B_NetShooter" else ("K2_ActivateAbility","OnRangedWeaponTargetDataReady","OnCompleted_CBD1B4EC430B0115F3F85FB83619F775","OnInterrupted_CBD1B4EC430B0115F3F85FB83619F775","OnCancelled_CBD1B4EC430B0115F3F85FB83619F775")
        row=dict(name=name,generated_class=bp.GeneratedClass.get_path_name(),parent=bp.ParentClass.get_path_name(),graphs={g.get_name():len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp)},
            fields={key:obj(cdo.get_property(key)) for key in fields},signatures={key:ue.describe_function(bp.GeneratedClass,key) for key in methods},
            referencers=ue.get_asset_referencers(package),dependencies=ue.get_asset_dependencies(package))
        if name=="B_NetShooter":
            scs=bp.get_property("SimpleConstructionScript")
            for index,node in enumerate(scs.get_property("AllNodes")):
                value=node.get_property("ComponentTemplate");export(value,root/("scs-"+str(index)+"-"+value.get_name()+".t3d"))
            row["component_templates"]=[obj(value) for value in bp.ComponentTemplates]
            for index,value in enumerate(bp.ComponentTemplates):export(value,root/("component-template-"+str(index)+".t3d"))
        rows.append(row)
    package="/ShooterCore/Weapons/NetShooter_PROTO/ID_NetShooter";item=ue.load_class(package+".ID_NetShooter_C");export(item.get_cdo(),root/"ID_NetShooter-cdo.t3d")
    equipment="/ShooterCore/Weapons/NetShooter_PROTO/WID_NetShooter";wid=ue.load_class(equipment+".WID_NetShooter_C");export(wid.get_cdo(),root/"WID_NetShooter-cdo.t3d")
    ability_set="/ShooterCore/Weapons/NetShooter_PROTO/AbilitySet_ShooterNetShooter";export(ue.load_object(ue.find_class("LyraAbilitySet"),ability_set+".AbilitySet_ShooterNetShooter"),root/"AbilitySet_ShooterNetShooter.t3d")
    return dict(status="passed",read_only=True,assets_saved=False,cpp_compile_executed=False,records=rows,
        item_dependencies=ue.get_asset_dependencies(package),item_referencers=ue.get_asset_referencers(package),equipment_dependencies=ue.get_asset_dependencies(equipment),ability_set_dependencies=ue.get_asset_dependencies(ability_set))


try:report=audit()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPNetShooterAuditResult")).write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_NETSHOOTER_AUDIT_PASSED")
