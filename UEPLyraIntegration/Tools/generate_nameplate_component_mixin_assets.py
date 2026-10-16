"""Nameplate component Interface/CDO and typed message plumbing, in a marked copy."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_CustomEvent, K2Node_ExecutionSequence
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_nameplate_component_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass generator to Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import read_graph, broadcast_graph, connect
from blueprint_graph_digest import digest

ADAPTER = "/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages"
OLD = {"ReadUI", "ReadVerb", "ReadDuration", "ReadFailure", "BroadcastUI", "BroadcastVerb", "BroadcastDuration",
       "BroadcastFailure", "CopyFailureText", "SameFailureText", "ReadQuickBarSlots", "BroadcastQuickBarSlots",
       "ReadQuickBarActiveIndex", "BroadcastQuickBarActiveIndex", "InjectAxis1DForAction"}
ROWS = (("NameplateSource", "uep_lyra_hud.nameplate_source_mixin", "LyraNameplateSource", "UEPResumeNameplateDiscovery"),
        ("NameplateManagerComponent", "uep_lyra_hud.nameplate_manager_mixin", "LyraNameplateManager", "UEPResumeNameplateManagerObservation"))


def argument(name):
    return next((arg[len(name)+2:] for arg in sys.argv if arg.startswith("-"+name+"=")), None)


def transport():
    bp = ue.load_object(Blueprint, ADAPTER)
    before = {graph.get_name(): digest(graph) for graph in bp.FunctionGraphs if graph.get_name() in OLD}
    if set(before) != OLD:
        raise RuntimeError("accepted fifteen transport functions required")
    names = {graph.get_name() for graph in bp.FunctionGraphs}
    for suffix, name in (("NameplateInfo", "Message_NameplateInfo"), ("NameplateRequest", "Message_NameplateRequest")):
        payload = ue.load_object(ue.find_class("UserDefinedStruct"), "/Game/UI/Indicators/"+name+"."+name)
        if "Read"+suffix not in names:
            read_graph(bp, suffix, payload, ue.find_class("AsyncAction_ListenForGameplayMessage"))
        if "Broadcast"+suffix not in names:
            broadcast_graph(bp, suffix, payload, ue.find_class("GameplayMessageSubsystem"))
    ue.compile_blueprint(bp)
    after = {graph.get_name(): digest(graph) for graph in bp.FunctionGraphs if graph.get_name() in OLD}
    if int(bp.Status) == 2 or after != before:
        raise RuntimeError("nameplate transport compile/prior semantic digest differs")
    bp.save_package()
    return bp.GeneratedClass, {"old_graphs_unchanged": True, "old_graph_digests": before,
        "functions": [{"name": graph.get_name(), "nodes": len(graph.Nodes)} for graph in bp.FunctionGraphs],
        "business_logic": False, "wildcard_calls_use_compiled_vm": True}


def ownership(bp, source, resume):
    fields = {str(variable.VarName) for variable in bp.NewVariables}
    if source and "UEPOriginalNameplateDiscoverProxy" not in fields:
        ue.blueprint_add_member_variable(bp, "UEPOriginalNameplateDiscoverProxy", EdGraphPinType(
            PinCategory="object", PinSubCategoryObject=ue.find_class("AsyncAction_ListenForGameplayMessage")))
        ue.compile_blueprint(bp)
        graph = bp.UbergraphPages[0]
        actions = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_AsyncAction_ListenForGameplayMessages"]
        if len(actions) != 1 or actions[0].node_find_pin("then").get_linked_to():
            raise RuntimeError("original nameplate source listener topology differs")
        setter = graph.graph_add_node_variable_set("UEPOriginalNameplateDiscoverProxy")
        connect(actions[0], "then", setter, "execute")
        connect(actions[0], "AsyncTaskProxy", setter, "UEPOriginalNameplateDiscoverProxy")
    existing = [node for graph in bp.UbergraphPages for node in graph.Nodes if node.get_class().get_name() == "K2Node_CustomEvent" and str(node.CustomFunctionName) == resume]
    if len(existing) > 1:
        raise RuntimeError("duplicate nameplate resume declaration")
    if existing:
        return
    graph = bp.UbergraphPages[0]
    actions = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_AsyncAction_ListenForGameplayMessages"]
    if len(actions) != (1 if source else 2):
        raise RuntimeError("nameplate original listener count differs")
    event = graph.graph_add_node(K2Node_CustomEvent)
    event.CustomFunctionName = resume
    graph.graph_reconstruct_node(event)
    if source:
        connect(event, "then", actions[0], "execute")
    else:
        # Listener-only resume: do not reconnect the original Ready Sequence's
        # third (Discover broadcast) branch or replay native BeginPlay.
        sequence = graph.graph_add_node(K2Node_ExecutionSequence)
        connect(event, "then", sequence, "execute")
        actions.sort(key=lambda action: action.node_find_pin("Channel").default_value)
        for index, action in enumerate(actions):
            connect(sequence, "then_"+str(index), action, "execute")


def generate():
    stage = require_authoring_stage(argument("UEPNameplateComponentsStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    references = {name: source/("Content/UI/Indicators/"+name+".uasset") for name, module, cls, resume in ROWS}
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in references.items()}
    ue.unregister_all_mixins()
    adapter, transport_report = transport()
    reports = []
    for name, module, cls, resume in ROWS:
        bp = ue.load_object(Blueprint, "/Game/UI/Indicators/"+name+"."+name)
        ue.unregister_all_mixins()
        ownership(bp, name == "NameplateSource", resume)
        if "PythonMessageAdapterClass" not in {str(variable.VarName) for variable in bp.NewVariables}:
            ue.blueprint_add_member_variable(bp, "PythonMessageAdapterClass", EdGraphPinType(
                PinCategory="class", PinSubCategoryObject=ue.find_class("Object")))
        ue.compile_blueprint(bp)
        asset_name = "DA_"+name+"Mixin"
        mixin = ue.find_asset("/Game/UEPMixins/"+asset_name+"."+asset_name)
        if mixin is None:
            factory = DataAssetFactory()
            factory.DataAssetClass = UEPPythonMixinSet
            mixin = ue.create_asset(asset_name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
        mixin.DefaultProfile = "Python"
        mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule=module, PythonClass=cls+suffix)
                          for profile, suffix in (("Python", "PythonProfile"), ("BlueprintFallback", "BlueprintFallbackProfile"))]
        ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
        ue.unregister_all_mixins()
        ue.compile_blueprint(bp)
        cdo = bp.GeneratedClass.get_cdo()
        cdo.PythonMessageAdapterClass = adapter
        if int(bp.Status) == 2 or cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
            raise RuntimeError("nameplate component Interface/CDO postcondition differs")
        if bp.GeneratedClass.get_name() != name+"_C":
            raise RuntimeError("nameplate component class identity changed")
        bp.save_package()
        mixin.save_package()
        reports.append({"asset": name, "class_preserved": True, "reference_sha256": hashes[name], "resume": resume})
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != hashes[name] for name, path in references.items()):
        raise RuntimeError("official nameplate component changed")
    return {"status": "passed", "components": reports, "transport": transport_report,
            "ownership_only": True, "runtime_acceptance": False}


result = argument("UEPGenerateNameplateComponentsResult")
if result is None:
    raise RuntimeError("UEPGenerateNameplateComponentsResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_NAMEPLATE_COMPONENTS_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
