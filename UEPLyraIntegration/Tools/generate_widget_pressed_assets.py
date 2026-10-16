"""Retained pressed-widget root and typed lifetime transport; no child edits."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import (Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_IfThenElse,
    K2Node_FunctionResult, K2Node_RemoveDelegate, K2Node_CreateDelegate, K2Node_Self)
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile
from mixin_graph_gates import semantics
from message_payload_graphs import connect

ROOT = "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhenInputPressed.GAB_ShowWidget_WhenInputPressed"
RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Input/Abilities/GAB_ShowWidget_WhenInputPressed.uasset"
CLASS_PATH, END = "UEPWidgetPressedClassPath", "UEPWidgetPressedNativeEnded"
GUARD, PENDING, WIDGET = "UEPWidgetPressedTearingDown", "UEPWidgetPressedPending", "UEPWidgetPressedWidget"
REMOVE = "UEPRemoveOriginalPressedWidgetBinding"


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-" + name + "="))


def full_cdo(bp, label):
    path = Path(arg("UEPHeroAbilityAssetsResult")).parent / ("widget-pressed-" + label + "-cdo.t3d")
    if not ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(bp.GeneratedClass.get_cdo(), str(path)):
        raise RuntimeError("native pressed-widget CDO export failed")
    data = path.read_bytes()
    text = data.decode("utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    allowed = ("PythonMixinProfile=", "PythonMixinSet=", GUARD + "=", PENDING + "=", WIDGET + "=")
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(allowed))


def transports(bp, original_bind):
    graph = ue.blueprint_add_function(bp, CLASS_PATH)
    entry, result = graph.Nodes[0], graph.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="string"), "ReturnValue")
    get = graph.graph_add_node_variable_get("WidgetToSpawn")
    convert = graph.graph_add_node_call_function(ue.find_class("KismetSystemLibrary").Conv_SoftClassReferenceToString)
    connect(entry, "then", result, "execute"); connect(get, "WidgetToSpawn", convert, "SoftClassReference")
    connect(convert, "ReturnValue", result, "ReturnValue")
    cleanup = ue.blueprint_add_function(bp, REMOVE)
    entry = cleanup.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("CommonActivatableWidget")), "Widget")
    remove = cleanup.graph_add_node(K2Node_RemoveDelegate)
    remove.DelegateReference = original_bind.DelegateReference
    cleanup.graph_reconstruct_node(remove)
    delegate, owner = cleanup.graph_add_node(K2Node_CreateDelegate), cleanup.graph_add_node(K2Node_Self)
    connect(entry, "then", remove, "execute"); connect(entry, "Widget", remove, "self")
    connect(owner, "self", delegate, "self"); connect(delegate, "OutputDelegate", remove, "Delegate")
    delegate.SelectedFunctionName = "OnWidgetDeactivated"
    if len(graph.Nodes) != 4 or len(cleanup.Nodes) != 4:
        raise RuntimeError("pressed-widget typed transports must have four nodes each")


def generate(stage):
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    relatives = (RELATIVE, "Plugins/GameFeatures/ShooterExplorer/Content/Input/Abilities/GA_ToggleInventory.uasset",
                 "Plugins/GameFeatures/ShooterExplorer/Content/Input/Abilities/GA_ToggleMap.uasset")
    hashes = {}
    for relative in relatives:
        pair = {str(root / relative): hashlib.sha256((root / relative).read_bytes()).hexdigest() for root in (source, stage)}
        if len(set(pair.values())) != 1: raise RuntimeError("unchanged original pressed-widget family required")
        hashes.update(pair)
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, ROOT); ue.unregister_all_mixins()
    original_class, before = bp.GeneratedClass.get_path_name(), full_cdo(bp, "before")
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in
                  ("K2_ActivateAbility", "K2_OnEndAbility", "OnWidgetDeactivated")}
    event = bp.UbergraphPages[0]
    def one(values):
        if len(values) != 1: raise RuntimeError("one original pressed-widget endpoint required")
        return values[0]
    end = one([node for node in event.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "K2_OnEndAbility"])
    push = one([node for node in event.Nodes if node.get_class().get_name() == "K2Node_AsyncAction"])
    binding = one([node for node in event.Nodes if node.get_class().get_name() == "K2Node_AddDelegate"])
    ignored = {(end.get_name(), "then"), (push.get_name(), "AfterPush"), (push.get_name(), "then")}
    if end.node_find_pin("then").get_linked_to() or push.node_find_pin("then").get_linked_to():
        raise RuntimeError("original pressed-widget End/async then should be empty")
    graphs = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    digests = {graph.get_name(): semantics(graph, names, ignored) for graph, names in graphs}
    ue.blueprint_add_member_variable(bp, GUARD, EdGraphPinType(PinCategory="bool"))
    for name, cls in ((PENDING, "AsyncAction_PushContentToLayerForPlayer"), (WIDGET, "CommonActivatableWidget")):
        ue.blueprint_add_member_variable(bp, name, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class(cls)))
    notify = ue.blueprint_add_function(bp, END)
    notify.Nodes[0].node_create_pin(1, EdGraphPinType(PinCategory="bool"), "bWasCancelled")
    transports(bp, binding); ue.compile_blueprint(bp)
    check, get_guard = event.graph_add_node(K2Node_IfThenElse), event.graph_add_node_variable_get(GUARD)
    call = event.graph_add_node_call_function(getattr(bp.GeneratedClass, END))
    connect(end, "then", check, "execute"); connect(get_guard, GUARD, check, "Condition")
    connect(check, "else", call, "execute"); connect(end, "bWasCancelled", call, "bWasCancelled")
    target = one(push.node_find_pin("AfterPush").get_linked_to())
    push.node_find_pin("AfterPush").break_link_to(target)
    store, clear = event.graph_add_node_variable_set(WIDGET), event.graph_add_node_variable_set(PENDING)
    connect(push, "AfterPush", store, "execute"); connect(push, "UserWidget", store, WIDGET)
    connect(store, "then", clear, "execute"); clear.node_find_pin("then").make_link_to(target)
    pending = event.graph_add_node_variable_set(PENDING)
    connect(push, "then", pending, "execute"); connect(push, "AsyncTaskProxy", pending, PENDING)
    name = "DA_WidgetPressedAbilityMixin"
    if ue.find_asset("/Game/UEPMixins/" + name + "." + name) is not None: raise RuntimeError("fresh pressed-widget Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities.widget_pressed_mixin", PythonClass=cls)
        for profile, cls in (("Python", "LyraWidgetPressedPythonProfile"), ("BlueprintFallback", "LyraWidgetPressedBlueprintFallbackProfile"))]
    ue.unregister_all_mixins(); ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or full_cdo(bp, "after") != before:
        raise RuntimeError("retained pressed-widget type/full CDO/compile differs")
    for name, description in signatures.items():
        if ue.describe_function(bp.GeneratedClass, name) != description: raise RuntimeError("pressed-widget original signature changed")
    for graph, names in graphs:
        if semantics(graph, names, ignored) != digests[graph.get_name()]: raise RuntimeError("original pressed-widget business changed")
    bp.save_package(); mixin.save_package()
    for path, digest in hashes.items():
        if path != str(stage / RELATIVE) and hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise RuntimeError("original pressed-widget family changed")
    return dict(status="passed", kind="widgetpressed", runtime_acceptance=False, full_acceptance=False,
        original_class=original_class, original_class_defaults_signature_graphs_preserved=True, original_full_cdo_preserved=True,
        native_end_adapter_nodes=3, soft_class_path_transport_nodes=4, original_delegate_cleanup_nodes=4,
        original_pending_widget_capture_nodes=3, native_children_unchanged=True, original_signatures=signatures,
        original_graphs=digests, dispatch_transport_endpoints=sorted(ignored),
        reference_hashes={path: digest for path, digest in hashes.items() if path != str(stage / RELATIVE)},
        assets=[RELATIVE, "Content/UEPMixins/DA_WidgetPressedAbilityMixin.uasset"])
