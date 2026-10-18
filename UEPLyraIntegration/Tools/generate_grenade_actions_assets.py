"""Retain all Actor graphs/RPC/timers; declare teleport/destroy helper overrides."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile

script=globals().get("__file__") or next(value for value in sys.argv if Path(value).name=="generate_grenade_actions_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from generate_grenade_vfx_assets import PACKAGE,RELATIVE,audit as vfx_audit


def arg(name): return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit(bp):
    graph,=[value for value in ue.blueprint_get_all_graphs(bp) if value.get_name()=="EventGraph"];nodes={value.get_name():value for value in graph.Nodes}
    if len(nodes)!=132: raise RuntimeError("original Actor EventGraph footprint differs")
    def link(node,pin,source,output):
        value,=nodes[node].node_find_pin(pin).get_linked_to()
        if value.owning_node!=nodes[source] or value.name!=output: raise RuntimeError("original Actor action flow differs: "+node+"/"+pin)
    for args in (("K2Node_VariableSet_5","execute","K2Node_CustomEvent_5","then"),("K2Node_VariableSet_5","ConservedVelocity","K2Node_CallFunction_23","ReturnValue"),
        ("K2Node_CallFunction_23","A","K2Node_VariableGet_25","Velocity"),("K2Node_VariableGet_25","self","K2Node_VariableGet_23","ProjectileMovement"),
        ("K2Node_VariableGet_36","execute","K2Node_VariableSet_5","then"),("K2Node_CallFunction_51","execute","K2Node_VariableGet_36","then"),
        ("K2Node_CallFunction_51","self","K2Node_VariableGet_36","NS_Trail"),("K2Node_CallFunction_30","execute","K2Node_CallFunction_51","then"),
        ("K2Node_CallFunction_30","NewLocation","K2Node_Knot_17","OutputPin"),("K2Node_Knot_17","InputPin","K2Node_CustomEvent_5","TeleportLocation"),
        ("K2Node_CallFunction_42","execute","K2Node_CallFunction_30","then"),("K2Node_VariableSet_6","execute","K2Node_CallFunction_42","then"),
        ("K2Node_VariableSet_6","Velocity","K2Node_PromotableOperator_3","ReturnValue"),("K2Node_PromotableOperator_3","A","K2Node_Knot_22","OutputPin"),
        ("K2Node_Knot_22","InputPin","K2Node_CustomEvent_5","TeleportForward"),("K2Node_PromotableOperator_3","B","K2Node_PromotableOperator_5","ReturnValue"),
        ("K2Node_PromotableOperator_5","A","K2Node_VariableGet_1","ConservedVelocity"),("K2Node_CallFunction_50","execute","K2Node_VariableSet_6","then")):
        link(*args)
    for name,method in (("K2Node_CallFunction_23","VSize"),("K2Node_CallFunction_51","Deactivate"),("K2Node_CallFunction_30","K2_SetActorLocation"),
        ("K2Node_CallFunction_42","Activate"),("K2Node_CallFunction_50","Setup VFX"),("K2Node_CallFunction_8","K2_DestroyActor")):
        if str(nodes[name].FunctionReference.MemberName)!=method: raise RuntimeError("original native Actor action differs")
    if nodes["K2Node_VariableGet_36"].node_find_pin("else").get_linked_to(): raise RuntimeError("original invalid-trail teleport did not stop")
    if nodes["K2Node_CallFunction_30"].node_find_pin("bSweep").default_value!="false" or nodes["K2Node_CallFunction_30"].node_find_pin("bTeleport").default_value!="true" or nodes["K2Node_CallFunction_42"].node_find_pin("bReset").default_value!="true": raise RuntimeError("original teleport native options differ")
    if nodes["K2Node_PromotableOperator_3"].node_find_pin("B").category!="real" or float(nodes["K2Node_PromotableOperator_5"].node_find_pin("B").default_value)!=2. or str(nodes["K2Node_PromotableOperator_5"].FunctionReference.MemberName)!="Divide_DoubleDouble": raise RuntimeError("original scalar half-speed operation differs")
    if not any(value.owning_node==nodes["K2Node_CustomEvent_2"] for value in nodes["K2Node_CallFunction_8"].node_find_pin("execute").get_linked_to()): raise RuntimeError("original destroy entry differs")
    system=nodes["K2Node_CustomEvent_2"].node_find_pin("PSystem")
    if system.category!="object" or system.get_linked_to(): raise RuntimeError("original unused Niagara delegate parameter differs")
    return dict(conserved_speed_from_projectile_velocity=True,conserved_written_before_trail_guard=True,invalid_trail_stops_after_conserved_write=True,
        sweep=False,teleport=True,activate_reset=True,speed_divisor=2.,forward_not_normalized=True,original_native_destroy_entry=True,original_timers_and_reliable_detonate_retained=True)


def generate():
    stage=require_authoring_stage(arg("UEPDashRPCStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()));ue.unregister_all_mixins()
    bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"grenade-actions-before");original_class=bp.GeneratedClass.get_path_name()
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in ("Setup VFX","PostLaunchCleanup","Teleport Grenade","Destroy Grenade","Detonate","ReceiveBeginPlay","ReceiveHit")}
    graphs=[(value,{node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)];hashes={value.get_name():semantics(value,names,set()) for value,names in graphs};policy=audit(bp);vfx=vfx_audit(bp)
    mixin=ue.load_object(ue.find_class("UEPPythonMixinSet"),"/Game/UEPMixins/DA_GrenadeVFXMixin.DA_GrenadeVFXMixin")
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.grenade_actions_mixin",PythonClass="LyraGrenadeActions"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"grenade-actions-after")!=before: raise RuntimeError("original Actor class/full CDO changed")
    if any(semantics(value,names,set())!=hashes[value.get_name()] for value,names in graphs) or any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original Actor graphs/signatures/RPC flags changed")
    bp.save_package();mixin.save_package()
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in binding["profiles"].items()}
        if counts!=dict(Python=4,BlueprintFallback=4): raise RuntimeError("four Actor methods per Profile required")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("native Actor signatures did not restore")
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="grenadeactions",runtime_acceptance=False,full_acceptance=False,original_class=original_class,original_full_cdo_preserved=True,
        original_graphs_unmodified=True,original_graphs=hashes,native_register_restore_passed=True,actual_registered_profile_method_counts=counts,new_business_nodes=0,
        original_vfx_policy=vfx,original_action_policy=policy,extra_signatures=signatures,native_server_rpc_flags_preserved=True,
        actor_fuse_detonate_damage_business_migrated=False,assets=[RELATIVE,"Content/UEPMixins/DA_GrenadeVFXMixin.uasset"])


try: report=generate()
except Exception: report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed": raise RuntimeError(report["error"])
ue.log("UEP_GRENADE_ACTIONS_ASSETS_PASSED")
