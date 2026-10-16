"""Author the example-owned failure UI and native FText transport primitives."""

import hashlib
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import (Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_BreakStruct,
                                  K2Node_FunctionResult, K2Node_CustomEvent, K2Node_CreateDelegate, K2Node_Self)
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_ability_failure_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass the generator to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import read_graph, broadcast_graph, connect

HELPER = "/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages"
RESUME = "UEPResumeFailureObservation"
PROXY = "UEPOriginalFailureProxy"
CLEANUP = "UEPRemoveOriginalFailureBindings"
TICK_DELTA = "UEPWidgetTickDelta"
DELAY_COMPLETE = "UEPFailureDelayComplete"


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


def path(value):
    return None if value is None else value.get_path_name()


def digest(graph):
    nodes = []
    for node in sorted(graph.Nodes, key=lambda node: node.get_name()):
        reference = None
        try:
            value = node.FunctionReference
            reference = [str(value.MemberName), path(value.MemberParent), bool(value.bSelfContext)]
        except Exception:
            pass
        pins = [{"name": pin.name, "direction": pin.direction, "category": pin.category,
                 "sub_category": pin.sub_category, "object_type": path(pin.sub_category_object),
                 "container": pin.container_type, "reference": pin.is_reference, "const": pin.is_const,
                 "default": pin.default_value, "text": str(pin.default_text_value), "object": path(pin.default_object),
                 "links": sorted((link.owning_node.get_name(), link.name) for link in pin.get_linked_to())}
                for pin in node.node_pins()]
        nodes.append({"name": node.get_name(), "class": node.get_class().get_name(), "function": reference, "pins": pins})
    return hashlib.sha256(json.dumps(nodes, sort_keys=True).encode()).hexdigest()


def text_graph(bp, name, payload, compare=False):
    graph = ue.blueprint_add_function(bp, name)
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("TextBlock")), "TextWidget")
    entry.node_create_pin(1, EdGraphPinType(PinCategory="struct", PinSubCategoryObject=payload), "Payload")
    split = graph.graph_add_node(K2Node_BreakStruct)
    split.StructType = payload
    graph.graph_reconstruct_node(split)
    inputs = [pin for pin in split.node_pins() if pin.direction == 0 and pin.category == "struct"]
    if len(inputs) != 1:
        raise RuntimeError("typed failure break-struct input differs")
    entry.node_find_pin("Payload").connect(inputs[0])
    if compare:
        getter = graph.graph_add_node_call_function(ue.find_class("TextBlock").GetText)
        equals = graph.graph_add_node_call_function(ue.find_class("KismetTextLibrary").EqualEqual_TextText)
        result = graph.graph_add_node(K2Node_FunctionResult)
        result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "Same")
        connect(entry, "then", result, "execute")
        connect(entry, "TextWidget", getter, "self")
        connect(getter, "ReturnValue", equals, "A")
        connect(split, "UserFacingReason", equals, "B")
        connect(equals, "ReturnValue", result, "Same")
    else:
        setter = graph.graph_add_node_call_function(ue.find_class("TextBlock").SetText)
        connect(entry, "then", setter, "execute")
        connect(entry, "TextWidget", setter, "self")
        connect(split, "UserFacingReason", setter, "InText")
    return graph


def extend_transport():
    bp = ue.load_object(Blueprint, HELPER)
    old = {"ReadUI", "ReadVerb", "ReadDuration", "BroadcastUI", "BroadcastVerb", "BroadcastDuration"}
    before = {graph.get_name(): digest(graph) for graph in bp.FunctionGraphs if graph.get_name() in old}
    if set(before) != old:
        raise RuntimeError("existing six typed transport graphs differ")
    names = {graph.get_name() for graph in bp.FunctionGraphs}
    payload = ue.find_struct("LyraAbilitySimpleFailureMessage")
    if "ReadFailure" not in names:
        read_graph(bp, "Failure", payload, ue.find_class("AsyncAction_ListenForGameplayMessage"))
    if "BroadcastFailure" not in names:
        broadcast_graph(bp, "Failure", payload, ue.find_class("GameplayMessageSubsystem"))
    if "CopyFailureText" not in names:
        text_graph(bp, "CopyFailureText", payload)
    if "SameFailureText" not in names:
        text_graph(bp, "SameFailureText", payload, True)
    ue.compile_blueprint(bp)
    after = {graph.get_name(): digest(graph) for graph in bp.FunctionGraphs if graph.get_name() in old}
    if int(bp.Status) == 2 or before != after:
        raise RuntimeError("failure transport compilation or prior graph semantic digest differs")
    bp.save_package()
    return bp.GeneratedClass, {"old_graphs_unchanged": True, "old_graph_digests": before,
                               "functions": [{"name": graph.get_name(), "nodes": len(graph.Nodes)} for graph in bp.FunctionGraphs],
                               "text_primitives_have_no_branch_or_string_conversion": True}


def configure_original_ownership(bp):
    variables = {str(variable.VarName) for variable in bp.NewVariables}
    if PROXY not in variables:
        ue.blueprint_add_member_variable(bp, PROXY, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("AsyncAction_ListenForGameplayMessage")))
        ue.compile_blueprint(bp)
        graph = bp.UbergraphPages[0]
        actions = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_AsyncAction_ListenForGameplayMessages"]
        if len(actions) != 1 or actions[0].node_find_pin("then").get_linked_to():
            raise RuntimeError("failure async factory topology differs")
        action = actions[0]
        store = graph.graph_add_node_variable_set(PROXY)
        connect(action, "then", store, "execute")
        connect(action, "AsyncTaskProxy", store, PROXY)
        event = graph.graph_add_node(K2Node_CustomEvent)
        event.CustomFunctionName = RESUME
        graph.graph_reconstruct_node(event)
        connect(event, "then", action, "execute")  # Listener entry only, no OnInitialized replay.
    if CLEANUP not in {graph.get_name() for graph in bp.FunctionGraphs}:
        graph = ue.blueprint_add_function(bp, CLEANUP)
        entry = graph.Nodes[0]
        owner = graph.graph_add_node(K2Node_Self)
        animation = graph.graph_add_node_variable_get("Outro")
        previous, previous_pin = entry, "then"
        for name in ("OutroCompleted", "OutroCurrentCompleted"):
            call = graph.graph_add_node_call_function(ue.find_class("UserWidget").UnbindFromAnimationFinished)
            delegate = graph.graph_add_node(K2Node_CreateDelegate)
            connect(previous, previous_pin, call, "execute")
            connect(owner, "self", call, "self")
            connect(owner, "self", delegate, "self")
            connect(animation, "Outro", call, "Animation")
            connect(delegate, "OutputDelegate", call, "Delegate")
            delegate.SelectedFunctionName = name  # Select after inferred object/signature.
            previous, previous_pin = call, "then"


def declare_native_completion(bp):
    # Remove only the experiment's transport Tick, not an original business
    # event. Native latent scheduling owns the correct world/UMG frame policy.
    for graph in bp.UbergraphPages:
        for node in list(graph.Nodes):
            if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "Tick":
                links = list(node.node_find_pin("then").get_linked_to())
                if len(links) != 1 or links[0].owning_node.get_class().get_name() != "K2Node_VariableSet" or str(links[0].owning_node.VariableReference.MemberName) != TICK_DELTA:
                    raise RuntimeError("refuse to remove an unknown Tick body")
                graph.graph_remove_node(links[0].owning_node)
                graph.graph_remove_node(node)
    if DELAY_COMPLETE not in {graph.get_name() for graph in bp.FunctionGraphs}:
        graph = ue.blueprint_add_function(bp, DELAY_COMPLETE)
        graph.Nodes[0].node_create_pin(1, EdGraphPinType(PinCategory="int"), "Linkage")


def generate():
    stage = require_authoring_stage(argument("UEPAbilityFailureStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = source / "Plugins/GameFeatures/ShooterCore/Content/UserInterface/HUD/W_AbilityFailureFeedback.uasset"
    reference_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    adapter, transport = extend_transport()
    bp = ue.load_object(Blueprint, "/ShooterCore/UserInterface/HUD/W_AbilityFailureFeedback.W_AbilityFailureFeedback")
    # Loading an already configured package may auto-register its runtime
    # router. Restore script flags before the Widget compiler inspects Tick.
    ue.unregister_all_mixins()
    configure_original_ownership(bp)
    declare_native_completion(bp)
    if "PythonMessageAdapterClass" not in {str(variable.VarName) for variable in bp.NewVariables}:
        ue.blueprint_add_member_variable(bp, "PythonMessageAdapterClass", EdGraphPinType(PinCategory="class", PinSubCategoryObject=ue.find_class("Object")))
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2:
        raise RuntimeError("failure ownership/cleanup helpers did not compile")
    name = "DA_W_AbilityFailureFeedbackMixin"
    mixin = ue.find_asset("/Game/UEPMixins/" + name + "." + name)
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.ability_failure_mixin", PythonClass=cls)
                      for profile, cls in (("Python", "LyraAbilityFailurePythonProfile"), ("BlueprintFallback", "LyraAbilityFailureBlueprintFallbackProfile"))]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.unregister_all_mixins()
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    cdo.PythonMessageAdapterClass = adapter
    if int(bp.Status) == 2 or cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python" or cdo.bHasScriptImplementedTick:
        raise RuntimeError("failure Interface/CDO postcondition differs: " + repr({
            "compile_status": int(bp.Status), "mixin": path(cdo.GetPythonMixinSet()),
            "profile": str(cdo.GetPythonMixinProfile()), "script_tick": bool(cdo.bHasScriptImplementedTick)}))
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != reference_hash:
        raise RuntimeError("official failure UI changed")
    return {"status": "passed", "class_preserved": bp.GeneratedClass.get_name() == "W_AbilityFailureFeedback_C",
            "reference_sha256": reference_hash, "transport": transport,
            "cleanup_helpers": [{"name": graph.get_name(), "nodes": len(graph.Nodes)} for graph in bp.FunctionGraphs if graph.get_name() == CLEANUP],
            "original_proxy_stored": True, "explicit_listener_entry": RESUME,
            "native_widget_tick_declared": bool(cdo.bHasScriptImplementedTick), "tick_declaration_nodes": 0,
            "native_latent_completion_declared": True,
            "native_latent_signature": ue.describe_function(bp.GeneratedClass, DELAY_COMPLETE),
            "runtime_acceptance": False}


result = argument("UEPGenerateAbilityFailureResult")
if result is None:
    raise RuntimeError("UEPGenerateAbilityFailureResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_ABILITY_FAILURE_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
