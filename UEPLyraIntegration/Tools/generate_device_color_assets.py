"""Device-color BP business gate; original native-parent wiring is retained."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_FunctionResult, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile
from mixin_graph_gates import semantics
from message_payload_graphs import connect

RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Game/B_TeamColor_DeviceProperty.uasset"
PACKAGE = "/ShooterCore/Game/B_TeamColor_DeviceProperty.B_TeamColor_DeviceProperty"
GATE = "UEPDeviceColorRoute"
INPUTS = ("PlatformUser", "DeviceId", "DeltaTime", "Duration")


def snapshot(bp, label):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPHeroAbilityAssetsResult="))
    path = Path(result).parent/("device-color-"+label+"-cdo.t3d")
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    if not exporter.export_to_file(bp.GeneratedClass.get_cdo(), str(path)): raise RuntimeError("native device-color CDO export failed")
    raw = path.read_bytes(); text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("PythonMixinProfile=", "PythonMixinSet=")))


def one(rows):
    if len(rows) != 1: raise RuntimeError("one original device-color entry/parent required")
    return rows[0]


def generate(stage):
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = source/RELATIVE; digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original device-color asset required")
    bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    before, original_class = snapshot(bp, "before"), bp.GeneratedClass.get_path_name()
    signatures = {method: ue.describe_function(bp.GeneratedClass, method) for method in ("EvaluateDeviceProperty", "ApplyDeviceProperty", "ResetDeviceProperty")}
    graph = bp.UbergraphPages[0]
    entry = one([node for node in graph.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "EvaluateDeviceProperty"])
    parent = one([node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallParentFunction"])
    if str(parent.FunctionReference.MemberName) != "EvaluateDeviceProperty" or parent.node_find_pin("DeviceId").get_linked_to():
        raise RuntimeError("original device-color native-parent wiring differs from audited baseline")
    ignored = {(entry.get_name(), "then")}
    originals = [(item, {node.get_name() for node in item.Nodes}) for item in ue.blueprint_get_all_graphs(bp)]
    hashes = {item.get_name(): semantics(item, names, ignored) for item, names in originals}
    route = ue.blueprint_add_function(bp, GATE); route_entry = route.Nodes[0]
    for name in INPUTS:
        pin = entry.node_find_pin(name)
        route_entry.node_create_pin(1, EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category, PinSubCategoryObject=pin.sub_category_object), name)
    result = route.graph_add_node(K2Node_FunctionResult)
    for name, default in (("ReturnValue", "true"), ("bCallNativeParent", "false")):
        result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), name); result.node_find_pin(name).default_value = default
    connect(route_entry, "then", result, "execute"); ue.compile_blueprint(bp)
    previous = one(entry.node_find_pin("then").get_linked_to()); entry.node_find_pin("then").break_link_to(previous)
    call = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, GATE))
    choose, native = graph.graph_add_node(K2Node_IfThenElse), graph.graph_add_node(K2Node_IfThenElse)
    connect(entry, "then", call, "execute"); connect(call, "then", choose, "execute"); connect(call, "ReturnValue", choose, "Condition")
    choose.node_find_pin("then").make_link_to(previous)
    connect(choose, "else", native, "execute"); connect(call, "bCallNativeParent", native, "Condition")
    connect(native, "then", parent, "execute")
    for name in INPUTS: connect(entry, name, call, name)
    name = "DA_DeviceColorMixin"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None: raise RuntimeError("fresh device-color Mixin Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_devices.team_color_mixin", PythonClass="LyraDeviceColor"+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or snapshot(bp, "after") != before:
        raise RuntimeError("original device-color class/full CDO defaults changed")
    for method, signature in signatures.items():
        if ue.describe_function(bp.GeneratedClass, method) != signature: raise RuntimeError("original device-color public signature changed")
    for item, names in originals:
        if semantics(item, names, ignored) != hashes[item.get_name()]: raise RuntimeError("original device-color graph/parent wiring changed")
    gate = ue.describe_function(bp.GeneratedClass, GATE)
    if {value["name"] for value in gate["parameters"] if value["output"]} != {"ReturnValue", "bCallNativeParent"}:
        raise RuntimeError("typed device-color route outputs differ")
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(original.read_bytes()).hexdigest() != digest: raise RuntimeError("official device-color asset changed")
    return dict(status="passed", kind="devicecolor", runtime_acceptance=False, full_acceptance=False, native_end_adapter_nodes=0,
        original_class=original_class, original_signature=signatures["EvaluateDeviceProperty"], extra_signatures=signatures,
        original_class_defaults_signature_graphs_preserved=True, full_device_cdo_preserved=True, original_graphs=hashes,
        native_parent_wiring_preserved=True, native_parent_device_id_pin_unconnected=True, typed_route_signature=gate,
        assets=[RELATIVE, "Content/UEPMixins/"+name+".uasset"], reference_hashes={str(original): digest})
