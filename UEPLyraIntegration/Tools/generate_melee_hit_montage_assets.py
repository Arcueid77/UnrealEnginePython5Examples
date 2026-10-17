"""Retain Melee graphs/defaults; configure only the original named-output helper."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_dash_selector_assets import snapshot

PACKAGE = "/ShooterCore/Game/Melee/GA_Melee.GA_Melee"
RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Game/Melee/GA_Melee.uasset"
METHOD = "Slelect Hit Montage"
PROBE = "/Game/UEPValidation/BP_MeleeHitMontageProbe"
PROBE_RELATIVE = "Content/UEPValidation/BP_MeleeHitMontageProbe.uasset"
MONTAGES = {
    "back": "/Game/Characters/Heroes/Mannequin/Animations/Actions/AM_MM_HitReact_Back_Med_01.AM_MM_HitReact_Back_Med_01",
    "front": "/Game/Characters/Heroes/Mannequin/Animations/Actions/AM_MM_HitReact_Front_Hvy_01.AM_MM_HitReact_Front_Hvy_01",
    "right": "/Game/Characters/Heroes/Mannequin/Animations/Actions/AM_MM_HitReact_Right_Med_01.AM_MM_HitReact_Right_Med_01",
    "left": "/Game/Characters/Heroes/Mannequin/Animations/Actions/AM_MM_HitReact_Left_Med_01.AM_MM_HitReact_Left_Med_01"}


def selector(bp):
    graph, = [value for value in ue.blueprint_get_all_graphs(bp) if value.get_name() == METHOD]
    nodes = {node.get_name(): node for node in graph.Nodes}
    if len(nodes) != 24: raise RuntimeError("original Melee hit helper node footprint changed")
    names = {"K2Node_CallFunction_0": "GetActorForwardVector", "K2Node_CallFunction_1": "GetActorRightVector",
        "K2Node_CallFunction_2": "Dot_VectorVector", "K2Node_CallFunction_25": "Dot_VectorVector",
        "K2Node_CallFunction_7": "InRange_FloatFloat", "K2Node_PromotableOperator_2": "Greater_DoubleDouble", "K2Node_PromotableOperator_3": "Greater_DoubleDouble"}
    if any(str(nodes[name].FunctionReference.MemberName) != function for name, function in names.items()): raise RuntimeError("native hit helper math differs")
    gate = nodes["K2Node_CallFunction_7"]
    if float(gate.node_find_pin("Min").default_value) != -.5 or float(gate.node_find_pin("Max").default_value) != .5 or any(gate.node_find_pin(name).default_value != "true" for name in ("InclusiveMin", "InclusiveMax")):
        raise RuntimeError("original inclusive right-dot bounds differ")
    for name in ("K2Node_PromotableOperator_2", "K2Node_PromotableOperator_3"):
        pin = nodes[name].node_find_pin("B")
        if pin.get_linked_to() or float(pin.default_value or 0.) != 0.: raise RuntimeError("original strict-zero sign comparator differs")
    for node, option, choice in (("K2Node_Select_1", "Option 0", "back"), ("K2Node_Select_1", "Option 1", "front"),
            ("K2Node_Select_0", "Option 0", "right"), ("K2Node_Select_0", "Option 1", "left")):
        if nodes[node].node_find_pin(option).default_object.get_path_name() != MONTAGES[choice]: raise RuntimeError("original hit montage asset control differs")
    return dict(nodes=24, min=-.5, max=.5, inclusive_min=True, inclusive_max=True, strict_sign_zero=0., montages=MONTAGES)


def probe(stage, cls):
    if (stage/PROBE_RELATIVE).exists(): raise RuntimeError("fresh stage-only hit helper caller required")
    bp = ue.create_blueprint(ue.find_class("Object"), PROBE)
    graph = ue.blueprint_add_function(bp, "Select"); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=cls), "AbilityRef")
    call = graph.graph_add_node_call_function(getattr(cls, METHOD)); result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "AbilityRef", call, "self"); connect(entry, "then", call, "execute"); connect(call, "then", result, "execute")
    for source, name in (("Hit Normal", "HitNormal"), ("Hit Actor", "HitActor")):
        pin = call.node_find_pin(source)
        entry.node_create_pin(1, EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category, PinSubCategoryObject=pin.sub_category_object), name)
        connect(entry, name, call, source)
    pin = call.node_find_pin("Hit Montage")
    result.node_create_pin(0, EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category, PinSubCategoryObject=pin.sub_category_object), "HitMontage")
    connect(call, "Hit Montage", result, "HitMontage"); ue.compile_blueprint(bp)
    if int(bp.Status) == 2 or len(graph.Nodes) != 3: raise RuntimeError("typed external BP hit caller did not compile")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, nodes=3, typed_ability_and_actor_references=True,
        virtual_bp_function_call=True, outputs=["HitMontage"], asset=str(stage/PROBE_RELATIVE), sha256=hashlib.sha256((stage/PROBE_RELATIVE).read_bytes()).hexdigest())


def generate(stage):
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = source/RELATIVE; digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original Melee required")
    bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    original_class = bp.GeneratedClass.get_path_name(); before = snapshot(bp, "melee-before")
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in (METHOD, "K2_ActivateAbility", "MontageHit")}
    originals = [(value, {node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes = {value.get_name(): semantics(value, names, set()) for value, names in originals}; audit = selector(bp)
    if ue.find_asset("/Game/UEPMixins/DA_MeleeHitMontageMixin.DA_MeleeHitMontageMixin") is not None: raise RuntimeError("fresh Melee Mixin Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset("DA_MeleeHitMontageMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_abilities.melee_hit_montage_mixin",
        PythonClass="LyraMeleeHitMontage"+name+"Profile") for name in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or snapshot(bp, "melee-after") != before:
        raise RuntimeError("original Melee class/full CDO changed")
    if any(ue.describe_function(bp.GeneratedClass, name) != signature for name, signature in signatures.items()): raise RuntimeError("original Melee signatures changed")
    if any(semantics(value, names, set()) != hashes[value.get_name()] for value, names in originals): raise RuntimeError("original Melee graphs changed")
    bp.save_package(); mixin.save_package(); caller = probe(stage, bp.GeneratedClass)
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == bp.GeneratedClass]
        counts = {name: len(value["functions"]) for name, value in binding["profiles"].items()}
        if counts != dict(Python=1, BlueprintFallback=1): raise RuntimeError("one named-output helper per Profile required")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass, name) != signature for name, signature in signatures.items()): raise RuntimeError("original hit helper signatures did not restore")
    bp.save_package(); mixin.save_package()
    return dict(status="passed", kind="meleehitmontage", runtime_acceptance=False, full_acceptance=False, native_end_adapter_nodes=0,
        original_class=original_class, original_signature=signatures[METHOD], extra_signatures=signatures,
        original_class_defaults_signature_graphs_preserved=True, original_full_cdo_preserved=True, original_graphs_unmodified=True,
        original_graphs=hashes, original_selector=audit, native_register_restore_passed=True, actual_registered_profile_method_counts=counts,
        caller_probe=caller, new_business_nodes=0, whole_melee_activation_trace_damage_migrated=False,
        assets=[RELATIVE, "Content/UEPMixins/DA_MeleeHitMontageMixin.uasset"], reference_hashes={str(original): digest})
