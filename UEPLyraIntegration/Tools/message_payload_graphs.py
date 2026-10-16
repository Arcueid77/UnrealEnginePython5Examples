"""Typed Blueprint VM transport authoring; no gameplay or subscription business."""

from unreal_engine.classes import K2Node_FunctionResult, K2Node_TemporaryVariable
from unreal_engine.structs import EdGraphPinType
import unreal_engine as ue


def connect(source, source_pin, target, target_pin):
    source.node_find_pin(source_pin).connect(target.node_find_pin(target_pin))


def read_graph(bp, suffix, payload_type, proxy_class):
    graph = ue.blueprint_add_function(bp, "Read" + suffix)
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=proxy_class), "Proxy")
    result = graph.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="struct", PinSubCategoryObject=payload_type), "Payload")
    result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "Success")
    getter = graph.graph_add_node_call_function(proxy_class.GetPayload)
    temporary = graph.graph_add_node(K2Node_TemporaryVariable)
    temporary.VariableType = EdGraphPinType(PinCategory="struct", PinSubCategoryObject=payload_type)
    graph.graph_reconstruct_node(temporary)
    connect(entry, "then", getter, "execute")
    connect(entry, "Proxy", getter, "self")
    connect(getter, "then", result, "execute")
    # GetPayload's UPARAM(ref) wildcard is an input. Supply typed local storage.
    connect(temporary, "Variable", getter, "OutPayload")
    connect(temporary, "Variable", result, "Payload")
    connect(getter, "ReturnValue", result, "Success")
    return graph


def broadcast_graph(bp, suffix, payload_type, router_class):
    graph = ue.blueprint_add_function(bp, "Broadcast" + suffix)
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=router_class), "Router")
    entry.node_create_pin(1, EdGraphPinType(PinCategory="struct", PinSubCategoryObject=ue.find_struct("GameplayTag")), "Channel")
    entry.node_create_pin(1, EdGraphPinType(PinCategory="struct", PinSubCategoryObject=payload_type), "Payload")
    call = graph.graph_add_node_call_function(router_class.K2_BroadcastMessage)
    connect(entry, "then", call, "execute")
    connect(entry, "Router", call, "self")
    connect(entry, "Channel", call, "Channel")
    connect(entry, "Payload", call, "Message")
    return graph
