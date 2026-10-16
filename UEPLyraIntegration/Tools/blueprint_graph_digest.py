"""Semantic fingerprint of a captured transport graph, excluding editor layout."""
import hashlib
import json


def path(value):
    return None if value is None else value.get_path_name()


def digest(graph):
    nodes = []
    for node in sorted(graph.Nodes, key=lambda value: value.get_name()):
        reference = None
        if node.get_class().get_name() == "K2Node_CallFunction":
            value = node.FunctionReference
            reference = [str(value.MemberName), path(value.MemberParent), bool(value.bSelfContext)]
        pins = [{"name": pin.name, "direction": pin.direction, "category": pin.category,
                 "sub_category": pin.sub_category, "object_type": path(pin.sub_category_object),
                 "container": pin.container_type, "reference": pin.is_reference, "const": pin.is_const,
                 "default": pin.default_value, "text": str(pin.default_text_value), "object": path(pin.default_object),
                 "links": sorted((link.owning_node.get_name(), link.name) for link in pin.get_linked_to())}
                for pin in node.node_pins()]
        nodes.append({"name": node.get_name(), "class": node.get_class().get_name(), "function": reference, "pins": pins})
    return hashlib.sha256(json.dumps(nodes, sort_keys=True).encode()).hexdigest()
