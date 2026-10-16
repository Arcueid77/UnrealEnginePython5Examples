"""Two inventory-pad BPs: retain original blocks behind virtual script gates."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_FunctionResult, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_inventory_pad_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass generator to Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

PARENT = "/ShooterCore/Blueprint/B_GrantInventory_Pad.B_GrantInventory_Pad"
CHILD = "/ShooterCore/Blueprint/B_GrantInventoryPad_WithMesh.B_GrantInventoryPad_WithMesh"
HOOKS = (("UEPDispatchInventoryPadConstruction", None), ("UEPDispatchInventoryPadOverlap", "OtherActor"),
         ("UEPDispatchInventoryPadMeshConstruction", None), ("UEPDispatchInventoryPadMeshTick", "DeltaSeconds"))


def argument(name):
    return next((arg[len(name)+2:] for arg in sys.argv if arg.startswith("-"+name+"=")), None)


def path(value):
    return None if value is None else value.get_path_name()


def original_semantics(graph, original_names, ignored_link):
    """Ignore only the rewired entry exec edge and newly added dispatch nodes."""
    result = []
    for node in sorted(graph.Nodes, key=lambda value: value.get_name()):
        if node.get_name() not in original_names:
            continue
        reference = None
        try:
            value = node.FunctionReference
            reference = [str(value.MemberName), path(value.MemberParent), bool(value.bSelfContext)]
        except Exception:
            pass  # Data/comment/entry nodes do not have FunctionReference.
        pins = []
        for pin in node.node_pins():
            endpoint = (node.get_name(), pin.name)
            links = sorted((link.owning_node.get_name(), link.name) for link in pin.get_linked_to()
                if link.owning_node.get_name() in original_names and endpoint != ignored_link and
                (link.owning_node.get_name(), link.name) != ignored_link)
            pins.append({"name": pin.name, "direction": pin.direction, "category": pin.category,
                "sub_category": pin.sub_category, "object_type": path(pin.sub_category_object),
                "container": pin.container_type, "reference": pin.is_reference, "const": pin.is_const,
                "default": pin.default_value, "text": str(pin.default_text_value), "object": path(pin.default_object), "links": links})
        result.append({"name": node.get_name(), "class": node.get_class().get_name(), "function": reference, "pins": pins})
    return hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()


def make_gate(parent, name, parameter):
    if any(graph.get_name() == name for graph in parent.FunctionGraphs):
        return
    graph = ue.blueprint_add_function(parent, name)
    entry = graph.Nodes[0]
    if parameter:
        kind = EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("Actor")) if parameter == "OtherActor" else EdGraphPinType(PinCategory="real", PinSubCategory="float")
        entry.node_create_pin(1, kind, parameter)
    result = graph.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "ReturnValue")
    result.node_find_pin("ReturnValue").default_value = "true"
    entry.node_find_pin("then").make_link_to(result.node_find_pin("execute"))


def gate_entry(graph, entry, function, name, parameter):
    output = entry.node_find_pin("then")
    links = output.get_linked_to()
    if len(links) != 1:
        raise RuntimeError("expected exactly one original exec path: " + name)
    # An existing wrapper is accepted only with the exact topology below.
    first = links[0].owning_node
    try:
        existing = str(first.FunctionReference.MemberName) == name
    except Exception:
        existing = False
    if existing:
        next_links = first.node_find_pin("then").get_linked_to()
        if len(next_links) != 1 or next_links[0].owning_node.get_class().get_name() != "K2Node_IfThenElse":
            raise RuntimeError("partially authored gate: " + name)
        branch = next_links[0].owning_node
        if branch.node_find_pin("else").get_linked_to() or len(branch.node_find_pin("then").get_linked_to()) != 1:
            raise RuntimeError("unsafe original/exception fallback topology: " + name)
        return {"hook": name, "original_blocks_retained": True, "added_dispatch_nodes": 2, "already_authored": True}
    old_names = {node.get_name() for node in graph.Nodes}
    ignored = (entry.get_name(), "then")
    before = original_semantics(graph, old_names, ignored)
    original_input = links[0]
    call = graph.graph_add_node_call_function(function)
    branch = graph.graph_add_node(K2Node_IfThenElse)
    output.break_link_to(original_input)
    output.make_link_to(call.node_find_pin("execute"))
    call.node_find_pin("then").make_link_to(branch.node_find_pin("execute"))
    call.node_find_pin("ReturnValue").make_link_to(branch.node_find_pin("Condition"))
    branch.node_find_pin("then").make_link_to(original_input)
    if parameter:
        entry.node_find_pin(parameter).make_link_to(call.node_find_pin(parameter))
    after = original_semantics(graph, old_names, ignored)
    if before != after or branch.node_find_pin("else").get_linked_to():
        raise RuntimeError("original business semantics changed: " + name)
    return {"hook": name, "original_blocks_retained": True, "added_dispatch_nodes": 2, "original_semantic_digest": before,
            "original_node_names": sorted(old_names), "ignored_entry_exec": list(ignored), "already_authored": False}


def generate():
    stage = require_authoring_stage(argument("UEPInventoryPadStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    references = [reference/("Plugins/GameFeatures/ShooterCore/Content/Blueprint/"+name+".uasset") for name in ("B_GrantInventory_Pad", "B_GrantInventoryPad_WithMesh")]
    hashes = {str(file): hashlib.sha256(file.read_bytes()).hexdigest() for file in references}
    ue.unregister_all_mixins()
    parent, child = ue.load_object(Blueprint, PARENT), ue.load_object(Blueprint, CHILD)
    expected_names = [parent.GeneratedClass.get_name(), child.GeneratedClass.get_name()]
    for name, parameter in HOOKS:
        make_gate(parent, name, parameter)
    ue.compile_blueprint(parent)
    original = []
    for bp, hook_index, event_kind in ((parent, 0, "construction"), (parent, 1, "overlap"),
                                       (child, 2, "construction"), (child, 3, "tick")):
        if event_kind == "construction":
            graph = next(graph for graph in bp.FunctionGraphs if graph.get_name() == "UserConstructionScript")
            entry = graph.Nodes[0]
        else:
            graph = bp.UbergraphPages[0]
            if event_kind == "overlap":
                matches = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_ComponentBoundEvent"]
            else:
                matches = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "ReceiveTick"]
            if len(matches) != 1:
                raise RuntimeError("ambiguous native entry: " + event_kind)
            entry = matches[0]
        name, parameter = HOOKS[hook_index]
        row = gate_entry(graph, entry, getattr(parent.GeneratedClass, name), name, parameter)
        row.update(asset=bp.get_path_name(), graph=graph.get_name())
        original.append(row)
    mixin_path = "/Game/UEPMixins/DA_InventoryPadMixin"
    mixin = ue.find_asset(mixin_path+".DA_InventoryPadMixin")
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset("DA_InventoryPadMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_world.inventory_pad_mixin",
        PythonClass="LyraInventoryPad"+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(parent, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(parent)
    ue.unregister_all_mixins()
    ue.compile_blueprint(child)
    for bp, expected in zip((parent, child), expected_names):
        if int(bp.Status) == 2 or bp.GeneratedClass.get_name() != expected:
            raise RuntimeError("inventory BP compile/class identity failed")
        if bp.GeneratedClass.get_cdo().GetPythonMixinSet() != mixin:
            raise RuntimeError("parent/inherited Interface CDO did not resolve one parent Set")
    for row in original:
        if not row["already_authored"]:
            bp = parent if row["asset"] == PARENT else child
            graph = next(graph for graph in ue.blueprint_get_all_graphs(bp) if graph.get_name() == row["graph"])
            if original_semantics(graph, set(row["original_node_names"]), tuple(row["ignored_entry_exec"])) != row["original_semantic_digest"]:
                raise RuntimeError("compile changed original business graph")
    for bp in (parent, child, mixin):
        bp.save_package()
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("official inventory BP changed")
    return {"status": "passed", "runtime_acceptance": False, "class_preserved": True, "related_class_routers_used": False,
        "single_parent_interface_set": True, "original_blocks_retained": True, "exception_defaults_to_no_original": True,
        "gates": original, "reference_hashes": hashes, "assets": [PARENT, CHILD, mixin_path+".DA_InventoryPadMixin"]}


result = argument("UEPGenerateInventoryPadResult")
if result is None:
    raise RuntimeError("UEPGenerateInventoryPadResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_INVENTORY_PAD_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
