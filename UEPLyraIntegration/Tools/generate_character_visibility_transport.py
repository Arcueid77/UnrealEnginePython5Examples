"""Exact native InitState registration; no Blueprint visibility decisions."""
import unreal_engine as ue
from unreal_engine.classes import K2Node_CreateDelegate, K2Node_Self
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_characters.visibility_mixin import SHOW, REGISTER


def generate(bp):
    graph = ue.blueprint_add_function(bp, REGISTER); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("LyraPawnExtensionComponent")), "Component")
    entry.node_create_pin(1, EdGraphPinType(PinCategory="struct", PinSubCategoryObject=ue.find_struct("GameplayTag")), "RequiredState")
    entry.node_create_pin(1, EdGraphPinType(PinCategory="bool"), "bCallImmediately")
    call = graph.graph_add_node_call_function(ue.find_class("GameFrameworkInitStateInterface").RegisterAndCallForInitStateChange)
    delegate, owner = graph.graph_add_node(K2Node_CreateDelegate), graph.graph_add_node(K2Node_Self)
    connect(entry, "then", call, "execute"); connect(entry, "Component", call, "self")
    connect(entry, "RequiredState", call, "RequiredState"); connect(entry, "bCallImmediately", call, "bCallImmediately")
    connect(owner, "self", delegate, "self"); connect(delegate, "OutputDelegate", call, "Delegate"); delegate.SelectedFunctionName = SHOW
    if len(graph.Nodes) != 4: raise RuntimeError("InitState registration transport contains business nodes")
    return dict(function=REGISTER, nodes=4, gameplay_business=False, python_callback_retained=False, callback=SHOW,
        native_function="RegisterAndCallForInitStateChange", native_arguments_forwarded=True)
