"""Retain original BP controls; only typed task/Delay dispatch and data transport."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_CustomEvent, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_dash_tasks_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics, make_gate, insert_gate
from message_payload_graphs import connect
from generate_dash_selector_assets import PACKAGE, RELATIVE, snapshot

TASKS, DELAY, AFTER = "UEPDashStartNativeTasks", "UEPDashBeginNativeDelay", "UEPDashAfterNativeDelay"
VALUE = "UEPDashDelayDuration"
ENDED, GUARD = "UEPDashNativeEnded", "UEPDashTearingDown"
METHODS = ("SelectDirectionalMontage", "K2_ActivateAbility", "SendInfo", "UEPDashStoreRemoteInput", "UEPDashPrepareLocalDirection", TASKS, "K2_OnEndAbility")
OUTPUTS = [RELATIVE, "Content/UEPMixins/DA_DashSelectorMixin.uasset"]


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))
def normal_snapshot(bp, name):
    return "\n".join(line for line in snapshot(bp, name).splitlines() if not line.strip().startswith((VALUE+"=", GUARD+"=")))


def generate():
    stage = require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    if any(str(value.VarName) == VALUE for value in bp.NewVariables): raise RuntimeError("fresh task transport property required")
    original_class = bp.GeneratedClass.get_path_name(); before = normal_snapshot(bp, "before")
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in METHODS}
    if signatures["K2_OnEndAbility"]["owner"] != "/Script/GameplayAbilities.GameplayAbility":
        raise RuntimeError("native inherited empty End event required; do not hide parent BP business")
    graph, = [value for value in bp.UbergraphPages if value.get_name() == "EventGraph"]
    nodes = {node.get_name(): node for node in graph.Nodes}
    task, root, delay, difference = [nodes[name] for name in ("K2Node_LatentAbilityCall_1", "K2Node_LatentAbilityCall_0", "K2Node_CallFunction_8", "K2Node_PromotableOperator_0")]
    incoming = [(nodes["K2Node_Knot_1"], "OutputPin"), (nodes["K2Node_CallFunction_21"], "then"), (nodes["K2Node_CallFunction_17"], "then")]
    for node, pin in incoming:
        destination, = node.node_find_pin(pin).get_linked_to()
        if destination.owning_node != task or destination.name != "execute": raise RuntimeError("accepted native task ingress differs")
    remote_call, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallFunction" and str(node.FunctionReference.MemberName) == "UEPDashStoreRemoteInput"]
    condition, = remote_call.node_find_pin("ReturnValue").get_linked_to(); remote_branch = condition.owning_node
    old_remote, = remote_branch.node_find_pin("else").get_linked_to()
    if old_remote.owning_node != nodes["K2Node_CallFunction_17"]: raise RuntimeError("accepted remote Commit rejoin differs")
    native_delay, = root.node_find_pin("OnFinish").get_linked_to()
    duration_input, = delay.node_find_pin("Duration").get_linked_to()
    end_input, = delay.node_find_pin("then").get_linked_to()
    if native_delay.owning_node != delay or duration_input.owning_node != difference or end_input.owning_node != nodes["K2Node_CallFunction_5"]:
        raise RuntimeError("original root-finish/duration/Delay/End span differs")
    if task.node_find_pin("bStopWhenAbilityEnds").default_value != "false" or root.node_find_pin("bIsAdditive").default_value != "true" or root.node_find_pin("ClampVelocityOnFinish").default_value != "1000.000000":
        raise RuntimeError("original montage/RootMotion primitive settings differ")
    ignored = {(node.get_name(), pin) for node, pin in incoming}
    ignored.update(((task.get_name(), "execute"), (remote_branch.get_name(), "else"), (old_remote.owning_node.get_name(), old_remote.name),
        (root.get_name(), "OnFinish"), (delay.get_name(), "execute"), (delay.get_name(), "Duration"), (difference.get_name(), duration_input.name),
        (delay.get_name(), "then"), (end_input.owning_node.get_name(), end_input.name)))
    if len(ignored) != 12: raise RuntimeError("declared task/Delay dispatch endpoint count differs")
    originals = [(value, {node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes = {value.get_name(): semantics(value, names, ignored if value == graph else set()) for value, names in originals}
    pin = delay.node_find_pin("Duration")
    real_type = EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category, PinSubCategoryObject=pin.sub_category_object)
    ue.blueprint_add_member_variable(bp, VALUE, real_type)
    ue.blueprint_add_member_variable(bp, GUARD, EdGraphPinType(PinCategory="bool"))
    end_event = graph.graph_add_node_event(ue.find_class("GameplayAbility"), "K2_OnEndAbility")
    end_event.set_property("bOverrideFunction", True)
    make_gate(bp, ENDED, "bWasCancelled", end_event.node_find_pin("bWasCancelled"))
    make_gate(bp, AFTER, None); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    routed_task = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, TASKS))
    for node, pin in incoming:
        node.node_find_pin(pin).break_link_to(task.node_find_pin("execute")); connect(node, pin, routed_task, "execute")
    # Python remote body now owns both Commit and task start; no second BP body.
    remote_branch.node_find_pin("else").break_link_to(old_remote)
    original_store = graph.graph_add_node_variable_set(VALUE)
    root.node_find_pin("OnFinish").break_link_to(delay.node_find_pin("execute"))
    connect(root, "OnFinish", original_store, "execute"); duration_input.make_link_to(original_store.node_find_pin(VALUE))
    connect(original_store, "then", delay, "execute")
    duration_input.break_link_to(delay.node_find_pin("Duration"))
    getter = graph.graph_add_node_variable_get(VALUE); connect(getter, VALUE, delay, "Duration")
    entry = graph.graph_add_node(K2Node_CustomEvent); entry.CustomFunctionName = DELAY; graph.graph_reconstruct_node(entry)
    entry.node_create_pin(1, real_type, "Duration")
    python_store = graph.graph_add_node_variable_set(VALUE)
    connect(entry, "then", python_store, "execute"); connect(entry, "Duration", python_store, VALUE); connect(python_store, "then", delay, "execute")
    insert_gate(graph, delay, "then", getattr(bp.GeneratedClass, AFTER))
    # End runs natively even while a Profile is disarmed/tearing down. Bypass
    # the mixed cleanup gate in that state; teardown already closes its scope.
    guard = graph.graph_add_node_variable_get(GUARD); guard_branch = graph.graph_add_node(K2Node_IfThenElse)
    end_call = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, ENDED))
    connect(end_event, "then", guard_branch, "execute"); connect(guard, GUARD, guard_branch, "Condition")
    connect(guard_branch, "else", end_call, "execute"); connect(end_event, "bWasCancelled", end_call, "bWasCancelled")
    if guard_branch.node_find_pin("then").get_linked_to(): raise RuntimeError("teardown must bypass mixed End dispatch")
    mixin = bp.GeneratedClass.get_cdo().GetPythonMixinSet()
    if str(mixin.DefaultProfile) != "Python": raise RuntimeError("accepted Dash default changed")
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities.dash_tasks_mixin",
        PythonClass="LyraDashTasks"+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or normal_snapshot(bp, "after") != before or float(bp.GeneratedClass.get_cdo().get_property(VALUE)) != 0. or bp.GeneratedClass.get_cdo().get_property(GUARD):
        raise RuntimeError("task revision changed original class/CDO or nonzero transport default")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items() if name != "K2_OnEndAbility"): raise RuntimeError("accepted signatures changed")
    end_signature = ue.describe_function(bp.GeneratedClass, "K2_OnEndAbility")
    if end_signature["owner"] != original_class: raise RuntimeError("native End event was not compiled as an actual target-class override")
    shape = lambda signature: [{key: row[key] for key in ("name", "type", "output")} for row in signature["parameters"]]
    if shape(end_signature) != shape(signatures["K2_OnEndAbility"]): raise RuntimeError("native End transport parameter shape changed")
    if any(semantics(value, names, ignored if value == graph else set()) != hashes[value.get_name()] for value, names in originals):
        raise RuntimeError("original business graph changed outside declared dispatch")
    if len(graph.Nodes)-len(nodes) != 11: raise RuntimeError("task/Delay/guarded End transport footprint differs")
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == bp.GeneratedClass]
        counts = {name: len(value["functions"]) for name, value in binding["profiles"].items()}
        if counts != dict(Python=7, BlueprintFallback=7): raise RuntimeError("seven task/continuation/native-End methods required")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items() if name != "K2_OnEndAbility") or ue.describe_function(bp.GeneratedClass, "K2_OnEndAbility") != end_signature:
        raise RuntimeError("original task/guarded End signatures did not restore")
    bp.save_package(); mixin.save_package()
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    return dict(status="passed", kind="dashtasks", runtime_acceptance=False, full_acceptance=False, original_class=original_class,
        original_full_cdo_preserved=True, transport_default_zero=True, original_signatures=signatures, native_server_rpc_flags_preserved=True,
        original_business_graphs_preserved_with_dispatch=True, original_graphs=hashes, task_transport_nodes=15, new_business_nodes=0,
        native_register_restore_passed=True, actual_registered_profile_method_counts=counts, native_commit_tasks_animation_movement_retained=True,
        original_native_delay_reused=True, dispatch_transport_endpoints=sorted(ignored), python_rpc_body_has_no_original_fallthrough=True,
        native_end_transport_signature=end_signature, native_end_guard=GUARD, native_end_gate=ENDED, native_end_teardown_bypass=True,
        whole_dash_activation_migrated=False, native_task_entry=TASKS, native_delay_entry=DELAY, delay_transport_property=VALUE,
        after_delay_signature=ue.describe_function(bp.GeneratedClass, AFTER), native_delay_signature=ue.describe_function(bp.GeneratedClass, DELAY),
        assets=OUTPUTS, reference_hashes={str(reference): hashlib.sha256(reference.read_bytes()).hexdigest()})


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
(ue.log if report["status"] == "passed" else ue.log_error)("UEP_DASH_TASKS_ASSETS_"+report["status"].upper())
