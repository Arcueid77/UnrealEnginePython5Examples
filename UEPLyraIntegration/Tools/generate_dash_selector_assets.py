"""Only the retained Dash helper is routed; no activation/RPC graph edits."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile
from mixin_graph_gates import semantics
from message_payload_graphs import connect

RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Game/Dash/GA_Hero_Dash.uasset"
PACKAGE = "/ShooterCore/Game/Dash/GA_Hero_Dash.GA_Hero_Dash"
PROBE = "/Game/UEPValidation/BP_DashSelectorProbe"
PROBE_RELATIVE = "Content/UEPValidation/BP_DashSelectorProbe.uasset"
METHOD = "SelectDirectionalMontage"


def snapshot(bp, label):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPHeroAbilityAssetsResult="))
    file = Path(result).parent/("dash-"+label+"-cdo.t3d")
    if not ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(bp.GeneratedClass.get_cdo(), str(file)):
        raise RuntimeError("native Dash full CDO export failed")
    data = file.read_bytes(); text = data.decode("utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("PythonMixinProfile=", "PythonMixinSet=")))


def audit(bp):
    graph, = [value for value in ue.blueprint_get_all_graphs(bp) if value.get_name() == METHOD]
    nodes = {node.get_name(): node for node in graph.Nodes}
    if len(nodes) != 26: raise RuntimeError("original Dash selector graph footprint differs")
    def link(node, pin, source, output):
        actual, = nodes[node].node_find_pin(pin).get_linked_to()
        if actual.owning_node != nodes[source] or actual.name != output: raise RuntimeError("original Dash selector dataflow differs: "+node+"/"+pin)
    for node, pin, source, output in (
        ("K2Node_IfThenElse_1", "execute", "K2Node_FunctionEntry_0", "then"),
        ("K2Node_IfThenElse_2", "execute", "K2Node_IfThenElse_1", "else"),
        ("K2Node_IfThenElse_0", "execute", "K2Node_IfThenElse_2", "else"),
        ("K2Node_CallFunction_11", "InVec", "K2Node_FunctionEntry_0", "FacingDirection"),
        ("K2Node_CallFunction_12", "InVec", "K2Node_FunctionEntry_0", "MovementDirection"),
        ("K2Node_CallFunction_14", "A", "K2Node_CallFunction_12", "ReturnValue"),
        ("K2Node_CallFunction_14", "B", "K2Node_CallFunction_11", "ReturnValue"),
        ("K2Node_CallFunction_1", "A", "K2Node_CallFunction_14", "ReturnValue_Yaw"),
        ("K2Node_PromotableOperator_1", "A", "K2Node_CallFunction_1", "ReturnValue"),
        ("K2Node_PromotableOperator_2", "A", "K2Node_CallFunction_1", "ReturnValue"),
        ("K2Node_PromotableOperator_4", "A", "K2Node_CallFunction_14", "ReturnValue_Yaw"),
        ("K2Node_IfThenElse_1", "Condition", "K2Node_PromotableOperator_1", "ReturnValue"),
        ("K2Node_IfThenElse_2", "Condition", "K2Node_PromotableOperator_2", "ReturnValue"),
        ("K2Node_IfThenElse_0", "Condition", "K2Node_PromotableOperator_4", "ReturnValue")):
        link(node, pin, source, output)
    for node, threshold in (("K2Node_PromotableOperator_1", 45.), ("K2Node_PromotableOperator_2", 135.), ("K2Node_PromotableOperator_4", 0.)):
        pin = nodes[node].node_find_pin("B")
        if pin.get_linked_to() or float(pin.default_value or 0.) != threshold: raise RuntimeError("original Dash selector threshold differs")
    for node, name in (("K2Node_CallFunction_11", "Conv_VectorToRotator"), ("K2Node_CallFunction_12", "Conv_VectorToRotator"),
            ("K2Node_CallFunction_14", "NormalizedDeltaRotator"), ("K2Node_CallFunction_1", "Abs"),
            ("K2Node_PromotableOperator_1", "Less_DoubleDouble"), ("K2Node_PromotableOperator_2", "Greater_DoubleDouble"), ("K2Node_PromotableOperator_4", "Less_DoubleDouble")):
        if str(nodes[node].FunctionReference.MemberName) != name: raise RuntimeError("original Dash selector native math differs")
    return dict(nodes=26, forward_abs_yaw_less_than=45., backward_abs_yaw_greater_than=135., left_yaw_less_than=0.,
        forward_bias_only=True, native_math_retained=True, graph=semantics(graph, set(nodes), set()))


def probe(stage, cls):
    if (stage/PROBE_RELATIVE).exists(): raise RuntimeError("fresh stage-only Dash caller required")
    bp = ue.create_blueprint(ue.find_class("Object"), PROBE)
    graph = ue.blueprint_add_function(bp, "Select"); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=cls), "AbilityRef")
    call = graph.graph_add_node_call_function(getattr(cls, METHOD)); result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "AbilityRef", call, "self")
    for name in ("FacingDirection", "MovementDirection"):
        pin = call.node_find_pin(name)
        entry.node_create_pin(1, EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category, PinSubCategoryObject=pin.sub_category_object), name)
        connect(entry, name, call, name)
    for name in ("DirectionalMontage", "BiasForwardMovement"):
        pin = call.node_find_pin(name)
        result.node_create_pin(0, EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category, PinSubCategoryObject=pin.sub_category_object), name)
        connect(call, name, result, name)
    executable = any(pin.name == "execute" for pin in call.node_pins())
    if executable: connect(entry, "then", call, "execute"); connect(call, "then", result, "execute")
    else: connect(entry, "then", result, "execute")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2 or len(graph.Nodes) != 3: raise RuntimeError("Dash named-output caller compile/shape failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, nodes=3, typed_ability_reference=True, virtual_bp_function_call=True,
        outputs=["DirectionalMontage", "BiasForwardMovement"], asset=str(stage/PROBE_RELATIVE), sha256=hashlib.sha256((stage/PROBE_RELATIVE).read_bytes()).hexdigest())


def generate(stage):
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = source/RELATIVE; digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original Dash required")
    bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    cls = bp.GeneratedClass; before = snapshot(bp, "before"); original_class = cls.get_path_name()
    signatures = {name: ue.describe_function(cls, name) for name in (METHOD, "K2_ActivateAbility", "SendInfo")}
    graphs = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    hashes = {graph.get_name(): semantics(graph, names, set()) for graph, names in graphs}; selector = audit(bp)
    name = "DA_DashSelectorMixin"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None: raise RuntimeError("fresh Dash Mixin Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities.dash_selector_mixin", PythonClass="LyraDashSelector"+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or snapshot(bp, "after") != before:
        raise RuntimeError("original Dash class/full CDO changed")
    for name, signature in signatures.items():
        if ue.describe_function(bp.GeneratedClass, name) != signature: raise RuntimeError("original Dash signature changed: "+name)
    for graph, names in graphs:
        if semantics(graph, names, set()) != hashes[graph.get_name()]: raise RuntimeError("original Dash graph changed")
    bp.save_package(); mixin.save_package()
    caller = probe(stage, bp.GeneratedClass)
    from generate_mixin_inheritance_probe import generate as inheritance_probe
    inheritance = inheritance_probe(stage)
    # Verify the real native router accepts both original named-output profiles.
    try:
        try: ue.register_declared_mixin(bp.GeneratedClass)
        except Exception as error:
            diagnostic = dict(generated_class=bp.GeneratedClass.get_path_name(), class_flags=int(bp.GeneratedClass.class_get_flags()),
                direct_interfaces=[value.Interface.get_path_name() for value in bp.get_property("ImplementedInterfaces")],
                getter_owners={name: ue.describe_function(bp.GeneratedClass, name)["owner"] for name in ("GetPythonMixinSet", "GetPythonMixinProfile")})
            raise RuntimeError("Dash actual registration rejected: "+json.dumps(diagnostic)) from error
        registered, = [entry for entry in ue.get_registered_mixins() if entry["target_class"] == bp.GeneratedClass]
        method_counts = {profile: len(value["functions"]) for profile, value in registered["profiles"].items()}
        if method_counts != dict(Python=1, BlueprintFallback=1): raise RuntimeError("Dash helper registration count differs")
    finally: ue.unregister_all_mixins()
    if ue.describe_function(bp.GeneratedClass, METHOD) != signatures[METHOD]: raise RuntimeError("Dash router did not restore original signature")
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(original.read_bytes()).hexdigest() != digest: raise RuntimeError("official Dash changed")
    return dict(status="passed", kind="dashselector", runtime_acceptance=False, full_acceptance=False, native_end_adapter_nodes=0,
        original_class=original_class, original_signature=signatures[METHOD], extra_signatures=signatures,
        original_class_defaults_signature_graphs_preserved=True, original_full_cdo_preserved=True, original_graphs=hashes,
        original_graphs_unmodified=True, original_selector=selector, actual_registered_profile_method_counts=method_counts,
        native_register_restore_passed=True, caller_probe=caller, inherited_declaration_probe=inheritance, new_business_nodes=0,
        assets=[RELATIVE, "Content/UEPMixins/DA_DashSelectorMixin.uasset"], reference_hashes={str(original): digest})
