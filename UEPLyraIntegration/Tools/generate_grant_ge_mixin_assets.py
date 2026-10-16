"""Configure one retained grant-GE BP; Timeline/data and old blocks stay intact."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_grant_ge_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import make_gate, insert_gate, semantics

ASSET = "/ShooterCore/Blueprint/B_GrantAbilityPad_ApplyGE.B_GrantAbilityPad_ApplyGE"
PREFIX, TEXT = "UEPDispatchGrantGE", "UEPTransferGrantGEText"

def argument(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))

def one(values):
    if len(values) != 1:
        raise RuntimeError("expected one unambiguous BP entry")
    return values[0]

def hooks(bp):
    cs = one([graph for graph in bp.FunctionGraphs if graph.get_name() == "UserConstructionScript"])
    graph = bp.UbergraphPages[0]
    timeline = one([node for node in graph.Nodes if node.get_class().get_name() == "K2Node_Timeline"])
    begin = one([node for node in graph.Nodes if node.get_class().get_name() == "K2Node_ComponentBoundEvent" and str(node.DelegatePropertyName) == "OnComponentBeginOverlap"])
    end = one([node for node in graph.Nodes if node.get_class().get_name() == "K2Node_ComponentBoundEvent" and str(node.DelegatePropertyName) == "OnComponentEndOverlap"])
    tick = one([node for node in graph.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "ReceiveTick"])
    return ((cs, cs.Nodes[0], "then", "Construction", None, None),
        (graph, begin, "then", "Begin", "OtherActor", "OtherActor"),
        (graph, end, "then", "End", "OtherActor", "OtherActor"),
        (graph, tick, "then", "Tick", "DeltaSeconds", "DeltaSeconds"),
        (graph, timeline, "Update", "Update", "Value", "Lerp"),
        (graph, timeline, "Finished", "Finish", None, None))

def curves(bp):
    return [{"length": float(value.TimelineLength), "tracks": [{"name": str(track.TrackName),
        "samples": [float(track.CurveFloat.call_function("GetFloatValue", t)) for t in (0.0, .25, .5, .75, 1.0)]}
        for track in value.FloatTracks]} for value in bp.Timelines]

def text_transport(bp):
    graph = ue.blueprint_add_function(bp, TEXT)
    entry = graph.Nodes[0]
    target, value = graph.graph_add_node_variable_get("Text"), graph.graph_add_node_variable_get("TextToDisplay")
    call = graph.graph_add_node_call_function(ue.find_class("TextRenderComponent").K2_SetText)
    entry.node_find_pin("then").make_link_to(call.node_find_pin("execute"))
    target.node_find_pin("Text").make_link_to(call.node_find_pin("self"))
    value.node_find_pin("TextToDisplay").make_link_to(call.node_find_pin("Value"))
    if len(graph.Nodes) != 4:
        raise RuntimeError("native FText transport must contain exactly four nodes")

def generate():
    stage = require_authoring_stage(argument("UEPGrantGEStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = reference/"Plugins/GameFeatures/ShooterCore/Content/Blueprint/B_GrantAbilityPad_ApplyGE.uasset"
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, ASSET)
    class_name, curve_data = bp.GeneratedClass.get_name(), curves(bp)
    for graph, entry, output, suffix, parameter, source in hooks(bp):
        make_gate(bp, PREFIX+suffix, parameter, entry.node_find_pin(source) if source else None)
    text_transport(bp)
    ue.compile_blueprint(bp)
    groups = {}
    for graph, entry, output, suffix, parameter, source in hooks(bp):
        key = graph.get_name()
        if key not in groups:
            groups[key] = {"graph": graph, "names": {node.get_name() for node in graph.Nodes}, "ignored": set()}
        groups[key]["ignored"].add((entry.get_name(), output))
    for group in groups.values():
        group["before"] = semantics(group["graph"], group["names"], group["ignored"])
    for graph, entry, output, suffix, parameter, source in hooks(bp):
        insert_gate(graph, entry, output, getattr(bp.GeneratedClass, PREFIX+suffix), parameter, source)
    mixin_path = "/Game/UEPMixins/DA_GrantGEPadMixin"
    if ue.find_asset(mixin_path+".DA_GrantGEPadMixin") is not None:
        raise RuntimeError("fresh grant-GE authoring required")
    factory = DataAssetFactory()
    factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset("DA_GrantGEPadMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_world.grant_ge_pad_mixin",
        PythonClass="LyraGrantGE"+name+"Profile") for name in ("Python", "BlueprintFallback")]
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2 or bp.GeneratedClass.get_name() != class_name or bp.GeneratedClass.get_cdo().GetPythonMixinSet() != mixin:
        raise RuntimeError("grant-GE class/interface compile failed")
    proofs = []
    for key, group in groups.items():
        current = one([graph for graph in ue.blueprint_get_all_graphs(bp) if graph.get_name() == key])
        if semantics(current, group["names"], group["ignored"]) != group["before"]:
            raise RuntimeError("grant-GE original business graph changed: "+key)
        proofs.append({"graph": key, "original_semantic_digest": group["before"], "rewired_exec_outputs": sorted(group["ignored"])})
    if curves(bp) != curve_data:
        raise RuntimeError("native Timeline curve changed")
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(original.read_bytes()).hexdigest() != digest:
        raise RuntimeError("official grant-GE asset changed")
    return {"status": "passed", "runtime_acceptance": False, "class_preserved": True, "gate_count": 6,
        "original_blocks_retained": True, "original_graphs": proofs, "native_curve_preserved": True,
        "curve_data": curve_data, "ftext_transport_nodes": 4, "reference_hashes": {str(original): digest}}


result = argument("UEPGenerateGrantGEResult")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_GRANT_GE_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
