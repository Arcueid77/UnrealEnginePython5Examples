"""Add four exact named-delegate transports; original business graphs stay intact."""
import unreal_engine as ue
from unreal_engine.classes import K2Node_AddDelegate, K2Node_RemoveDelegate, K2Node_CreateDelegate, K2Node_Self
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from generate_auto_respawn_helper_assets import generate as helpers

END_BIND, END_CLEAR = "UEPAutoRespawnBindEndPlay", "UEPAutoRespawnUnbindEndPlay"
DEATH_BIND, DEATH_CLEAR = "UEPAutoRespawnBindDeath", "UEPAutoRespawnUnbindDeath"


def transports(bp):
    original = {graph.get_name(): graph for graph in ue.blueprint_get_all_graphs(bp)}
    result = []
    for name, graph_name, binding, member, cls, callback in (
        (END_BIND, "BindDeathListener", True, "OnEndPlay", "Actor", "OnAvatarEndPlay"),
        (END_CLEAR, "ClearDeathListener", False, "OnEndPlay", "Actor", "OnAvatarEndPlay"),
        (DEATH_BIND, "BindDeathListener", True, "OnDeathStarted", "LyraHealthComponent", "OnDeathStarted"),
        (DEATH_CLEAR, "ClearDeathListener", False, "OnDeathStarted", "LyraHealthComponent", "OnDeathStarted")):
        source, = [node for node in original[graph_name].Nodes
            if node.get_class().get_name() == ("K2Node_AddDelegate" if binding else "K2Node_RemoveDelegate")
            and str(node.DelegateReference.MemberName) == member]
        pin, = source.node_find_pin("Delegate").get_linked_to()
        if str(pin.owning_node.SelectedFunctionName) != callback:
            raise RuntimeError("original AutoRespawn delegate target differs: "+member)
        graph = ue.blueprint_add_function(bp, name); entry = graph.Nodes[0]
        entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class(cls)), "Target")
        call = graph.graph_add_node(K2Node_AddDelegate if binding else K2Node_RemoveDelegate)
        call.DelegateReference = source.DelegateReference; graph.graph_reconstruct_node(call)
        delegate, owner = graph.graph_add_node(K2Node_CreateDelegate), graph.graph_add_node(K2Node_Self)
        connect(entry, "then", call, "execute"); connect(entry, "Target", call, "self")
        connect(owner, "self", delegate, "self"); connect(delegate, "OutputDelegate", call, "Delegate")
        delegate.SelectedFunctionName = callback
        if len(graph.Nodes) != 4 or str(call.DelegateReference.MemberName) != member or str(delegate.SelectedFunctionName) != callback:
            raise RuntimeError("exact AutoRespawn native delegate transport differs")
        result.append(dict(function=name, nodes=4, target_class=cls, delegate=member, callback=callback,
            operation="add_unique" if binding else "remove_exact"))
    return result


def generate(stage): return helpers(stage, listener_transports=transports)
