"""Retain all original Grenade graphs/CDO; route the actual activation event."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile

script=globals().get("__file__") or next(value for value in sys.argv if Path(value).name=="generate_grenade_activation_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from generate_grenade_widget_assets import PACKAGE,RELATIVE,audit as ui_audit

OUTPUTS=(RELATIVE,"Content/UEPMixins/DA_GrenadeWidgetMixin.uasset")


def arg(name): return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit(bp):
    graphs={value.get_name():value for value in ue.blueprint_get_all_graphs(bp)}
    event={value.get_name():value for value in graphs["EventGraph"].Nodes}
    if len(event)!=46: raise RuntimeError("original Grenade EventGraph footprint differs")
    for node,member in (("K2Node_CallFunction_12","K2_CheckAbilityCost"),("K2Node_CallFunction_13","K2_CheckAbilityCooldown"),
        ("K2Node_CallFunction_2","K2_CommitAbility"),("K2Node_CallFunction_33","K2_HasAuthority"),("K2Node_CallFunction_6","K2_EndAbility")):
        if str(event[node].FunctionReference.MemberName)!=member: raise RuntimeError("original Grenade activation native call differs")
    if event["K2Node_CallFunction_2"].node_find_pin("ReturnValue").get_linked_to(): raise RuntimeError("original Commit return was not ignored")
    task=event["K2Node_LatentAbilityCall_0"]
    if task.node_find_pin("bStopWhenAbilityEnds").default_value!="false": raise RuntimeError("original Grenade montage stop policy differs")
    for pin in ("OnCompleted","OnBlendedIn","OnBlendOut","OnInterrupted","OnCancelled"):
        if task.node_find_pin(pin).get_linked_to(): raise RuntimeError("original Grenade unexpectedly waits for montage callback")
    channel=event["K2Node_CallFunction_10"].node_find_pin("Channel").default_value
    if channel!='(TagName="Ability.Grenade.Duration.Message")': raise RuntimeError("original Grenade duration channel differs")
    location={value.get_name():value for value in graphs["Get Spawn Location"].Nodes}
    for node,amount in (("K2Node_PromotableOperator_0",5.),("K2Node_PromotableOperator_3",25.)):
        pin=location[node].node_find_pin("B")
        if pin.category!="real" or float(pin.default_value)!=amount: raise RuntimeError("original scalar actor-basis offset differs")
    rotation={value.get_name():value for value in graphs["Get Spawn Rotation"].Nodes}
    if str(rotation["K2Node_PromotableOperator_1"].FunctionReference.MemberName)!="Less_DoubleDouble" or float(rotation["K2Node_PromotableOperator_1"].node_find_pin("B").default_value)!=45.:
        raise RuntimeError("original strict near-distance comparator differs")
    trace=rotation["K2Node_CallFunction_7"]
    if trace.node_find_pin("TraceChannel").default_value!="TraceTypeQuery4" or trace.node_find_pin("bTraceComplex").default_value!="false" or trace.node_find_pin("bIgnoreSelf").default_value!="true":
        raise RuntimeError("original Grenade native aim trace differs")
    spawn=event["K2Node_SpawnActorFromClass_0"]
    if spawn.node_find_pin("CollisionHandlingOverride").default_value!="AlwaysSpawn" or spawn.node_find_pin("TransformScaleMethod").default_value!="OverrideRootScale":
        raise RuntimeError("original Grenade spawn policy differs")
    return dict(cost_then_cooldown_both=True,commit_return_ignored=True,forward_offset=5.,up_offset=25.,near_distance_strict=45.,
        near_distance_before_hit_boolean=True,native_hit_location_not_impact=True,authority_only_spawn_cooldown_write=True,
        montage_stop_when_ability_ends=False,montage_completion_connections=0,duration_channel="Ability.Grenade.Duration.Message",end_immediately_after_message=True)


def generate():
    stage=require_authoring_stage(arg("UEPDashRPCStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins()
    original_class=bp.GeneratedClass.get_path_name();before=snapshot(bp,"grenade-activation-before")
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in ("K2_OnPawnAvatarSet","K2_OnAbilityRemoved","K2_ActivateAbility")}
    originals=[(value,{node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes={value.get_name():semantics(value,names,set()) for value,names in originals}
    policy=audit(bp);ui=ui_audit(bp)
    mixin=ue.load_object(ue.find_class("UEPPythonMixinSet"),"/Game/UEPMixins/DA_GrenadeWidgetMixin.DA_GrenadeWidgetMixin")
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_abilities.grenade_activation_mixin",PythonClass="LyraGrenadeActivation"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"grenade-activation-after")!=before: raise RuntimeError("original Grenade class/full CDO changed")
    if any(semantics(value,names,set())!=hashes[value.get_name()] for value,names in originals): raise RuntimeError("original Grenade graphs changed")
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original Grenade signatures changed")
    bp.save_package();mixin.save_package()
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in binding["profiles"].items()}
        if counts!=dict(Python=3,BlueprintFallback=3): raise RuntimeError("three original Grenade events/Profile required")
    finally: ue.unregister_all_mixins()
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="grenadeactivation",runtime_acceptance=False,full_acceptance=False,original_class=original_class,
        original_full_cdo_preserved=True,original_graphs_unmodified=True,original_graphs=hashes,original_ui_policy=ui,original_activation_policy=policy,
        extra_signatures=signatures,native_register_restore_passed=True,actual_registered_profile_method_counts=counts,new_business_nodes=0,
        actual_activation_event_overridden=True,activation_aim_business_migrated=True,projectile_actor_business_migrated=False,assets=OUTPUTS)


try: report=generate()
except Exception: report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed": raise RuntimeError(report["error"])
ue.log("UEP_GRENADE_ACTIVATION_ASSETS_PASSED")
