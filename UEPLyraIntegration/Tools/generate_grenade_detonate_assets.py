"""Route after original RPC/DoOnce; retain original body and native delegate."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_grenade_detonate_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_dash_selector_assets import snapshot
from generate_grenade_vfx_assets import PACKAGE, RELATIVE, audit as vfx_audit

BODY, BIND = "UEPGrenadeDetonateBody", "UEPGrenadeBindTrailFinished"


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, PACKAGE)
    ue.unregister_all_mixins()
    before, original_class = snapshot(bp, "grenade-detonate-before"), bp.GeneratedClass.get_path_name()
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in
                  ("Setup VFX", "PostLaunchCleanup", "Teleport Grenade", "Destroy Grenade", "Detonate", "ReceiveBeginPlay", "ReceiveHit")}
    if signatures["Detonate"]["flags"] & (0x40|0x80|0x4000) != (0x40|0x80|0x4000):
        raise RuntimeError("original reliable multicast RPC required")
    graph, = [value for value in ue.blueprint_get_all_graphs(bp) if value.get_name() == "EventGraph"]
    nodes = {node.get_name(): node for node in graph.Nodes}
    if len(nodes) != 132:
        raise RuntimeError("accepted original Actor footprint required")
    entry, once, cue, bind = [nodes[name] for name in
                            ("K2Node_CustomEvent_0", "K2Node_MacroInstance_1", "K2Node_CallFunction_21", "K2Node_AddDelegate_1")]
    if str(entry.CustomFunctionName) != "Detonate" or str(cue.FunctionReference.MemberName) != "ExecuteGameplayCueOnActor":
        raise RuntimeError("original RPC/Cue endpoints differ")
    for source, pin, target, target_pin in ((entry, "then", once, "execute"), (once, "Completed", cue, "execute")):
        linked, = source.node_find_pin(pin).get_linked_to()
        if linked.owning_node != target or linked.name != target_pin:
            raise RuntimeError("original RPC/DoOnce/Cue path differs")
    if once.node_find_pin("Reset").get_linked_to() or once.node_find_pin("Start Closed").get_linked_to():
        raise RuntimeError("original one-shot state differs")
    ignored = {(once.get_name(), "Completed"), (cue.get_name(), "execute")}
    graphs = [(value, {node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes = {value.get_name(): semantics(value, names, ignored if value == graph else set()) for value, names in graphs}
    vfx = vfx_audit(bp)
    body = graph.graph_add_node(K2Node_CustomEvent)
    body.CustomFunctionName = BODY
    graph.graph_reconstruct_node(body)
    connect(body, "then", cue, "execute")
    binding = graph.graph_add_node(K2Node_CustomEvent)
    binding.CustomFunctionName = BIND
    graph.graph_reconstruct_node(binding)
    connect(binding, "then", bind, "execute")
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    call = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, BODY))
    once.node_find_pin("Completed").break_link_to(cue.node_find_pin("execute"))
    connect(once, "Completed", call, "execute")
    if call.node_find_pin("then").get_linked_to():
        raise RuntimeError("Python body must not fall through to original body")
    call.NodePosX, call.NodePosY = once.NodePosX+250, once.NodePosY
    mixin = bp.GeneratedClass.get_cdo().GetPythonMixinSet()
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_weapons.grenade_detonate_mixin",
                       PythonClass="LyraGrenadeDetonate"+name+"Profile") for name in ("Python", "BlueprintFallback")]
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or snapshot(bp, "grenade-detonate-after") != before:
        raise RuntimeError("original Actor class/full CDO changed")
    if any(semantics(value, names, ignored if value == graph else set()) != hashes[value.get_name()] for value, names in graphs):
        raise RuntimeError("original graph changed outside the two dispatch endpoints")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()):
        raise RuntimeError("original Actor signatures or RPC flags changed")
    transports = {name: ue.describe_function(bp.GeneratedClass, name) for name in (BODY, BIND)}
    if len(graph.Nodes)-len(nodes) != 3 or any(value["parameters"] or value["flags"] & 0x40 for value in transports.values()):
        raise RuntimeError("three transport-only nodes and ordinary zero-input functions required")
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        registered, = [value for value in ue.get_registered_mixins() if value["target_class"] == bp.GeneratedClass]
        counts = {name: len(value["functions"]) for name, value in registered["profiles"].items()}
        if counts != dict(Python=7, BlueprintFallback=7):
            raise RuntimeError("seven Actor methods per Profile required")
    finally:
        ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()):
        raise RuntimeError("original signatures did not restore")
    bp.save_package()
    mixin.save_package()
    return dict(status="passed", kind="grenadedetonate", runtime_acceptance=False, full_acceptance=False,
                original_class=original_class, original_full_cdo_preserved=True, original_graphs=hashes,
                original_business_graphs_preserved_with_dispatch=True, original_vfx_policy=vfx,
                extra_signatures=signatures, transport_signatures=transports, transport_nodes=3, new_business_nodes=0,
                declared_dispatch_endpoints=sorted([list(value) for value in ignored]),
                native_server_rpc_flags_preserved=True, native_do_once_retained=True, native_weak_delegate_retained=True,
                python_body_has_no_original_fallthrough=True, native_register_restore_passed=True,
                actual_registered_profile_method_counts=counts, actor_detonate_damage_business_migrated=True,
                assets=[RELATIVE, "Content/UEPMixins/DA_GrenadeVFXMixin.uasset"])


try:
    report = generate()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
    ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["status"] != "passed":
    raise RuntimeError(report["error"])
ue.log("UEP_GRENADE_DETONATE_ASSETS_PASSED")
