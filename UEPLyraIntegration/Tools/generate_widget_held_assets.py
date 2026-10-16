"""Configure retained held-widget root; leave both native children untouched."""
import hashlib
import json
from pathlib import Path
import sys

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_IfThenElse, K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile
from mixin_graph_gates import make_gate, insert_gate, semantics
from message_payload_graphs import connect

ROOT = "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhileInputHeld.GAB_ShowWidget_WhileInputHeld"
RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Input/Abilities/GAB_ShowWidget_WhileInputHeld.uasset"
END, GUARD = "UEPWidgetHeldNativeEnded", "UEPWidgetHeldTearingDown"
CLASS_PATH = "UEPWidgetHeldClassPath"


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-" + name + "="))


def full_cdo(bp, label):
    path = Path(arg("UEPHeroAbilityAssetsResult")).parent / ("widget-held-" + label + "-cdo.t3d")
    if not ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(bp.GeneratedClass.get_cdo(), str(path)):
        raise RuntimeError("native held-widget CDO export failed")
    data = path.read_bytes()
    text = data.decode("utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    allowed = ("PythonMixinProfile=", "PythonMixinSet=", GUARD + "=")
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(allowed))


def class_path_transport(bp):
    """Typed soft-path transport only; do not load or choose a Widget class."""
    graph = ue.blueprint_add_function(bp, CLASS_PATH)
    entry = graph.Nodes[0]
    result = graph.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="string"), "ReturnValue")
    get = graph.graph_add_node_variable_get("Widget Class")
    convert = graph.graph_add_node_call_function(
        ue.find_class("KismetSystemLibrary").Conv_SoftClassReferenceToString)
    connect(entry, "then", result, "execute")
    connect(get, "Widget Class", convert, "SoftClassReference")
    connect(convert, "ReturnValue", result, "ReturnValue")
    if len(graph.Nodes) != 4:
        raise RuntimeError("held-widget soft-class transport must have exactly four nodes")
    return graph


def generate(stage):
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    relatives = (RELATIVE, "Plugins/GameFeatures/ShooterCore/Content/ControlPoint/GA_ShowLeaderboard_CP.uasset",
                 "Plugins/GameFeatures/ShooterCore/Content/Elimination/GA_ShowLeaderboard_TDM.uasset")
    hashes = {}
    for relative in relatives:
        pair = {str(root / relative): hashlib.sha256((root / relative).read_bytes()).hexdigest() for root in (source, stage)}
        if len(set(pair.values())) != 1: raise RuntimeError("unchanged original held-widget family required")
        hashes.update(pair)
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, ROOT)
    ue.unregister_all_mixins()
    original_class = bp.GeneratedClass.get_path_name()
    methods = ("K2_ActivateAbility", "K2_OnEndAbility", "CreateAndDisplayWidget", "RemoveWidget")
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in methods}
    before = full_cdo(bp, "before")
    event = bp.UbergraphPages[0]
    ends = [node for node in event.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "K2_OnEndAbility"]
    if len(ends) != 1: raise RuntimeError("one original held-widget native End required")
    end = ends[0]
    ignored = {(end.get_name(), "then")}
    states = [node for node in event.Nodes if node.get_class().get_name() == "K2Node_LatentAbilityCall"
              and str(node.ProxyFactoryFunctionName) == "StartAbilityState"]
    if len(states) != 1:
        raise RuntimeError("one original held-widget native StartAbilityState required")
    state = states[0]
    ignored.update((state.get_name(), pin) for pin in ("OnStateEnded", "OnStateInterrupted"))
    graphs = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    digests = {graph.get_name(): semantics(graph, names, ignored) for graph, names in graphs}
    ue.blueprint_add_member_variable(bp, GUARD, EdGraphPinType(PinCategory="bool"))
    make_gate(bp, END, "bWasCancelled", end.node_find_pin("bWasCancelled"))
    transport = class_path_transport(bp)
    ue.compile_blueprint(bp)
    insert_gate(event, end, "then", getattr(bp.GeneratedClass, END), "bWasCancelled", "bWasCancelled")
    target = end.node_find_pin("then").get_linked_to()[0]
    end.node_find_pin("then").break_link_to(target)
    branch, get = event.graph_add_node(K2Node_IfThenElse), event.graph_add_node_variable_get(GUARD)
    connect(end, "then", branch, "execute"); connect(get, GUARD, branch, "Condition")
    branch.node_find_pin("else").make_link_to(target)
    # Original-BP state tasks also call the routed RemoveWidget. During an
    # explicit Profile teardown the router rejects reentry, so skip those two
    # dispatch endpoints only while GUARD is true. Native state teardown still
    # runs and the Python teardown has already removed its owned UI.
    for pin in ("OnStateEnded", "OnStateInterrupted"):
        source_pin = state.node_find_pin(pin)
        targets = source_pin.get_linked_to()
        if len(targets) != 1:
            raise RuntimeError("one retained held-widget state continuation required")
        source_pin.break_link_to(targets[0])
        check, get_guard = event.graph_add_node(K2Node_IfThenElse), event.graph_add_node_variable_get(GUARD)
        connect(state, pin, check, "execute"); connect(get_guard, GUARD, check, "Condition")
        check.node_find_pin("else").make_link_to(targets[0])
    name = "DA_WidgetHeldAbilityMixin"
    if ue.find_asset("/Game/UEPMixins/" + name + "." + name) is not None: raise RuntimeError("fresh held-widget Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities.widget_held_mixin", PythonClass=cls)
        for profile, cls in (("Python", "LyraWidgetHeldPythonProfile"), ("BlueprintFallback", "LyraWidgetHeldBlueprintFallbackProfile"))]
    ue.unregister_all_mixins(); ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or full_cdo(bp, "after") != before:
        raise RuntimeError("retained held-widget type/full CDO/compile differs")
    for name, description in signatures.items():
        if ue.describe_function(bp.GeneratedClass, name) != description: raise RuntimeError("held-widget public signature changed: " + name)
    for graph, names in graphs:
        if semantics(graph, names, ignored) != digests[graph.get_name()]: raise RuntimeError("original held-widget business changed")
    bp.save_package(); mixin.save_package()
    # Root is the sole authored class. Child assets are real native unchanged
    # inputs; their CDO widget/layer/policy remains inherited configuration.
    for file, digest in hashes.items():
        if file == str(stage / RELATIVE): continue
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest: raise RuntimeError("original held-widget family asset changed")
    return dict(status="passed", kind="widgetheld", runtime_acceptance=False, full_acceptance=False,
        original_class=original_class, original_class_defaults_signature_graphs_preserved=True,
        original_full_cdo_preserved=True, native_end_adapter_nodes=4, original_signatures=signatures,
        soft_class_path_transport_nodes=len(transport.Nodes),
        native_state_teardown_guard_nodes=4,
        soft_class_path_transport=ue.describe_function(bp.GeneratedClass, CLASS_PATH),
        original_graphs=digests, dispatch_transport_endpoints=sorted(ignored), native_children_unchanged=True,
        reference_hashes={file: digest for file, digest in hashes.items() if file != str(stage / RELATIVE)},
        assets=[RELATIVE, "Content/UEPMixins/DA_WidgetHeldAbilityMixin.uasset"])
