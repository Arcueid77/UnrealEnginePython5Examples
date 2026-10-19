"""Preserve motion interface ABI and the original retriggerable latent node."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_CustomEvent, K2Node_FunctionResult
from unreal_engine.structs import UEPPythonMixinProfile, EdGraphPinType
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_dash_selector_assets import snapshot

PACKAGE = "/Game/Effects/Blueprints/B_FootStep.B_FootStep"
RELATIVE = "Content/Effects/Blueprints/B_FootStep.uasset"
PROBE = "Content/UEPValidation/BP_FootstepCaller.uasset"
DELAY, AFTER = "UEPFootstepBeginNativeDelay", "UEPFootstepAfterNativeDelay"


def kind(pin):
    return EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category,
        PinSubCategoryObject=pin.sub_category_object, bIsReference=pin.is_reference, bIsConst=pin.is_const)


def generate(stage):
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original footprint required")
    ue.unregister_all_mixins(); bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    before = snapshot(bp, "footstep-before"); signature = ue.describe_function(bp.GeneratedClass, "AnimMotionEffect")
    graph, = [g for g in ue.blueprint_get_all_graphs(bp) if g.get_name() == "EventGraph"]
    nodes = {n.get_name():n for n in graph.Nodes}
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp)) != 93: raise RuntimeError("original footprint differs")
    delay, branch = nodes["K2Node_CallFunction_10"], nodes["K2Node_IfThenElse_0"]
    if str(delay.FunctionReference.MemberName) != "RetriggerableDelay" or delay.node_find_pin("Duration").default_value != "3.000000": raise RuntimeError("original latent node differs")
    link, = delay.node_find_pin("then").get_linked_to()
    if link.owning_node != branch or link.name != "execute": raise RuntimeError("original cleanup link differs")
    ignored = {(delay.get_name(), "then"), (branch.get_name(), "execute")}
    originals = [(g, {n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    hashes = {g.get_name():semantics(g, keys, ignored if g == graph else set()) for g, keys in originals}
    begin = graph.graph_add_node(K2Node_CustomEvent); begin.CustomFunctionName = DELAY; graph.graph_reconstruct_node(begin); connect(begin, "then", delay, "execute")
    after = graph.graph_add_node(K2Node_CustomEvent); after.CustomFunctionName = AFTER; graph.graph_reconstruct_node(after); connect(after, "then", branch, "execute")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset("DA_FootstepMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_weapons.footstep_mixin", PythonClass="LyraFootstep"+name+"Profile") for name in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    call = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, AFTER))
    delay.node_find_pin("then").break_link_to(branch.node_find_pin("execute")); connect(delay, "then", call, "execute")
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or snapshot(bp, "footstep-after") != before or ue.describe_function(bp.GeneratedClass, "AnimMotionEffect") != signature: raise RuntimeError("original full CDO/interface ABI changed")
    if len(graph.Nodes)-len(nodes) != 3 or any(semantics(g, keys, ignored if g == graph else set()) != hashes[g.get_name()] for g, keys in originals): raise RuntimeError("original footprint graph changed outside delay dispatch")
    try:
        ue.register_declared_mixin(bp.GeneratedClass); binding, = [r for r in ue.get_registered_mixins() if r["target_class"] == bp.GeneratedClass]
        counts = {name:len(row["functions"]) for name,row in binding["profiles"].items()}
        if counts != dict(Python=2, BlueprintFallback=2): raise RuntimeError("motion and cleanup registration required")
    finally: ue.unregister_all_mixins()
    probe = ue.create_blueprint(ue.find_class("Object"), "/Game/UEPValidation/BP_FootstepCaller")
    g = ue.blueprint_add_function(probe, "CallMotion"); entry = g.Nodes[0]
    c = g.graph_add_node_call_function(bp.GeneratedClass.AnimMotionEffect); ret = g.graph_add_node(K2Node_FunctionResult)
    for pin in c.node_pins():
        if pin.direction == 0 and pin.category not in ("exec", "delegate"):
            name = "Target" if pin.name == "self" else pin.name
            entry.node_create_pin(1, kind(pin), name); connect(entry, name, c, pin.name)
    connect(entry, "then", c, "execute"); connect(c, "then", ret, "execute"); ue.compile_blueprint(probe)
    if int(probe.Status) == 2: raise RuntimeError("typed motion caller compile failed")
    for asset in (bp, mixin, probe): asset.save_package()
    return dict(status="passed", kind="footstep", runtime_acceptance=False, full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True, original_full_cdo_preserved=True,
        original_business_graphs_preserved_with_dispatch=True, original_graph_nodes=93, original_graphs=hashes,
        interface_signature=signature, interface_signature_preserved=True, native_end_adapter_nodes=0,
        transport_nodes=3, new_business_nodes=0, original_retriggerable_delay_node_reused=True,
        native_delay_seconds=3., native_delay_uuid_preserved=True, cleanup_tests_validity_not_active=True,
        actual_registered_profile_method_counts=counts, native_register_restore_passed=True,
        caller_probe=dict(stage_only=True, asset=str(stage/PROBE), sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),
        assets=[RELATIVE, "Content/UEPMixins/DA_FootstepMixin.uasset"], reference_hashes={str(source):digest})
