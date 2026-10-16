"""Keep original widget graphs; one parent Set and typed cleanup transport."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "generate_action_touch_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from message_payload_graphs import read_graph, broadcast_graph, connect

PROXY, RESUME = "UEPOriginalActionDurationProxy", "UEPResumeActionDuration"


def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))


def one(values):
    if len(values) != 1:
        raise RuntimeError("one action-touch original graph/entry required")
    return values[0]


def generate():
    stage = require_authoring_stage(arg("UEPActionTouchStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes = {str(reference/"Content/UI/Hud"/(name+".uasset")):
        hashlib.sha256((reference/"Content/UI/Hud"/(name+".uasset")).read_bytes()).hexdigest()
        for name in ("W_ActionTouchButton", "W_ActionTouchButton_MobileOnly")}
    ue.unregister_all_mixins()
    bps = [ue.load_object(Blueprint, "/Game/UI/Hud/"+n+"."+n) for n in ("W_ActionTouchButton", "W_ActionTouchButton_MobileOnly")]
    parent, child = bps
    original_tick_metadata = {bp.get_path_name(): {field: bp.GeneratedClass.get_cdo().get_property(field)
        for field in ("TickFrequency", "bHasScriptImplementedTick")} for bp in bps}
    event = parent.UbergraphPages[0]
    action = one([n for n in event.Nodes if n.get_class().get_name() == "K2Node_AsyncAction_ListenForGameplayMessages"])
    groups = []
    for bp in bps:
        for graph in list(bp.FunctionGraphs)+list(bp.UbergraphPages):
            ignored = {(action.get_name(), "then")} if graph == event else set()
            names = {n.get_name() for n in graph.Nodes}
            groups.append(dict(bp=bp, name=graph.get_name(), names=names, ignored=ignored, before=semantics(graph, names, ignored)))
    if PROXY in {str(v.VarName) for v in parent.NewVariables}:
        raise RuntimeError("fresh action-touch authoring required")
    ue.blueprint_add_member_variable(parent, PROXY, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("AsyncAction_ListenForGameplayMessage")))
    ue.compile_blueprint(parent)
    continuation = action.node_find_pin("then").get_linked_to()
    if continuation:
        raise RuntimeError("original duration factory continuation changed")
    setter = event.graph_add_node_variable_set(PROXY)
    connect(action, "then", setter, "execute"); connect(action, "AsyncTaskProxy", setter, PROXY)
    ue.blueprint_add_function(parent, RESUME)  # Signature only; no BP business.
    payload = ue.find_struct("LyraInteractionDurationMessage")
    read_graph(parent, "ActionDuration", payload, ue.find_class("AsyncAction_ListenForGameplayMessage"))
    broadcast_graph(parent, "ActionDuration", payload, ue.find_class("GameplayMessageSubsystem"))
    ue.compile_blueprint(parent)
    name = "DA_ActionTouchMixin"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None:
        raise RuntimeError("fresh action-touch Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=p, PythonModule="uep_lyra_hud.action_touch_mixin",
        PythonClass="LyraActionTouch"+p+"Profile") for p in ("Python", "BlueprintFallback")]
    ue.unregister_all_mixins(); ue.blueprint_configure_mixin(parent, mixin, "Python", "PythonMixinProfile")
    for bp, name in zip(bps, ("W_ActionTouchButton_C", "W_ActionTouchButton_MobileOnly_C")):
        ue.unregister_all_mixins(); ue.compile_blueprint(bp)
        if int(bp.Status) == 2 or bp.GeneratedClass.get_name() != name or bp.GeneratedClass.get_cdo().GetPythonMixinSet() != mixin:
            raise RuntimeError("action-touch retained class/inherited Set failed")
        if any(bp.GeneratedClass.get_cdo().get_property(field) != value for field, value in original_tick_metadata[bp.get_path_name()].items()):
            raise RuntimeError("action-touch original native Tick scheduling changed")
    proofs = []
    for row in groups:
        graph = one([g for g in ue.blueprint_get_all_graphs(row["bp"]) if g.get_name() == row["name"]])
        if semantics(graph, row["names"], row["ignored"]) != row["before"]:
            raise RuntimeError("action-touch original graph changed: "+row["name"])
        proofs.append(dict(asset=row["bp"].get_path_name(), graph=row["name"], original_semantic_digest=row["before"],
                           dispatch_transport_endpoints=sorted(row["ignored"])))
    for bp in bps+[mixin]:
        bp.save_package()
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("official action-touch asset changed")
    return dict(status="passed", runtime_acceptance=False, class_preserved=True, single_parent_interface_set=True,
        original_blocks_retained=True, gate_count=0, original_graphs=proofs, direct_function_mixin=True,
        original_async_proxy_exposed_for_owned_cleanup=True, typed_payload_vm_transport=True,
        original_tick_metadata=original_tick_metadata, native_tick_metadata_preserved=True,
        resume_declaration_business_logic=False, reference_hashes=hashes)


try:
    report = generate()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPGenerateActionTouchResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_ACTION_TOUCH_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
