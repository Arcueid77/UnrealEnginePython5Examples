"""One four-node named multicast transport; no gameplay decision or new event."""
import unreal_engine as ue
from unreal_engine.classes import K2Node_AddDelegate, K2Node_CreateDelegate, K2Node_Self
from unreal_engine.structs import EdGraphPinType, MemberReference
from message_payload_graphs import connect
from uep_lyra_characters.team_listener_mixin import BIND
from uep_lyra_characters.team_observer_mixin import BOUND_EVENT


def generate(bp):
    graph = ue.blueprint_add_function(bp, BIND); entry = graph.Nodes[0]
    cls = ue.find_class("AsyncAction_ObserveTeamColors")
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=cls), "Observer")
    call = graph.graph_add_node(K2Node_AddDelegate)
    # A property getter can expose a borrowed struct view. Never assign that
    # view back onto its own storage: use a separate reflected struct value.
    call.DelegateReference = MemberReference(MemberName="OnTeamChanged", MemberParent=cls, bSelfContext=False)
    graph.graph_reconstruct_node(call)
    delegate, owner = graph.graph_add_node(K2Node_CreateDelegate), graph.graph_add_node(K2Node_Self)
    # AddDelegate initially has an untyped target before its member is set.
    # Require the reconstructed native target to agree with the typed argument.
    for node, name in ((entry, "Observer"), (call, "self")):
        pin = node.node_find_pin(name)
        if pin.category != "object" or pin.sub_category_object != cls:
            raise RuntimeError("native listener pin differs: "+name+"/"+str(pin.category)+"/"+str(pin.sub_category)+"/"+str(pin.sub_category_object)+
                "/reference="+str(call.DelegateReference.MemberParent)+"/self="+str(call.DelegateReference.bSelfContext))
    connect(entry, "Observer", call, "self"); connect(entry, "then", call, "execute")
    connect(owner, "self", delegate, "self"); connect(delegate, "OutputDelegate", call, "Delegate")
    delegate.SelectedFunctionName = BOUND_EVENT
    if len(graph.Nodes) != 4 or str(call.DelegateReference.MemberName) != "OnTeamChanged" or str(delegate.SelectedFunctionName) != BOUND_EVENT:
        raise RuntimeError("Character observer exact native delegate transport differs")
    return dict(function=BIND, nodes=4, target_class="AsyncAction_ObserveTeamColors", delegate="OnTeamChanged",
        callback=BOUND_EVENT, operation="add_unique", gameplay_business=False, python_callback_retained=False)
