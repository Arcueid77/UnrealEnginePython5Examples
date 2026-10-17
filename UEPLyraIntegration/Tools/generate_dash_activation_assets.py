"""One native task entry; actual activation ownership is the Python override."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_dash_activation_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_dash_selector_assets import PACKAGE, RELATIVE, METHOD, snapshot

TASKS = "UEPDashStartNativeTasks"
OUTPUTS = [RELATIVE, "Content/UEPMixins/DA_DashSelectorMixin.uasset"]
METHODS = (METHOD, "K2_ActivateAbility", "SendInfo", "UEPDashStoreRemoteInput", "UEPDashPrepareLocalDirection")


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    stage = require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    before = snapshot(bp, "before"); original_class = bp.GeneratedClass.get_path_name()
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in METHODS}
    if signatures["K2_ActivateAbility"]["parameters"] or signatures["K2_ActivateAbility"]["flags"] & 0x40:
        raise RuntimeError("actual zero-argument non-Net activation event required")
    graph, = [value for value in bp.UbergraphPages if value.get_name() == "EventGraph"]
    nodes = {node.get_name(): node for node in graph.Nodes}
    task = nodes["K2Node_LatentAbilityCall_1"]
    if task.ProxyFactoryFunctionName != "CreatePlayMontageAndWaitProxy": raise RuntimeError("original native montage task differs")
    original_inputs = {(pin.owning_node.get_name(), pin.name) for pin in task.node_find_pin("execute").get_linked_to()}
    if original_inputs != {("K2Node_CallFunction_17", "then"), ("K2Node_CallFunction_21", "then"), ("K2Node_Knot_1", "OutputPin")}:
        raise RuntimeError("original authority/RPC native task merge differs: "+repr(original_inputs))
    originals = [(value, {node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes = {value.get_name(): semantics(value, names, set()) for value, names in originals}
    entry = graph.graph_add_node(K2Node_CustomEvent); entry.CustomFunctionName = TASKS; graph.graph_reconstruct_node(entry)
    connect(entry, "then", task, "execute")
    entry.NodePosX, entry.NodePosY = task.NodePosX-400, task.NodePosY-300
    mixin = bp.GeneratedClass.get_cdo().GetPythonMixinSet()
    if str(mixin.DefaultProfile) != "Python": raise RuntimeError("accepted Dash default changed")
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities.dash_activation_mixin",
        PythonClass="LyraDashActivation"+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or snapshot(bp, "after") != before:
        raise RuntimeError("activation revision changed original class/full CDO")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()): raise RuntimeError("existing signature/Net flags changed")
    if any(semantics(value, names, set()) != hashes[value.get_name()] for value, names in originals): raise RuntimeError("original business graph changed")
    if len(graph.Nodes)-len(nodes) != 1: raise RuntimeError("native task entry footprint differs")
    task_signature = ue.describe_function(bp.GeneratedClass, TASKS)
    if task_signature["parameters"] or task_signature["flags"] & 0x40: raise RuntimeError("native task entry must not introduce an RPC")
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == bp.GeneratedClass]
        counts = {name: len(value["functions"]) for name, value in binding["profiles"].items()}
        if counts != dict(Python=4, BlueprintFallback=4): raise RuntimeError("actual activation/three helper overrides not registered")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()): raise RuntimeError("existing signatures did not restore")
    bp.save_package(); mixin.save_package()
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    return dict(status="passed", kind="dashactivation", runtime_acceptance=False, full_acceptance=False, original_class=original_class,
        original_full_cdo_preserved=True, original_signatures=signatures, native_server_rpc_flags_preserved=True,
        original_business_graphs_preserved_with_dispatch=True, original_graphs=hashes, native_task_entry_nodes=1, new_business_nodes=0,
        native_register_restore_passed=True, actual_registered_profile_method_counts=counts, native_task_entry=TASKS, task_entry_signature=task_signature,
        actual_activation_event_overridden=True, native_commit_tasks_animation_movement_retained=True, whole_dash_activation_migrated=False,
        assets=OUTPUTS, reference_hashes={str(reference): hashlib.sha256(reference.read_bytes()).hexdigest()})


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
(ue.log if report["status"] == "passed" else ue.log_error)("UEP_DASH_ACTIVATION_ASSETS_"+report["status"].upper())
