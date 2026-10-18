"""Declare native ReceiveHit policy override; keep reliable Detonate untouched."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile

script=globals().get("__file__") or next(value for value in sys.argv if Path(value).name=="generate_grenade_hit_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from generate_grenade_vfx_assets import PACKAGE,RELATIVE,audit as vfx_audit


def arg(name): return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit(bp):
    graph,=[value for value in ue.blueprint_get_all_graphs(bp) if value.get_name()=="EventGraph"];nodes={node.get_name():node for node in graph.Nodes}
    if len(nodes)!=132: raise RuntimeError("original Actor Hit graph footprint differs")
    def links(node,pin,expected):
        actual={(value.owning_node.get_name(),value.name) for value in nodes[node].node_find_pin(pin).get_linked_to()}
        if actual!=set(expected): raise RuntimeError("original Hit link differs: "+node+"/"+pin)
    for node,pin,expected in (("K2Node_CallFunction_20","execute",[("K2Node_Event_1","then")]),("K2Node_CallFunction_20","A",[("K2Node_Event_1","Other")]),
        ("K2Node_CallFunction_20","B",[("K2Node_VariableGet_16","Instigator")]),("K2Node_CallFunction_25","execute",[("K2Node_CallFunction_20","DifferentTeams")]),
        ("K2Node_CallFunction_25","Handle",[("K2Node_VariableGet_4","Timer")]),("K2Node_CallFunction_14","execute",[("K2Node_CallFunction_25","then")]),
        ("K2Node_Knot_8","InputPin",[("K2Node_CallFunction_20","OnSameTeam"),("K2Node_CallFunction_20","InvalidArgument")]),
        ("K2Node_CallFunction_15","execute",[("K2Node_CallFunction_14","then"),("K2Node_Knot_8","OutputPin")])): links(node,pin,expected)
    for node,name in (("K2Node_CallFunction_20","CompareTeams"),("K2Node_CallFunction_25","K2_ClearAndInvalidateTimerHandle"),("K2Node_CallFunction_14","Detonate"),("K2Node_CallFunction_15","SpawnSoundAtLocation")):
        if str(nodes[node].FunctionReference.MemberName)!=name: raise RuntimeError("original native Hit call differs")
    sound=nodes["K2Node_CallFunction_15"]
    if sound.node_find_pin("Sound").default_object.get_path_name()!="/Game/Audio/MetaSounds/sfx_Weapon_GrenadeImpact_nl_meta.sfx_Weapon_GrenadeImpact_nl_meta" or sound.node_find_pin("AttenuationSettings").default_object.get_path_name()!="/Game/Audio/AttenuationPresets/ATT_Projectile.ATT_Projectile": raise RuntimeError("original native impact audio assets differ")
    for pin,value in (("VolumeMultiplier","1.000000"),("PitchMultiplier","1.000000"),("StartTime","0.000000"),("bAutoDestroy","true")):
        if sound.node_find_pin(pin).default_value!=value: raise RuntimeError("original native sound option differs")
    signature=ue.describe_function(bp.GeneratedClass,"ReceiveHit")
    if [value["name"] for value in signature["parameters"]]!=["MyComp","Other","OtherComp","bSelfMoved","HitLocation","HitNormal","NormalImpulse","Hit"]: raise RuntimeError("all original Hit reflected inputs must remain")
    return dict(team_a="Other",team_b="Instigator",different_team_clears_fuse_then_requests_native_rpc=True,same_or_invalid_only_audio=True,
        original_impact_sound=True,native_audio_volume=1.,native_audio_pitch=1.,native_audio_start=0.,native_audio_auto_destroy=True,all_reflected_inputs_preserved=True,
        reliable_detonate_body_retained=True,world_context_cached_before_possible_actor_destroy=True)


def generate():
    stage=require_authoring_stage(arg("UEPDashRPCStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()));ue.unregister_all_mixins()
    bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"grenade-hit-before");original_class=bp.GeneratedClass.get_path_name()
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in ("Setup VFX","PostLaunchCleanup","Teleport Grenade","Destroy Grenade","Detonate","ReceiveBeginPlay","ReceiveHit")}
    graphs=[(value,{node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)];hashes={value.get_name():semantics(value,names,set()) for value,names in graphs};policy=audit(bp);vfx=vfx_audit(bp)
    mixin=ue.load_object(ue.find_class("UEPPythonMixinSet"),"/Game/UEPMixins/DA_GrenadeVFXMixin.DA_GrenadeVFXMixin")
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.grenade_hit_mixin",PythonClass="LyraGrenadeHit"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"grenade-hit-after")!=before: raise RuntimeError("original Actor class/full CDO changed")
    if any(semantics(value,names,set())!=hashes[value.get_name()] for value,names in graphs) or any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original Actor graphs/signatures/RPC flags changed")
    bp.save_package();mixin.save_package()
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in binding["profiles"].items()}
        if counts!=dict(Python=6,BlueprintFallback=6): raise RuntimeError("six retained Actor methods per Profile required")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original signatures did not restore")
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="grenadehit",runtime_acceptance=False,full_acceptance=False,original_class=original_class,original_full_cdo_preserved=True,
        original_graphs_unmodified=True,original_graphs=hashes,native_register_restore_passed=True,actual_registered_profile_method_counts=counts,new_business_nodes=0,
        original_vfx_policy=vfx,original_hit_policy=policy,extra_signatures=signatures,native_server_rpc_flags_preserved=True,
        actor_detonate_damage_business_migrated=False,assets=[RELATIVE,"Content/UEPMixins/DA_GrenadeVFXMixin.uasset"])


try: report=generate()
except Exception: report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed": raise RuntimeError(report["error"])
ue.log("UEP_GRENADE_HIT_ASSETS_PASSED")
