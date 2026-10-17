"""Route the retained authority trace without duplicating original BP business."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_melee_trace_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_melee_hit_montage_assets import PACKAGE, RELATIVE, METHOD, selector
from generate_dash_selector_assets import snapshot

TRACE, ENDED, GUARD = "UEPMeleeAuthorityTrace", "UEPMeleeNativeEnded", "UEPMeleeTearingDown"
OUTPUTS = [RELATIVE, "Content/UEPMixins/DA_MeleeHitMontageMixin.uasset"]


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    original_class = bp.GeneratedClass.get_path_name(); before = snapshot(bp, "melee-trace-before")
    methods = (METHOD, "K2_ActivateAbility", "MontageHit", "K2_OnEndAbility", TRACE, ENDED)
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in methods}
    if signatures["K2_OnEndAbility"]["owner"] != original_class or signatures[TRACE]["parameters"] or signatures[TRACE]["flags"] & 0x40:
        raise RuntimeError("accepted native End/trace entry differs")
    graph, = [value for value in bp.UbergraphPages if value.get_name() == "EventGraph"]
    nodes = {node.get_name(): node for node in graph.Nodes}
    authority, capsule = (nodes[name] for name in ("K2Node_CallFunction_43", "K2Node_CallFunction_17"))
    if str(authority.FunctionReference.MemberName) != "K2_HasAuthority" or str(capsule.FunctionReference.MemberName) != "CapsuleTraceSingleForObjects":
        raise RuntimeError("original authority/capsule endpoints differ")
    link, = authority.node_find_pin("True").get_linked_to()
    if link.owning_node != capsule or link.name != "execute": raise RuntimeError("original direct authority trace path differs")
    trace, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CustomEvent" and str(node.CustomFunctionName) == TRACE]
    link, = trace.node_find_pin("then").get_linked_to()
    if link.owning_node != capsule or link.name != "execute": raise RuntimeError("retained original trace entry differs")
    ignored = {(authority.get_name(), "True"), (capsule.get_name(), "execute")}
    graphs = [(value, {node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes = {value.get_name(): semantics(value, names, ignored if value == graph else set()) for value, names in graphs}
    helper = selector(bp)
    call = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, TRACE))
    authority.node_find_pin("True").break_link_to(capsule.node_find_pin("execute"))
    connect(authority, "True", call, "execute")
    # TRACE's original body still starts at capsule. Do not route its own event
    # back to this virtual call, which would recurse on call-original.
    if call.node_find_pin("then").get_linked_to(): raise RuntimeError("Python trace must not fall through to BP")
    call.NodePosX, call.NodePosY = authority.NodePosX+260, authority.NodePosY
    mixin = bp.GeneratedClass.get_cdo().GetPythonMixinSet()
    if str(mixin.DefaultProfile) != "Python": raise RuntimeError("accepted Melee default changed")
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_abilities.melee_trace_mixin",
        PythonClass="LyraMeleeTrace"+name+"Profile") for name in ("Python", "BlueprintFallback")]
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or snapshot(bp, "melee-trace-after") != before:
        raise RuntimeError("Melee trace changed original class/full CDO")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()): raise RuntimeError("accepted Melee ABI changed")
    if any(semantics(value, names, ignored if value == graph else set()) != hashes[value.get_name()] for value, names in graphs):
        raise RuntimeError("original Melee graph changed outside declared authority dispatch endpoints")
    if len(graph.Nodes)-len(nodes) != 1: raise RuntimeError("one dispatch node required")
    link, = trace.node_find_pin("then").get_linked_to()
    if link.owning_node != capsule or link.name != "execute": raise RuntimeError("original capsule entry was replaced")
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == bp.GeneratedClass]
        counts = {name: len(value["functions"]) for name, value in binding["profiles"].items()}
        if counts != dict(Python=4, BlueprintFallback=4): raise RuntimeError("all four Melee methods must register")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()): raise RuntimeError("Melee router did not restore ABI")
    bp.save_package(); mixin.save_package()
    return dict(status="passed", kind="meleetrace", runtime_acceptance=False, full_acceptance=False, original_class=original_class,
        original_full_cdo_preserved=True, native_server_rpc_flags_preserved=True, original_signatures=signatures, original_graphs=hashes,
        original_business_graphs_preserved_with_dispatch=True, native_commit_tasks_animation_movement_retained=True,
        actual_registered_profile_method_counts=counts, native_register_restore_passed=True, new_business_nodes=0, transport_nodes=1,
        native_end_transport_signature=signatures["K2_OnEndAbility"], native_end_teardown_bypass=True, native_end_guard=GUARD,
        native_end_gate=ENDED, native_trace_entry=TRACE, native_trace_signature=signatures[TRACE],
        declared_dispatch_endpoints=sorted([list(value) for value in ignored]), original_trace_body_retained=True,
        python_trace_has_no_original_fallthrough=True, original_selector=helper,
        whole_melee_trace_damage_business_migrated=False, whole_dash_activation_migrated=False, assets=OUTPUTS)


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
(ue.log if report["status"] == "passed" else ue.log_error)("UEP_MELEE_TRACE_ASSETS_"+report["status"].upper())
