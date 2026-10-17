"""Exactly the original statically selected parent call, not BeginPlay replay."""
import unreal_engine as ue
from unreal_engine.classes import K2Node_CallParentFunction
from unreal_engine.structs import MemberReference
from message_payload_graphs import connect
from uep_lyra_characters.begin_play_mixin import PARENT


def generate(bp, source):
    graph = ue.blueprint_add_function(bp, PARENT); entry = graph.Nodes[0]
    call = graph.graph_add_node(K2Node_CallParentFunction)
    call.FunctionReference = MemberReference(MemberName="ReceiveBeginPlay", MemberParent=source.FunctionReference.MemberParent, bSelfContext=False)
    graph.graph_reconstruct_node(call); connect(entry, "then", call, "execute")
    if len(graph.Nodes) != 2: raise RuntimeError("parent BeginPlay transport contains new business")
    return dict(function=PARENT, nodes=2, gameplay_business=False, parent_function="ReceiveBeginPlay",
        parent_class=source.FunctionReference.MemberParent.get_path_name(), replay_current_actor_begin_play=False)
