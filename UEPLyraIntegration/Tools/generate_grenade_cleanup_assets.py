"""Revise retained Actor Profiles only; original native timer/delegates stay BP."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile

script=globals().get("__file__") or next(value for value in sys.argv if Path(value).name=="generate_grenade_cleanup_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from generate_grenade_vfx_assets import PACKAGE,RELATIVE,audit as vfx_audit


def arg(name): return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit(bp):
    graph,=[value for value in ue.blueprint_get_all_graphs(bp) if value.get_name()=="EventGraph"];nodes={node.get_name():node for node in graph.Nodes}
    if len(nodes)!=132: raise RuntimeError("original Grenade Actor EventGraph footprint differs")
    def links(node,pin,expected):
        actual={(value.owning_node.get_name(),value.name) for value in nodes[node].node_find_pin(pin).get_linked_to()}
        if actual!=set(expected): raise RuntimeError("original cleanup flow differs: "+node+"/"+pin)
    for node,pin,expected in (("K2Node_DynamicCast_4","execute",[("K2Node_CustomEvent_1","then")]),
        ("K2Node_DynamicCast_4","Object",[("K2Node_VariableGet_9","Instigator")]),
        ("K2Node_CallFunction_4","execute",[("K2Node_DynamicCast_4","then")]),
        ("K2Node_CallFunction_4","self",[("K2Node_VariableGet_10","CapsuleComponent")]),
        ("K2Node_CallFunction_4","Actor",[("K2Node_Self_1","self")]),
        ("K2Node_Knot_13","InputPin",[("K2Node_DynamicCast_4","CastFailed")]),
        ("K2Node_Knot_15","InputPin",[("K2Node_Knot_13","OutputPin")]),
        ("K2Node_CallFunction_11","execute",[("K2Node_CallFunction_4","then"),("K2Node_Knot_15","OutputPin")]),
        ("K2Node_CallFunction_11","self",[("K2Node_VariableGet_8","Mesh")]),
        ("K2Node_CallFunction_11","Actor",[("K2Node_Knot_10","OutputPin")]),
        ("K2Node_VariableSet_0","execute",[("K2Node_CallFunction_11","then")]),
        ("K2Node_VariableSet_0","self",[("K2Node_VariableGet_6","ProjectileMovement")])): links(node,pin,expected)
    for name in ("K2Node_CallFunction_4","K2Node_CallFunction_11"):
        if str(nodes[name].FunctionReference.MemberName)!="IgnoreActorWhenMoving" or nodes[name].node_find_pin("bShouldIgnore").default_value!="false": raise RuntimeError("original native collision unignore differs")
    timer=nodes["K2Node_CallFunction_1"]
    if str(timer.FunctionReference.MemberName)!="K2_SetTimerDelegate" or float(timer.node_find_pin("Time").default_value)!=.16 or timer.node_find_pin("bLooping").default_value!="false": raise RuntimeError("original one-shot native timer differs")
    if str(nodes["K2Node_CreateDelegate_0"].SelectedFunctionName)!="PostLaunchCleanup" or str(nodes["K2Node_CreateDelegate_1"].SelectedFunctionName)!="Detonate": raise RuntimeError("original native timer bindings differ")
    if nodes["K2Node_VariableSet_0"].node_find_pin("bRotationFollowsVelocity").default_value!="true": raise RuntimeError("original native rotation restore differs")
    return dict(native_timer_seconds=.16,native_timer_looping=False,native_timer_callback="PostLaunchCleanup",cast_failed_rejoins_mesh_cleanup=True,
        character_capsule_unignore=True,grenade_mesh_unignore=True,rotation_follows_velocity=True,detonate_timer_and_reliable_rpc_retained=True)


def generate():
    stage=require_authoring_stage(arg("UEPDashRPCStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins()
    before=snapshot(bp,"grenade-cleanup-before");original_class=bp.GeneratedClass.get_path_name()
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in ("Setup VFX","PostLaunchCleanup","Detonate","ReceiveBeginPlay","ReceiveHit")}
    graphs=[(value,{node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)];hashes={value.get_name():semantics(value,names,set()) for value,names in graphs}
    policy=audit(bp);vfx=vfx_audit(bp)
    mixin=ue.load_object(ue.find_class("UEPPythonMixinSet"),"/Game/UEPMixins/DA_GrenadeVFXMixin.DA_GrenadeVFXMixin")
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.grenade_cleanup_mixin",PythonClass="LyraGrenadeCleanup"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"grenade-cleanup-after")!=before: raise RuntimeError("original Grenade class/full CDO changed")
    if any(semantics(value,names,set())!=hashes[value.get_name()] for value,names in graphs) or any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original Grenade graphs/signatures/RPC flags changed")
    bp.save_package();mixin.save_package()
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in binding["profiles"].items()}
        if counts!=dict(Python=2,BlueprintFallback=2): raise RuntimeError("two retained Actor helpers per Profile required")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("native Actor helper/RPC signatures did not restore")
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="grenadecleanup",runtime_acceptance=False,full_acceptance=False,original_class=original_class,
        original_full_cdo_preserved=True,original_graphs_unmodified=True,original_graphs=hashes,native_register_restore_passed=True,
        actual_registered_profile_method_counts=counts,new_business_nodes=0,original_vfx_policy=vfx,original_cleanup_policy=policy,extra_signatures=signatures,
        native_server_rpc_flags_preserved=True,actor_fuse_detonate_damage_business_migrated=False,assets=[RELATIVE,"Content/UEPMixins/DA_GrenadeVFXMixin.uasset"])


try: report=generate()
except Exception: report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed": raise RuntimeError(report["error"])
ue.log("UEP_GRENADE_CLEANUP_ASSETS_PASSED")
