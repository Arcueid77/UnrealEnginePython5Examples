"""Read-only native signatures, montage callback identities and child defaults."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import struct
import zlib
import unreal_engine as ue
from unreal_engine.classes import Blueprint

script=globals().get("__file__") or next(value for value in sys.argv if Path(value).name=="audit_weapon_ability_fire.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name):return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))
def value(obj):return obj.get_path_name() if hasattr(obj,"get_path_name") else obj


def audit():
    stage=require_authoring_stage(arg("UEPFireStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,"/Game/Weapons/GA_Weapon_Fire.GA_Weapon_Fire");ue.unregister_all_mixins()
    graph,=[g for g in ue.blueprint_get_all_graphs(bp) if g.get_name()=="EventGraph"]
    tasks={}
    for node in graph.Nodes:
        if node.get_class().get_name()!="K2Node_LatentAbilityCall":continue
        guid=node.NodeGuid;parts=[int(guid.get_field(key))&0xffffffff for key in ("A","B","C","D")]
        # FKismetCompilerContext::GetGuid replaces D with MemCrc32(NodeGuid).
        suffix="".join(format(part,"08X") for part in parts[:3])+format(zlib.crc32(struct.pack("<4I",*parts)),"08X")
        tasks[node.get_name()]=dict(guid=suffix,callbacks={name:ue.describe_function(bp.GeneratedClass,name+"_"+suffix) for name in ("OnCompleted","OnInterrupted","OnCancelled")})
    methods=("K2_ActivateAbility","K2_OnAbilityAdded","OnRangedWeaponTargetDataReady","FireComplete","FailureMontage Delay Complete","Slelect Hit Montage")
    field_names=("GE_Damage","GameplayCue_Impact","Gameplay Cue TagFiring","CharacterFireMontage","AutoRate","FireDelayTimeSecs","FieldActorToSpawnOnImpact","Can Trigger Failure Montage","Failure Montage Delay Time")
    records=[]
    for path in ("/Game/Weapons/GA_Weapon_Fire.GA_Weapon_Fire","/ShooterCore/Weapons/Pistol/GA_Weapon_Fire_Pistol.GA_Weapon_Fire_Pistol",
                 "/ShooterCore/Weapons/Rifle/GA_Weapon_Fire_Rifle_Auto.GA_Weapon_Fire_Rifle_Auto","/ShooterCore/Weapons/Shotgun/GA_Weapon_Fire_Shotgun.GA_Weapon_Fire_Shotgun"):
        source=ue.load_object(Blueprint,path);cdo=source.GeneratedClass.get_cdo()
        records.append(dict(path=path,generated_class=source.GeneratedClass.get_path_name(),graph_counts={g.get_name():len(g.Nodes) for g in ue.blueprint_get_all_graphs(source)},
            fields={key:value(cdo.get_property(key)) for key in field_names},signatures={name:ue.describe_function(source.GeneratedClass,name) for name in methods}))
    return dict(status="passed",read_only=True,assets_saved=False,cpp_compile_executed=False,tasks=tasks,blueprints=records,
        source_sha256=hashlib.sha256((stage/"Content/Weapons/GA_Weapon_Fire.uasset").read_bytes()).hexdigest())


try:report=audit()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPFireAuditResult")).write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_WEAPON_ABILITY_FIRE_AUDIT_PASSED")
