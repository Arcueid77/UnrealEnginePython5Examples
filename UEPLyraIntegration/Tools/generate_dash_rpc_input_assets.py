"""Gate two original RPC-receiver stores, preserving its native network UFunction."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_FunctionResult, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_dash_rpc_input_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_dash_selector_assets import PACKAGE, RELATIVE, METHOD, snapshot, audit

GATE = "UEPDashStoreRemoteInput"
OUTPUTS = [RELATIVE, "Content/UEPMixins/DA_DashSelectorMixin.uasset"]


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    stage = require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    before = snapshot(bp, "before"); cls_name = bp.GeneratedClass.get_path_name()
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in (METHOD, "K2_ActivateAbility", "SendInfo")}
    rpc = signatures["SendInfo"]
    if int(rpc["flags"]) & (0x40|0x80|0x200000) != (0x40|0x80|0x200000):
        raise RuntimeError("original SendInfo must remain a reliable server RPC")
    graph, = [value for value in bp.UbergraphPages if value.get_name() == "EventGraph"]
    nodes = {node.get_name(): node for node in graph.Nodes}
    entry, first, second, commit = [nodes[name] for name in
        ("K2Node_CustomEvent_1", "K2Node_VariableSet_5", "K2Node_VariableSet_6", "K2Node_CallFunction_17")]
    if str(entry.CustomFunctionName) != "SendInfo" or str(first.VariableReference.MemberName) != "Direction" or str(second.VariableReference.MemberName) != "Montage":
        raise RuntimeError("original two-store RPC span differs")
    for source, output, target, pin in ((entry, "then", first, "execute"), (first, "then", second, "execute"),
            (second, "then", commit, "execute"), (entry, "Vector", first, "Direction"), (entry, "Montage", second, "Montage")):
        actual, = source.node_find_pin(output).get_linked_to()
        if actual.owning_node != target or actual.name != pin: raise RuntimeError("original RPC span link differs")
    if str(commit.FunctionReference.MemberName) != "K2_CommitAbility": raise RuntimeError("original native continuation differs")
    ignored = {(entry.get_name(), "then")}
    originals = [(value, {node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes = {value.get_name(): semantics(value, names, ignored if value == graph else set()) for value, names in originals}
    selector = audit(bp)
    gate = ue.blueprint_add_function(bp, GATE); gate_entry = gate.Nodes[0]
    for name in ("Vector", "Montage"):
        pin = entry.node_find_pin(name)
        gate_entry.node_create_pin(1, EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category,
            PinSubCategoryObject=pin.sub_category_object), name)
    result = gate.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "ReturnValue")
    result.node_find_pin("ReturnValue").default_value = "true"; connect(gate_entry, "then", result, "execute")
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    call = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, GATE)); branch = graph.graph_add_node(K2Node_IfThenElse)
    entry.node_find_pin("then").break_link_to(first.node_find_pin("execute"))
    connect(entry, "then", call, "execute"); connect(call, "then", branch, "execute")
    connect(call, "ReturnValue", branch, "Condition"); connect(branch, "then", first, "execute"); connect(branch, "else", commit, "execute")
    for name in ("Vector", "Montage"): connect(entry, name, call, name)
    call.NodePosX, call.NodePosY = entry.NodePosX+260, entry.NodePosY
    branch.NodePosX, branch.NodePosY = entry.NodePosX+520, entry.NodePosY
    mixin = bp.GeneratedClass.get_cdo().GetPythonMixinSet()
    if str(mixin.DefaultProfile) != "Python": raise RuntimeError("accepted Dash default Profile changed")
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities.dash_rpc_input_mixin",
        PythonClass="LyraDashRPCInput"+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != cls_name or snapshot(bp, "after") != before:
        raise RuntimeError("RPC revision changed original class/full CDO")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()):
        raise RuntimeError("RPC revision changed an original reflected signature or Net flags")
    if any(semantics(value, names, ignored if value == graph else set()) != hashes[value.get_name()] for value, names in originals):
        raise RuntimeError("RPC revision changed original business graph semantics")
    if len(gate.Nodes) != 2 or len(graph.Nodes)-len(nodes) != 2: raise RuntimeError("RPC adapter footprint differs")
    counts = None
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == bp.GeneratedClass]
        counts = {name: len(value["functions"]) for name, value in binding["profiles"].items()}
        if counts != dict(Python=2, BlueprintFallback=2): raise RuntimeError("RPC input/selector registration differs")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()):
        raise RuntimeError("RPC revision did not restore original signatures")
    bp.save_package(); mixin.save_package()
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    return dict(status="passed", kind="dashrpcinput", runtime_acceptance=False, full_acceptance=False,
        original_class=cls_name, original_full_cdo_preserved=True, original_signatures=signatures,
        native_server_rpc_flags_preserved=True, original_business_graphs_preserved_with_dispatch=True,
        original_selector=selector, original_graphs=hashes, transport_nodes=4, new_business_nodes=0,
        python_replaces_two_remote_stores=True, native_commit_tasks_animation_movement_retained=True,
        whole_dash_activation_migrated=False, actual_registered_profile_method_counts=counts,
        gate_signature=ue.describe_function(bp.GeneratedClass, GATE), native_register_restore_passed=True,
        dispatch=dict(entry="SendInfo", python_false_continuation="K2_CommitAbility", fallback_true="Direction,Montage,K2_CommitAbility"),
        assets=OUTPUTS, reference_hashes={str(reference): hashlib.sha256(reference.read_bytes()).hexdigest()})


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
(ue.log if report["status"] == "passed" else ue.log_error)("UEP_DASH_RPC_INPUT_ASSETS_"+report["status"].upper())
