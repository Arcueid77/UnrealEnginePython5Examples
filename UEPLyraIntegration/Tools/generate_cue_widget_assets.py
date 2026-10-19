"""Base-owned widget gates preserve native Cue parent calls and child bytes."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics, insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.cue_widget_mixin import CLASS, START, REMOVE

RELATIVE = "Content/GameplayCueNotifies/GCNL_Widget_Base.uasset"
SET = "Content/UEPMixins/DA_CueWidgetMixin.uasset"
PROBE = "Content/UEPValidation/BP_CueWidgetCaller.uasset"
FIXTURE = "Content/UEPValidation/BP_CueWidgetBaseFixture.uasset"
CHILDREN = {
    "match":("/ShooterCore/GameplayCues/GCNL_MatchDecided.GCNL_MatchDecided", "Plugins/GameFeatures/ShooterCore/Content/GameplayCues/GCNL_MatchDecided.uasset"),
    "waiting":("/ShooterCore/GameplayCues/GCNL_WaitingForPlayers.GCNL_WaitingForPlayers", "Plugins/GameFeatures/ShooterCore/Content/GameplayCues/GCNL_WaitingForPlayers.uasset")}
EVENTS = ("OnLoopingStart", "OnRemoval")


def kind(pin):
    return EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category,
        PinSubCategoryObject=pin.sub_category_object, bIsReference=pin.is_reference, bIsConst=pin.is_const)


def generate(stage):
    official = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    digest = hashlib.sha256((official/RELATIVE).read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original Cue widget base required")
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, CLASS.removesuffix("_C")); ue.unregister_all_mixins()
    before = snapshot(bp, "cue-widget-base-before"); signatures = {name:ue.describe_function(bp.GeneratedClass, name) for name in EVENTS}
    abstract_before = bool(bp.bGenerateAbstractClass)
    children = {}
    for label,(package,relative) in CHILDREN.items():
        child = ue.load_object(Blueprint, package); file = stage/relative; value = hashlib.sha256(file.read_bytes()).hexdigest()
        if value != hashlib.sha256((official/relative).read_bytes()).hexdigest(): raise RuntimeError("fresh original Cue child required")
        children[label] = dict(bp=child, relative=relative, sha256=value, cdo=snapshot(child, "cue-widget-"+label+"-before"),
            signatures={name:ue.describe_function(child.GeneratedClass, name) for name in EVENTS})
    graphs = [(g, {n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    if sum(len(names) for _,names in graphs) != 40: raise RuntimeError("original Cue widget footprint differs")
    graph = bp.UbergraphPages[0]; nodes = {n.get_name():n for n in graph.Nodes}
    parent, removal = nodes["K2Node_CallParentFunction_1"], nodes["K2Node_Event_3"]
    if str(parent.FunctionReference.MemberName) != "OnLoopingStart": raise RuntimeError("native Cue parent continuation differs")
    ignored = set()
    for node in (parent, removal):
        target, = node.node_find_pin("then").get_linked_to(); ignored.update(((node.get_name(), "then"), (target.owning_node.get_name(), target.name)))
    hashes = {g.get_name():semantics(g, names, ignored if g == graph else set()) for g,names in graphs}
    for name,event in ((START,nodes["K2Node_Event_1"]), (REMOVE,removal)):
        g = ue.blueprint_add_function(bp, name); entry = g.Nodes[0]; result = g.graph_add_node(K2Node_FunctionResult)
        for parameter in ("Target", "Parameters", "SpawnResults"): entry.node_create_pin(1, kind(event.node_find_pin(parameter)), parameter)
        result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "ReturnValue"); result.node_find_pin("ReturnValue").default_value = "true"
        connect(entry, "then", result, "execute")
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    for node,name,event in ((parent,START,nodes["K2Node_Event_1"]), (removal,REMOVE,removal)):
        old = {n.get_name() for n in graph.Nodes}; insert_gate(graph, node, "then", getattr(bp.GeneratedClass, name))
        call, = [n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name() == "K2Node_CallFunction"]
        for parameter in ("Target", "Parameters", "SpawnResults"): connect(event, parameter, call, parameter)
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset("DA_CueWidgetMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_hud.cue_widget_mixin", PythonClass="LyraCueWidget"+name+"Profile") for name in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or snapshot(bp, "cue-widget-base-after") != before or any(ue.describe_function(bp.GeneratedClass,name) != value for name,value in signatures.items()): raise RuntimeError("Cue base CDO/native event ABI changed")
    if any(semantics(g,names,ignored if g == graph else set()) != hashes[g.get_name()] for g,names in graphs): raise RuntimeError("original Cue graph changed outside typed gates")
    for label,row in children.items():
        if snapshot(row["bp"], "cue-widget-"+label+"-after") != row["cdo"] or any(ue.describe_function(row["bp"].GeneratedClass,name) != value for name,value in row["signatures"].items()) or hashlib.sha256((stage/row["relative"]).read_bytes()).hexdigest() != row["sha256"]: raise RuntimeError("Cue child defaults/events/bytes changed")
    interface_nodes = sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ("GetPythonMixinSet", "GetPythonMixinProfile"))
    added = sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-40
    if added != 8+interface_nodes: raise RuntimeError("Cue transport footprint differs: "+str((added,interface_nodes)))
    try:
        ue.register_declared_mixin(bp.GeneratedClass); row, = [r for r in ue.get_registered_mixins() if r["target_class"] == bp.GeneratedClass]
        counts = {name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts != dict(Python=2,BlueprintFallback=2): raise RuntimeError("two base-owned Cue methods required")
    finally: ue.unregister_all_mixins()
    probe = ue.create_blueprint(ue.find_class("Object"), "/Game/UEPValidation/BP_CueWidgetCaller")
    for method,source in (("Start", "AddGameplayCueOnActor"), ("Remove", "RemoveGameplayCueOnActor")):
        g = ue.blueprint_add_function(probe, method); entry = g.Nodes[0]
        call = g.graph_add_node_call_function(getattr(ue.find_class("GameplayCueFunctionLibrary"),source)); result = g.graph_add_node(K2Node_FunctionResult)
        for pin in call.node_pins():
            if pin.direction == 0 and pin.category not in ("exec", "delegate") and pin.name != "self":
                name = pin.name
                entry.node_create_pin(1,kind(pin),name); connect(entry,name,call,pin.name)
        connect(entry,"then",call,"execute"); connect(call,"then",result,"execute")
    ue.compile_blueprint(probe)
    if int(probe.Status) == 2: raise RuntimeError("native Cue Blueprint caller failed")
    fixture = ue.create_blueprint(bp.GeneratedClass, "/Game/UEPValidation/BP_CueWidgetBaseFixture")
    fixture.bGenerateAbstractClass = False; ue.compile_blueprint(fixture); ue.unregister_all_mixins()
    if int(fixture.Status) == 2 or fixture.ParentClass != bp.GeneratedClass or not abstract_before or bool(bp.bGenerateAbstractClass) != abstract_before: raise RuntimeError("production abstract base/concrete diagnostic child differs")
    for asset in (bp,mixin,probe,fixture): asset.save_package()
    return dict(status="passed",kind="cuewidgets",runtime_acceptance=False,full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,
        original_business_graphs_preserved_with_dispatch=True,original_graph_nodes=40,original_graphs=hashes,
        original_native_parent_start_call_preserved=True,child_defaults_event_signatures_and_asset_bytes_preserved=True,
        production_abstract_base_preserved=True,
        child_reference_hashes={row["relative"]:row["sha256"] for row in children.values()},base_owned_gates=True,
        transport_nodes=8,interface_nodes=interface_nodes,new_business_nodes=0,native_end_adapter_nodes=0,
        actual_registered_profile_method_counts=counts,caller_probe=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),
        fixture_probe=dict(stage_only=True,asset=str(stage/FIXTURE),sha256=hashlib.sha256((stage/FIXTURE).read_bytes()).hexdigest(),parent=bp.GeneratedClass.get_path_name()),
        assets=[RELATIVE,SET])
