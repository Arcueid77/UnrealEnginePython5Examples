"""Revise only parent Profile classes; preserve original Fire graphs/defaults."""
import json
import hashlib
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_weapon_actor_fire_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from generate_weapon_actor_helpers_assets import PACKAGE, RELATIVE, METHODS, CHILDREN, audit


def arg(name): return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    stage=require_authoring_stage(arg("UEPDashRPCStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()))
    parent_digest=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins()
    before=snapshot(bp,"weapon-fire-before");original_class=bp.GeneratedClass.get_path_name()
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in METHODS+("Fire","ReceiveBeginPlay")}
    if signatures["Fire"]["flags"] & 0x40: raise RuntimeError("original Fire is an ordinary entry,not RPC")
    graphs=[(value,{node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes={value.get_name():semantics(value,names,set()) for value,names in graphs};helpers=audit(bp)
    graph,=[value for value,_ in graphs if value.get_name()=="EventGraph"];nodes={node.get_name():node for node in graph.Nodes}
    if len(nodes)!=98: raise RuntimeError("original weapon EventGraph footprint differs")
    for node,cls in (("K2Node_SpawnActorFromClass_0","/Game/Effects/Blueprints/B_WeaponFire.B_WeaponFire_C"),
        ("K2Node_SpawnActorFromClass_2","/Game/Effects/Blueprints/B_WeaponImpacts.B_WeaponImpacts_C"),
        ("K2Node_SpawnActorFromClass_1","/Game/Effects/Blueprints/B_WeaponDecals.B_WeaponDecals_C")):
        item=nodes[node]
        if item.node_find_pin("Class").default_object.get_path_name()!=cls or item.node_find_pin("CollisionHandlingOverride").default_value!="Undefined" or item.node_find_pin("TransformScaleMethod").default_value!="OverrideRootScale": raise RuntimeError("original FX spawn policy differs")
    for node in ("K2Node_CallFunction_12","K2Node_CallFunction_5","K2Node_CallFunction_14"):
        for pin,default in (("LocationRule","KeepRelative"),("RotationRule","KeepRelative"),("ScaleRule","KeepRelative"),("bWeldSimulatedBodies","TRUE")):
            if nodes[node].node_find_pin(pin).default_value!=default: raise RuntimeError("original FX attachment differs")
    mixin=bp.GeneratedClass.get_cdo().GetPythonMixinSet()
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.weapon_actor_fire_mixin",PythonClass="LyraWeaponActorFire"+name+"Profile") for name in ("Python","BlueprintFallback")]
    # Fire already exists on the retained class. Only the external Mixin Set
    # needs revision; recompiling an already routed parent can serialize stale
    # REINST native flags. Preserve the accepted parent bytes exactly.
    ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"weapon-fire-after")!=before: raise RuntimeError("original weapon class/full CDO changed")
    if any(semantics(value,names,set())!=hashes[value.get_name()] for value,names in graphs) or any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original weapon graphs/signatures changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==bp.GeneratedClass]
        counts={name:len(row["functions"]) for name,row in binding["profiles"].items()}
        if counts!=dict(Python=5,BlueprintFallback=5): raise RuntimeError("five parent methods per Profile required")
    finally: ue.unregister_all_mixins()
    children=[]
    for package in CHILDREN:
        child=ue.load_object(Blueprint,package)
        if child.GeneratedClass.get_cdo().GetPythonMixinSet()!=mixin: raise RuntimeError("child lost inherited parent declaration")
        children.append(package)
    mixin.save_package()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=parent_digest:raise RuntimeError("accepted parent saved bytes changed")
    return dict(status="passed",kind="weaponactorfire",runtime_acceptance=False,full_acceptance=False,original_class=original_class,
        original_full_cdo_preserved=True,original_graphs_unmodified=True,original_graphs=hashes,extra_signatures=signatures,
        original_helper_policy=helpers,actual_registered_profile_method_counts=counts,native_register_restore_passed=True,
        original_fire_order=["WeaponFire","Weapon Impacts","Weapon Decals"],native_original_fx_actors_retained=True,new_business_nodes=0,
        begin_play_migrated=False,parent_saved_bytes_unchanged=True,parent_saved_sha256=parent_digest,
        inherited_children=children,assets=[RELATIVE,"Content/UEPMixins/DA_WeaponActorHelpersMixin.uasset"])


try: report=generate()
except Exception: report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed": raise RuntimeError(report["error"])
ue.log("UEP_WEAPON_ACTOR_FIRE_ASSETS_PASSED")
