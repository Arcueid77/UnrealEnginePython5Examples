"""Retain BP business behind typed virtual boolean gates; no runtime policy."""
import hashlib
import json
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType


def path(value):
    return value.get_path_name() if value is not None else None


def semantics(graph, names, ignored):
    rows = []
    for node in sorted(graph.Nodes, key=lambda value: value.get_name()):
        if node.get_name() not in names:
            continue
        reference = None
        try:
            value = node.FunctionReference
            reference = [str(value.MemberName), path(value.MemberParent), bool(value.bSelfContext)]
        except Exception:
            pass
        pins = []
        for pin in node.node_pins():
            endpoint = node.get_name(), pin.name
            links = sorted((other.owning_node.get_name(), other.name) for other in pin.get_linked_to()
                if other.owning_node.get_name() in names and endpoint not in ignored and
                (other.owning_node.get_name(), other.name) not in ignored)
            pins.append(dict(name=pin.name, direction=pin.direction, category=pin.category, sub_category=pin.sub_category,
                object_type=path(pin.sub_category_object), container=pin.container_type, reference=pin.is_reference,
                const=pin.is_const, default=pin.default_value, text=str(pin.default_text_value), object=path(pin.default_object), links=links))
        rows.append(dict(name=node.get_name(), cls=node.get_class().get_name(), function=reference, pins=pins))
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def make_gate(bp, name, parameter, source_pin=None):
    if any(graph.get_name() == name for graph in bp.FunctionGraphs):
        raise RuntimeError("fresh gate authoring required: "+name)
    graph = ue.blueprint_add_function(bp, name)
    entry = graph.Nodes[0]
    if parameter:
        kind = EdGraphPinType(PinCategory=source_pin.category, PinSubCategory=source_pin.sub_category,
                             PinSubCategoryObject=source_pin.sub_category_object)
        entry.node_create_pin(1, kind, parameter)
    result = graph.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "ReturnValue")
    result.node_find_pin("ReturnValue").default_value = "true"
    entry.node_find_pin("then").make_link_to(result.node_find_pin("execute"))


def insert_gate(graph, entry, output_name, function, parameter=None, source_name=None):
    output = entry.node_find_pin(output_name)
    previous = output.get_linked_to()
    if len(previous) != 1:
        raise RuntimeError("one original execution path required: "+entry.get_name()+"/"+output_name)
    call = graph.graph_add_node_call_function(function)
    branch = graph.graph_add_node(K2Node_IfThenElse)
    output.break_link_to(previous[0])
    output.make_link_to(call.node_find_pin("execute"))
    call.node_find_pin("then").make_link_to(branch.node_find_pin("execute"))
    call.node_find_pin("ReturnValue").make_link_to(branch.node_find_pin("Condition"))
    branch.node_find_pin("then").make_link_to(previous[0])
    if parameter:
        entry.node_find_pin(source_name).make_link_to(call.node_find_pin(parameter))
    if branch.node_find_pin("else").get_linked_to():
        raise RuntimeError("Python gate must not fall through to original BP")
    # Keep the dispatch readable when opening the retained graph in the editor.
    call.NodePosX, call.NodePosY = entry.NodePosX+260, entry.NodePosY
    branch.NodePosX, branch.NodePosY = entry.NodePosX+520, entry.NodePosY
