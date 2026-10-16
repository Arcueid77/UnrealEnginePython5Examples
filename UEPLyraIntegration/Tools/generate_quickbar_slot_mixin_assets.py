"""Example-owned quickbar configuration and typed native VM transports only."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_quickbar_slot_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass generator to Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import read_graph, broadcast_graph, connect

ASSET = "/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot"
HELPER = "/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages"
RESUME = "UEPResumeQuickBarSlotObservation"
PROXIES = {"Lyra.QuickBar.Message.SlotsChanged": "UEPOriginalSlotsProxy",
           "Lyra.QuickBar.Message.ActiveIndexChanged": "UEPOriginalActiveIndexProxy"}
OLD = {"ReadUI", "ReadVerb", "ReadDuration", "ReadFailure", "BroadcastUI", "BroadcastVerb", "BroadcastDuration",
       "BroadcastFailure", "CopyFailureText", "SameFailureText", "ReadQuickBarSlots", "BroadcastQuickBarSlots",
       "ReadQuickBarActiveIndex", "BroadcastQuickBarActiveIndex"}


def argument(name):
    return next((arg[len(name)+2:] for arg in sys.argv if arg.startswith("-"+name+"=")), None)


def path(value):
    return None if value is None else value.get_path_name()


def digest(graph):
    # Same pin/default/reference semantics as the accepted failure adapter gate.
    nodes = []
    for node in sorted(graph.Nodes, key=lambda value: value.get_name()):
        reference = None
        try:
            value = node.FunctionReference
            reference = [str(value.MemberName), path(value.MemberParent), bool(value.bSelfContext)]
        except Exception:
            pass  # Non-call nodes have no FunctionReference.
        pins = [{"name": pin.name, "direction": pin.direction, "category": pin.category,
                 "sub_category": pin.sub_category, "object_type": path(pin.sub_category_object),
                 "container": pin.container_type, "reference": pin.is_reference, "const": pin.is_const,
                 "default": pin.default_value, "text": str(pin.default_text_value), "object": path(pin.default_object),
                 "links": sorted((link.owning_node.get_name(), link.name) for link in pin.get_linked_to())}
                for pin in node.node_pins()]
        nodes.append({"name": node.get_name(), "class": node.get_class().get_name(), "function": reference, "pins": pins})
    return hashlib.sha256(json.dumps(nodes, sort_keys=True).encode()).hexdigest()


def extend_transport():
    bp = ue.load_object(Blueprint, HELPER)
    # A later batch may have extended the shared adapter. Preserve every
    # existing graph, not only the QuickBar-era subset of fourteen functions.
    before = {graph.get_name(): digest(graph) for graph in bp.FunctionGraphs}
    base = OLD-{"ReadQuickBarSlots", "BroadcastQuickBarSlots", "ReadQuickBarActiveIndex", "BroadcastQuickBarActiveIndex"}
    if not base.issubset(before):
        raise RuntimeError("accepted ten transport functions required")
    names = {graph.get_name() for graph in bp.FunctionGraphs}
    for suffix, struct_name in (("QuickBarSlots", "LyraQuickBarSlotsChangedMessage"),
                                ("QuickBarActiveIndex", "LyraQuickBarActiveIndexChangedMessage")):
        payload = ue.find_struct(struct_name)
        if "Read"+suffix not in names:
            read_graph(bp, suffix, payload, ue.find_class("AsyncAction_ListenForGameplayMessage"))
        if "Broadcast"+suffix not in names:
            broadcast_graph(bp, suffix, payload, ue.find_class("GameplayMessageSubsystem"))
    if "InjectAxis1DForAction" not in names:
        # FInputActionValue converts to Python primitives when read by UEP.
        # Keep its exact native Axis1D storage entirely inside the compiled VM.
        graph = ue.blueprint_add_function(bp, "InjectAxis1DForAction")
        entry = graph.Nodes[0]
        entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("EnhancedInputLocalPlayerSubsystem")), "Subsystem")
        entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("InputAction")), "Action")
        make = graph.graph_add_node_call_function(ue.find_class("EnhancedInputLibrary").MakeInputActionValueOfType)
        x = make.node_find_pin("X")
        entry.node_create_pin(1, EdGraphPinType(PinCategory=x.category, PinSubCategory=x.sub_category), "Value")
        inject = graph.graph_add_node_call_function(ue.find_class("EnhancedInputSubsystemInterface").InjectInputForAction)
        make.node_find_pin("ValueType").default_value = "Axis1D"
        connect(entry, "then", inject, "execute")
        connect(entry, "Subsystem", inject, "self")
        connect(entry, "Action", inject, "Action")
        connect(entry, "Value", make, "X")
        connect(make, "ReturnValue", inject, "RawValue")
    ue.compile_blueprint(bp)
    after = {graph.get_name(): digest(graph) for graph in bp.FunctionGraphs if graph.get_name() in before}
    if int(bp.Status) == 2 or before != after:
        raise RuntimeError("quickbar transport compile or prior semantic digest changed")
    bp.save_package()
    return bp.GeneratedClass, {"old_graphs_unchanged": True, "old_graph_digests": before,
                               "preserves_all_existing_functions": True,
                               "functions": [{"name": graph.get_name(), "nodes": len(graph.Nodes)} for graph in bp.FunctionGraphs],
                               "business_logic": False, "wildcard_calls_use_compiled_vm": True}


def configure_ownership(bp):
    variables = {str(variable.VarName) for variable in bp.NewVariables}
    missing = [name for name in PROXIES.values() if name not in variables]
    if missing and len(missing) != 2:
        raise RuntimeError("partially authored quickbar ownership; inspect before repairing")
    if missing:
        for name in missing:
            ue.blueprint_add_member_variable(bp, name, EdGraphPinType(PinCategory="object",
                                               PinSubCategoryObject=ue.find_class("AsyncAction_ListenForGameplayMessage")))
        ue.compile_blueprint(bp)
        graph = bp.UbergraphPages[0]
        actions = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_AsyncAction_ListenForGameplayMessages"]
        if len(actions) != 2:
            raise RuntimeError("quickbar original listener inventory differs")
        for action in actions:
            channel = action.node_find_pin("Channel").default_value
            matches = [name for tag, name in PROXIES.items() if tag in channel]
            if len(matches) != 1 or action.node_find_pin("then").get_linked_to():
                raise RuntimeError("quickbar original factory topology differs")
            name = matches[0]
            store = graph.graph_add_node_variable_set(name)
            connect(action, "then", store, "execute")
            connect(action, "AsyncTaskProxy", store, name)
        # Reuse the listener-only Sequence reached after OnInitialized's empty
        # update; never replay that initialization/model mutation on resume.
        upstream = [action.node_find_pin("execute").get_linked_to() for action in actions]
        if any(len(links) != 1 for links in upstream) or upstream[0][0].owning_node != upstream[1][0].owning_node:
            raise RuntimeError("quickbar listener Sequence differs")
        sequence = upstream[0][0].owning_node
        if sequence.get_class().get_name() != "K2Node_ExecutionSequence":
            raise RuntimeError("expected listener-only Sequence")
        event = graph.graph_add_node(K2Node_CustomEvent)
        event.CustomFunctionName = RESUME
        graph.graph_reconstruct_node(event)
        connect(event, "then", sequence, "execute")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2:
        raise RuntimeError("quickbar ownership declarations failed to compile")


def generate():
    stage = require_authoring_stage(argument("UEPQuickBarStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = source / "Plugins/GameFeatures/ShooterCore/Content/UserInterface/HUD/W_QuickBarSlot.uasset"
    original_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    adapter, transport = extend_transport()
    bp = ue.load_object(Blueprint, ASSET)
    ue.unregister_all_mixins()
    configure_ownership(bp)
    if "PythonMessageAdapterClass" not in {str(variable.VarName) for variable in bp.NewVariables}:
        ue.blueprint_add_member_variable(bp, "PythonMessageAdapterClass",
            EdGraphPinType(PinCategory="class", PinSubCategoryObject=ue.find_class("Object")))
        ue.compile_blueprint(bp)
    name = "DA_W_QuickBarSlotMixin"
    mixin = ue.find_asset("/Game/UEPMixins/"+name+"."+name)
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.quickbar_slot_mixin", PythonClass=cls)
                      for profile, cls in (("Python", "LyraQuickBarSlotPythonProfile"),
                                           ("BlueprintFallback", "LyraQuickBarSlotBlueprintFallbackProfile"))]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.unregister_all_mixins()
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    cdo.PythonMessageAdapterClass = adapter
    if (int(bp.Status) == 2 or cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python" or
            not cdo.bHasScriptImplementedTick or bp.GeneratedClass.get_name() != "W_QuickBarSlot_C"):
        raise RuntimeError("quickbar Interface/CDO/class/Tick postcondition differs")
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("official quickbar changed")
    return {"status": "passed", "class_preserved": True, "reference_sha256": original_hash,
            "original_proxy_stored": all(cdo.has_property(name) for name in PROXIES.values()),
            "explicit_resume": RESUME, "transport": transport, "cleanup_nodes": 0,
            "cleanup_business_logic": False, "original_widget_tick_retained": True, "runtime_acceptance": False}


result = argument("UEPGenerateQuickBarResult")
if result is None:
    raise RuntimeError("UEPGenerateQuickBarResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_QUICKBAR_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
