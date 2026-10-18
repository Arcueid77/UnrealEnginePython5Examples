"""Declare retained Actor BeginPlay override; no new BP/CPP timer adapters."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile

script=globals().get("__file__") or next(value for value in sys.argv if Path(value).name=="generate_grenade_begin_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from generate_grenade_vfx_assets import PACKAGE,RELATIVE,audit as vfx_audit


def arg(name): return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit(bp):
    graph,=[value for value in ue.blueprint_get_all_graphs(bp) if value.get_name()=="EventGraph"];nodes={node.get_name():node for node in graph.Nodes}
    if len(nodes)!=132: raise RuntimeError("original Actor BeginPlay footprint differs")
    def links(node,pin,expected):
        actual={(value.owning_node.get_name(),value.name) for value in nodes[node].node_find_pin(pin).get_linked_to()}
        if actual!=set(expected): raise RuntimeError("original BeginPlay link differs: "+node+"/"+pin)
    for node,pin,expected in (("K2Node_CallFunction_0","execute",[("K2Node_Event_0","then")]),("K2Node_DynamicCast_0","execute",[("K2Node_CallFunction_0","then")]),
        ("K2Node_CallFunction_13","execute",[("K2Node_DynamicCast_0","then")]),("K2Node_CallFunction_13","self",[("K2Node_VariableGet_14","CapsuleComponent")]),
        ("K2Node_CallFunction_12","execute",[("K2Node_CallFunction_13","then")]),("K2Node_CallFunction_12","self",[("K2Node_VariableGet_11","Mesh")]),
        ("K2Node_Knot_11","InputPin",[("K2Node_DynamicCast_0","CastFailed")]),("K2Node_Knot_14","InputPin",[("K2Node_Knot_11","OutputPin")]),
        ("K2Node_CallFunction_26","execute",[("K2Node_CallFunction_12","then"),("K2Node_Knot_14","OutputPin")]),
        ("K2Node_CallFunction_2","execute",[("K2Node_CallFunction_26","then")]),("K2Node_CallFunction_2","Delegate",[("K2Node_CreateDelegate_1","OutputDelegate")]),
        ("K2Node_VariableSet_3","execute",[("K2Node_CallFunction_2","then")]),("K2Node_VariableSet_3","Timer",[("K2Node_CallFunction_2","ReturnValue")]),
        ("K2Node_CallFunction_1","execute",[("K2Node_VariableSet_3","then")]),("K2Node_CallFunction_1","Delegate",[("K2Node_CreateDelegate_0","OutputDelegate")])): links(node,pin,expected)
    material=nodes["K2Node_CallFunction_0"]
    if str(material.FunctionReference.MemberName)!="SetForceMipLevelsToBeResident": raise RuntimeError("original native material request differs")
    for pin,value in (("OverrideForceMiplevelsToBeResident","true"),("bForceMiplevelsToBeResidentValue","true"),("ForceDuration","3.000000"),("CinematicTextureGroups","0"),("bFastResponse","true")):
        if material.node_find_pin(pin).default_value!=value: raise RuntimeError("original material option differs: "+pin)
    for node in ("K2Node_CallFunction_12","K2Node_CallFunction_13"):
        if str(nodes[node].FunctionReference.MemberName)!="IgnoreActorWhenMoving" or nodes[node].node_find_pin("bShouldIgnore").default_value!="true": raise RuntimeError("original initial collision ignore differs")
    for node,delegate,name in (("K2Node_CallFunction_2","K2Node_CreateDelegate_1","Detonate"),("K2Node_CallFunction_1","K2Node_CreateDelegate_0","PostLaunchCleanup")):
        if str(nodes[node].FunctionReference.MemberName)!="K2_SetTimerDelegate" or str(nodes[delegate].SelectedFunctionName)!=name: raise RuntimeError("original native timer target differs")
        if ue.describe_function(bp.GeneratedClass,name)["parameters"]: raise RuntimeError("native named timer target must have no parameters")
        for pin,value in (("bLooping","false"),("bMaxOncePerFrame","false"),("InitialStartDelay","0.000000"),("InitialStartDelayVariance","0.000000")):
            if nodes[node].node_find_pin(pin).default_value!=value: raise RuntimeError("original native timer option differs")
    if float(nodes["K2Node_CallFunction_1"].node_find_pin("Time").default_value)!=.16: raise RuntimeError("original cleanup delay differs")
    return dict(material_force_seconds=3.,material_fast_response=True,character_only_both_ignores=True,noncharacter_still_vfx_and_timers=True,
        native_timer_actor_owner=True,zero_parameter_timer_targets=["Detonate","PostLaunchCleanup"],native_function_name_api="K2_SetTimer",
        cleanup_seconds=.16,original_fuse_property="TimeBeforeExplode",native_timer_jitter=0.,native_timer_looping=False,returned_fuse_handle_stored=True,new_native_adapters=0)


def generate():
    stage=require_authoring_stage(arg("UEPDashRPCStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()));ue.unregister_all_mixins()
    bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"grenade-begin-before");original_class=bp.GeneratedClass.get_path_name()
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in ("Setup VFX","PostLaunchCleanup","Teleport Grenade","Destroy Grenade","Detonate","ReceiveBeginPlay","ReceiveHit")}
    graphs=[(value,{node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)];hashes={value.get_name():semantics(value,names,set()) for value,names in graphs};policy=audit(bp);vfx=vfx_audit(bp)
    mixin=ue.load_object(ue.find_class("UEPPythonMixinSet"),"/Game/UEPMixins/DA_GrenadeVFXMixin.DA_GrenadeVFXMixin")
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.grenade_begin_mixin",PythonClass="LyraGrenadeBegin"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"grenade-begin-after")!=before: raise RuntimeError("original Actor class/full CDO changed")
    if any(semantics(value,names,set())!=hashes[value.get_name()] for value,names in graphs) or any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original Actor graphs/signatures/RPC flags changed")
    bp.save_package();mixin.save_package()
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in binding["profiles"].items()}
        if counts!=dict(Python=5,BlueprintFallback=5): raise RuntimeError("five retained Actor functions per Profile required")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("native signatures did not restore")
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="grenadebegin",runtime_acceptance=False,full_acceptance=False,original_class=original_class,original_full_cdo_preserved=True,
        original_graphs_unmodified=True,original_graphs=hashes,native_register_restore_passed=True,actual_registered_profile_method_counts=counts,new_business_nodes=0,
        original_vfx_policy=vfx,original_begin_policy=policy,extra_signatures=signatures,native_server_rpc_flags_preserved=True,
        actor_detonate_damage_business_migrated=False,assets=[RELATIVE,"Content/UEPMixins/DA_GrenadeVFXMixin.uasset"])


try: report=generate()
except Exception: report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed": raise RuntimeError(report["error"])
ue.log("UEP_GRENADE_BEGIN_ASSETS_PASSED")
