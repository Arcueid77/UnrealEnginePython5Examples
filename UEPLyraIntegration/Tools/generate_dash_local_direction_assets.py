"""Keep original local direction graphs behind a typed preparation gateway."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_IfThenElse
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_dash_local_direction_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics, make_gate
from message_payload_graphs import connect
from generate_dash_selector_assets import PACKAGE, RELATIVE, METHOD, snapshot, audit

GATE = "UEPDashPrepareLocalDirection"
OUTPUTS = [RELATIVE, "Content/UEPMixins/DA_DashSelectorMixin.uasset"]


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    stage = require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    original_class = bp.GeneratedClass.get_path_name(); before = snapshot(bp, "before")
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in (METHOD, "K2_ActivateAbility", "SendInfo", "UEPDashStoreRemoteInput")}
    graph, = [value for value in bp.UbergraphPages if value.get_name() == "EventGraph"]
    nodes = {node.get_name(): node for node in graph.Nodes}
    role, selector, montage, direction, zero = [nodes[name] for name in
        ("K2Node_CallFunction_30", "K2Node_CallFunction_16", "K2Node_VariableSet_2", "K2Node_VariableSet_0", "K2Node_IfThenElse_2")]
    zero_math = nodes["K2Node_CallFunction_3"]
    if str(role.FunctionReference.MemberName) != "IsLocallyControlled" or str(selector.FunctionReference.MemberName) != METHOD:
        raise RuntimeError("original local Dash role/selector span differs")
    for source, pin, target, name in ((role, "True", selector, "execute"), (selector, "then", montage, "execute"),
            (montage, "then", direction, "execute"), (direction, "then", zero, "execute"), (direction, "Output_Get", zero_math, "A")):
        actual, = source.node_find_pin(pin).get_linked_to()
        if actual.owning_node != target or actual.name != name: raise RuntimeError("original local direction executable/data span differs")
    composite = nodes["K2Node_Composite_0"]
    if composite.node_find_pin("Positive").get_linked_to(): raise RuntimeError("original unused Positive output now has consumers")
    query, = [value for value in ue.blueprint_get_all_graphs(bp) if value.get_name() == "Get Direction"]
    query_nodes = {node.get_name(): node for node in query.Nodes}
    if len(query_nodes) != 24 or query_nodes["K2Node_CallFunction_13"].node_find_pin("QueryExtent").default_value != "500.000000,500.000000,500.000000":
        raise RuntimeError("original direction graph/native nav extent differs")
    if query_nodes["K2Node_PromotableOperator_2"].node_find_pin("B").default_value != "1.000000,1.000000,1.200000":
        raise RuntimeError("original camera directional multiplier differs")
    ignored = {(role.get_name(), "True"), (direction.get_name(), "Output_Get")}
    originals = [(value, {node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes = {value.get_name(): semantics(value, names, ignored if value == graph else set()) for value, names in originals}
    original_selector = audit(bp)
    make_gate(bp, GATE, None); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    call = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, GATE)); branch = graph.graph_add_node(K2Node_IfThenElse)
    role.node_find_pin("True").break_link_to(selector.node_find_pin("execute"))
    connect(role, "True", call, "execute"); connect(call, "then", branch, "execute"); connect(call, "ReturnValue", branch, "Condition")
    connect(branch, "then", selector, "execute"); connect(branch, "else", zero, "execute")
    # Do not rely on an impure setter's cached Output_Get on the bypass path.
    getter = graph.graph_add_node_variable_get("Direction")
    direction.node_find_pin("Output_Get").break_link_to(zero_math.node_find_pin("A")); connect(getter, "Direction", zero_math, "A")
    call.NodePosX, call.NodePosY = role.NodePosX+260, role.NodePosY
    branch.NodePosX, branch.NodePosY = role.NodePosX+520, role.NodePosY
    mixin = bp.GeneratedClass.get_cdo().GetPythonMixinSet()
    if str(mixin.DefaultProfile) != "Python": raise RuntimeError("accepted Dash default changed")
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities.dash_local_direction_mixin",
        PythonClass="LyraDashLocalDirection"+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or snapshot(bp, "after") != before:
        raise RuntimeError("local direction revision changed original class/full CDO")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()): raise RuntimeError("original Dash signature/Net flags changed")
    if any(semantics(value, names, ignored if value == graph else set()) != hashes[value.get_name()] for value, names in originals):
        raise RuntimeError("original direction/RPC/selector business graph changed")
    if len(graph.Nodes)-len(nodes) != 3: raise RuntimeError("local direction gateway footprint differs")
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == bp.GeneratedClass]
        counts = {name: len(value["functions"]) for name, value in binding["profiles"].items()}
        if counts != dict(Python=3, BlueprintFallback=3): raise RuntimeError("direction/selector/remote input registration differs")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()): raise RuntimeError("original signatures did not restore")
    bp.save_package(); mixin.save_package()
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    return dict(status="passed", kind="dashlocaldirection", runtime_acceptance=False, full_acceptance=False, original_class=original_class,
        original_full_cdo_preserved=True, original_signatures=signatures, native_server_rpc_flags_preserved=True,
        original_business_graphs_preserved_with_dispatch=True, original_selector=original_selector, original_graphs=hashes,
        local_direction_transport_nodes=5, new_business_nodes=0, unused_positive_output_retained=True, native_direction_property_read=True,
        native_register_restore_passed=True, actual_registered_profile_method_counts=counts, native_commit_tasks_animation_movement_retained=True,
        whole_dash_activation_migrated=False, gate_signature=ue.describe_function(bp.GeneratedClass, GATE),
        dispatch=dict(entry="IsLocallyControlled.True", fallback_true="SelectDirectionalMontage,Montage,Direction", python_false="Vector_IsNearlyZero"),
        assets=OUTPUTS, reference_hashes={str(reference): hashlib.sha256(reference.read_bytes()).hexdigest()})


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
(ue.log if report["status"] == "passed" else ue.log_error)("UEP_DASH_LOCAL_DIRECTION_ASSETS_"+report["status"].upper())
