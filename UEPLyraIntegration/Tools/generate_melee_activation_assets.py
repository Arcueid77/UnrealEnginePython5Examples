"""Preserve accepted Melee helper and original trace body behind native entry."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_CustomEvent, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_melee_activation_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics, make_gate
from message_payload_graphs import connect
from generate_melee_hit_montage_assets import PACKAGE, RELATIVE, METHOD, selector
from generate_dash_selector_assets import snapshot

TRACE, ENDED, GUARD = "UEPMeleeAuthorityTrace", "UEPMeleeNativeEnded", "UEPMeleeTearingDown"
OUTPUTS = [RELATIVE, "Content/UEPMixins/DA_MeleeHitMontageMixin.uasset"]


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))
def cdo(bp, name): return "\n".join(line for line in snapshot(bp, name).splitlines() if not line.strip().startswith(GUARD+"="))


def generate():
    stage = require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    original_class = bp.GeneratedClass.get_path_name(); before = cdo(bp, "melee-entry-before")
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in (METHOD, "K2_ActivateAbility", "MontageHit")}
    old_end = ue.describe_function(bp.GeneratedClass, "K2_OnEndAbility")
    if old_end["owner"] != "/Script/GameplayAbilities.GameplayAbility": raise RuntimeError("do not hide parent End business")
    graphs = [(value, {node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes = {value.get_name(): semantics(value, names, set()) for value, names in graphs}; helper = selector(bp)
    graph, = [value for value in bp.UbergraphPages if value.get_name() == "EventGraph"]
    nodes = {node.get_name(): node for node in graph.Nodes}; capsule = nodes["K2Node_CallFunction_17"]
    if str(capsule.FunctionReference.MemberName) != "CapsuleTraceSingleForObjects": raise RuntimeError("original authority trace entry differs")
    ue.blueprint_add_member_variable(bp, GUARD, EdGraphPinType(PinCategory="bool"))
    end = graph.graph_add_node_event(ue.find_class("GameplayAbility"), "K2_OnEndAbility"); end.set_property("bOverrideFunction", True)
    make_gate(bp, ENDED, "bWasCancelled", end.node_find_pin("bWasCancelled"))
    trace = graph.graph_add_node(K2Node_CustomEvent); trace.CustomFunctionName = TRACE; graph.graph_reconstruct_node(trace)
    connect(trace, "then", capsule, "execute")
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    guard = graph.graph_add_node_variable_get(GUARD); branch = graph.graph_add_node(K2Node_IfThenElse)
    callback = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, ENDED))
    connect(end, "then", branch, "execute"); connect(guard, GUARD, branch, "Condition")
    connect(branch, "else", callback, "execute"); connect(end, "bWasCancelled", callback, "bWasCancelled")
    if branch.node_find_pin("then").get_linked_to(): raise RuntimeError("teardown must bypass mixed End")
    mixin = bp.GeneratedClass.get_cdo().GetPythonMixinSet()
    if str(mixin.DefaultProfile) != "Python": raise RuntimeError("accepted Melee default changed")
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_abilities.melee_activation_mixin",
        PythonClass="LyraMeleeActivation"+name+"Profile") for name in ("Python", "BlueprintFallback")]
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or cdo(bp, "melee-entry-after") != before or bp.GeneratedClass.get_cdo().get_property(GUARD):
        raise RuntimeError("Melee activation changed original class/CDO or guard default")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()): raise RuntimeError("accepted Melee signatures changed")
    if any(semantics(value, names, set()) != hashes[value.get_name()] for value, names in graphs): raise RuntimeError("original Melee graph changed")
    end_signature = ue.describe_function(bp.GeneratedClass, "K2_OnEndAbility")
    if end_signature["owner"] != original_class or len(graph.Nodes)-len(nodes) != 5: raise RuntimeError("actual guarded End/trace-entry footprint differs")
    trace_signature = ue.describe_function(bp.GeneratedClass, TRACE)
    if trace_signature["parameters"] or trace_signature["flags"] & 0x40: raise RuntimeError("authority trace transport must not be a new RPC")
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == bp.GeneratedClass]
        counts = {name: len(value["functions"]) for name, value in binding["profiles"].items()}
        if counts != dict(Python=3, BlueprintFallback=3): raise RuntimeError("helper/actual activation/End routing incomplete")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()) or ue.describe_function(bp.GeneratedClass, "K2_OnEndAbility") != end_signature:
        raise RuntimeError("Melee activation router did not restore signatures")
    bp.save_package(); mixin.save_package()
    return dict(status="passed", kind="meleeactivation", runtime_acceptance=False, full_acceptance=False, original_class=original_class,
        original_full_cdo_preserved=True, native_server_rpc_flags_preserved=True, original_signatures=signatures, original_graphs=hashes,
        original_business_graphs_preserved_with_dispatch=True, native_commit_tasks_animation_movement_retained=True,
        actual_registered_profile_method_counts=counts, native_register_restore_passed=True, new_business_nodes=0, transport_nodes=7,
        actual_activation_event_overridden=True, native_end_transport_signature=end_signature, native_end_teardown_bypass=True,
        native_end_guard=GUARD, native_end_gate=ENDED, native_trace_entry=TRACE, native_trace_signature=trace_signature,
        original_selector=helper, whole_melee_trace_damage_business_migrated=False, whole_dash_activation_migrated=False, assets=OUTPUTS)


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
(ue.log if report["status"] == "passed" else ue.log_error)("UEP_MELEE_ACTIVATION_ASSETS_"+report["status"].upper())
