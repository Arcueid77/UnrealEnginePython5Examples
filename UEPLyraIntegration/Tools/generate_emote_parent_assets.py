"""Extend the existing ability-widget router without changing original business."""
import hashlib
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import (Blueprint, UEPPythonMixinSet, K2Node_IfThenElse,
    K2Node_FunctionResult, K2Node_RemoveDelegate, K2Node_CreateDelegate, K2Node_Self)
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_emote_parent_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import make_gate, insert_gate, semantics
from message_payload_graphs import connect

PARENT = "/Game/Characters/Heroes/Abilities/GA_AbilityWithWidget.GA_AbilityWithWidget"
CHILD = "/ShooterCore/Game/Emote/GA_Emote.GA_Emote"
ADS = "/ShooterCore/Input/Abilities/GA_ADS.GA_ADS"
SET = "/Game/UEPMixins/DA_AbilityWidgetMixin.DA_AbilityWidgetMixin"
ACTIVATE, MOVEMENT, END = "UEPEmoteActivateGate", "UEPEmoteMovementGate", "UEPEmoteNativeEndGate"
GUARD, REMOVE = "UEPEmoteTearingDown", "UEPRemoveOriginalEmoteBinding"
RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Game/Emote/GA_Emote.uasset"
OUTPUTS = ["Content/Characters/Heroes/Abilities/GA_AbilityWithWidget.uasset",
    "Content/UEPMixins/DA_AbilityWidgetMixin.uasset", RELATIVE,
    "Plugins/GameFeatures/ShooterCore/Content/Input/Abilities/GA_ADS.uasset"]


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-" + name + "="))


def one(values):
    if len(values) != 1:
        raise RuntimeError("exactly one original Emote entry required")
    return values[0]


def profiles(mixin):
    return [(str(row.ProfileName), str(row.PythonModule), str(row.PythonClass)) for row in mixin.Profiles]


def cdo_snapshot(bp, label, allowed=()):
    path = Path(arg("UEPEmoteAssetsResult")).parent / (label + "-cdo.t3d")
    if not ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(bp.GeneratedClass.get_cdo(), str(path)):
        raise RuntimeError("native full CDO export failed: " + label)
    data = path.read_bytes()
    text = data.decode("utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(allowed))


def multi_gate(bp, name, parameters):
    if any(graph.get_name() == name for graph in bp.FunctionGraphs):
        raise RuntimeError("fresh Emote gate required")
    graph = ue.blueprint_add_function(bp, name)
    entry = graph.Nodes[0]
    for field, kind in parameters:
        entry.node_create_pin(1, kind, field)
    result = graph.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "ReturnValue")
    result.node_find_pin("ReturnValue").default_value = "true"
    connect(entry, "then", result, "execute")


def remove_original_binding(bp, original):
    # Only native dynamic-delegate plumbing. Never ClearAll a foreign listener.
    graph = ue.blueprint_add_function(bp, REMOVE)
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("Character")), "Character")
    remove = graph.graph_add_node(K2Node_RemoveDelegate)
    remove.DelegateReference = original.DelegateReference
    graph.graph_reconstruct_node(remove)
    delegate, owner = graph.graph_add_node(K2Node_CreateDelegate), graph.graph_add_node(K2Node_Self)
    connect(entry, "then", remove, "execute")
    connect(entry, "Character", remove, "self")
    connect(owner, "self", delegate, "self")
    connect(delegate, "OutputDelegate", remove, "Delegate")
    delegate.SelectedFunctionName = "CheckForMovement"
    return graph


def generate():
    stage = require_authoring_stage(arg("UEPEmoteStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes = {str(source / relative): hashlib.sha256((source / relative).read_bytes()).hexdigest() for relative in (RELATIVE, OUTPUTS[0], OUTPUTS[3])}
    if hashlib.sha256((stage / RELATIVE).read_bytes()).hexdigest() != hashes[str(source / RELATIVE)]:
        raise RuntimeError("unchanged original Emote required before authoring")
    ue.unregister_all_mixins()
    parent, child, ads = [ue.load_object(Blueprint, path) for path in (PARENT, CHILD, ADS)]
    mixin = ue.load_object(UEPPythonMixinSet, SET)
    ue.unregister_all_mixins()
    old_profiles, default_profile = profiles(mixin), str(mixin.DefaultProfile)
    if not {"ADSPython", "ADSBlueprintFallback"}.issubset({row[0] for row in old_profiles}):
        raise RuntimeError("accepted ADS shared-parent family required")
    if {"EmotePython", "EmoteBlueprintFallback"}.intersection(row[0] for row in old_profiles):
        raise RuntimeError("fresh Emote family extension required")
    event = child.UbergraphPages[0]
    activate = one([node for node in event.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "K2_ActivateAbility"])
    movement = one([node for node in event.Nodes if node.get_class().get_name() == "K2Node_CustomEvent" and str(node.CustomFunctionName) == "CheckForMovement"])
    add = one([node for node in event.Nodes if node.get_class().get_name() == "K2Node_AddDelegate"])
    ignored = {(node.get_name(), "then") for node in (activate, movement)}
    snapshots = {label: [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
                 for label, bp in (("parent", parent), ("emote", child), ("ads", ads))}
    graph_proof = {label: {graph.get_name(): semantics(graph, names, ignored if label == "emote" else set()) for graph, names in rows}
                   for label, rows in snapshots.items()}
    allowed = ("PythonMixinProfile=", "PythonMixinSet=", GUARD + "=")
    before = {label: cdo_snapshot(bp, label + "-before", allowed if label == "emote" else ())
              for label, bp in (("parent", parent), ("emote", child), ("ads", ads))}
    signatures = {name: ue.describe_function(child.GeneratedClass, name) for name in ("K2_ActivateAbility", "CheckForMovement", "K2_OnAbilityAdded", "K2_OnAbilityRemoved")}
    make_gate(parent, ACTIVATE, None)
    parameters = []
    for field in ("DeltaSeconds", "OldLocation", "OldVelocity"):
        pin = movement.node_find_pin(field)
        parameters.append((field, EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category,
                                                PinSubCategoryObject=pin.sub_category_object)))
    multi_gate(parent, MOVEMENT, parameters)
    multi_gate(parent, END, [("bWasCancelled", EdGraphPinType(PinCategory="bool"))])
    ue.compile_blueprint(parent)
    ue.blueprint_add_member_variable(child, GUARD, EdGraphPinType(PinCategory="bool"))
    helper = remove_original_binding(child, add)
    ue.compile_blueprint(child)
    insert_gate(event, activate, "then", getattr(parent.GeneratedClass, ACTIVATE))
    target = one(movement.node_find_pin("then").get_linked_to())
    movement.node_find_pin("then").break_link_to(target)
    call, branch = event.graph_add_node_call_function(getattr(parent.GeneratedClass, MOVEMENT)), event.graph_add_node(K2Node_IfThenElse)
    connect(movement, "then", call, "execute"); connect(call, "then", branch, "execute")
    connect(call, "ReturnValue", branch, "Condition"); branch.node_find_pin("then").make_link_to(target)
    for field, kind in parameters:
        connect(movement, field, call, field)
    end = event.graph_add_node_event(ue.find_class("GameplayAbility"), "K2_OnEndAbility")
    end.set_property("bOverrideFunction", True)
    guard, get = event.graph_add_node(K2Node_IfThenElse), event.graph_add_node_variable_get(GUARD)
    notify = event.graph_add_node_call_function(getattr(parent.GeneratedClass, END))
    connect(end, "then", guard, "execute"); connect(get, GUARD, guard, "Condition")
    connect(guard, "else", notify, "execute"); connect(end, "bWasCancelled", notify, "bWasCancelled")
    mixin.Profiles = list(mixin.Profiles) + [UEPPythonMixinProfile(ProfileName=name,
        PythonModule="uep_lyra_abilities.emote_mixin", PythonClass=cls) for name, cls in (
        ("EmotePython", "LyraEmotePythonProfile"), ("EmoteBlueprintFallback", "LyraEmoteBlueprintFallbackProfile"))]
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(child, mixin, "EmotePython", "PythonMixinProfile")
    ue.compile_blueprint(child)
    ue.unregister_all_mixins()
    if any(int(bp.Status) == 2 for bp in (parent, child, ads)):
        raise RuntimeError("Emote shared-parent Blueprint compilation failed")
    for label, bp in (("parent", parent), ("emote", child), ("ads", ads)):
        if cdo_snapshot(bp, label + "-after", allowed if label == "emote" else ()) != before[label]:
            raise RuntimeError("original full CDO changed: " + label)
    for label, rows in snapshots.items():
        for graph, names in rows:
            if semantics(graph, names, ignored if label == "emote" else set()) != graph_proof[label][graph.get_name()]:
                raise RuntimeError("original family business graph changed: " + label + "/" + graph.get_name())
    for name, description in signatures.items():
        if ue.describe_function(child.GeneratedClass, name) != description:
            raise RuntimeError("original Emote public signature changed: " + name)
    if profiles(mixin)[:len(old_profiles)] != old_profiles or str(mixin.DefaultProfile) != default_profile:
        raise RuntimeError("existing ability-widget profiles/default changed")
    if len(helper.Nodes) != 4 or child.GeneratedClass.get_path_name() != CHILD + "_C":
        raise RuntimeError("retained class/native delegate transport differs")
    if child.GeneratedClass.get_cdo().GetPythonMixinSet() != mixin or str(child.GeneratedClass.get_cdo().GetPythonMixinProfile()) != "EmotePython":
        raise RuntimeError("Emote CDO selector differs")
    parent.save_package(); child.save_package(); mixin.save_package()
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("official family asset changed")
    return dict(status="passed", kind="emoteparent", runtime_acceptance=False, full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True, single_parent_router=True,
        original_full_cdo_preserved=True, existing_ads_profiles_defaults_graphs_preserved=True,
        existing_profiles_preserved=old_profiles, original_signatures=signatures, original_graphs=graph_proof,
        dispatch_transport_endpoints=sorted(ignored), native_end_adapter_nodes=4, precise_delegate_remove_nodes=4,
        new_profiles=["EmotePython", "EmoteBlueprintFallback"], reference_hashes=hashes, assets=OUTPUTS)


try:
    report = generate()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
    ue.log_error(report["error"])
Path(arg("UEPEmoteAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["status"] != "passed":
    raise RuntimeError(report["error"])
ue.log("UEP_EMOTE_PARENT_ASSETS_PASSED")
