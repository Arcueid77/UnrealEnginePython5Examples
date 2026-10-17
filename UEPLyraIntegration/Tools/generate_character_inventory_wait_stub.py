"""Empty int-linkage resume declaration; native latent manager calls Python."""
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_characters.inventory_wait_mixin import RESUME


def generate(bp, name=RESUME):
    graph = ue.blueprint_add_function(bp, name); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="int"), "Linkage")
    result = graph.graph_add_node(K2Node_FunctionResult); connect(entry, "then", result, "execute")
    if len(graph.Nodes) != 2: raise RuntimeError("inventory wait declaration has business nodes")
    return dict(function=name, nodes=2, parameter="Linkage", parameter_type="int32", gameplay_business=False,
        native_latent_resume_target=True, blueprint_fallback_body_empty=True)
