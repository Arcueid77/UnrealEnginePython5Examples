"""Typed native reset listener plus script decisions and retained parent End."""
import unreal_engine as ue
from unreal_engine.classes import K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType
from mixin_graph_gates import semantics, make_gate, insert_gate
from message_payload_graphs import connect
from generate_auto_respawn_helper_assets import generate as helpers
from generate_auto_respawn_listener_assets import transports as listeners
from generate_auto_respawn_event_assets import transports as events

PROXY, ENDED = "UEPAutoRespawnResetProxy", "UEPAutoRespawnRuntimeEnded"
START, SUBSCRIBED = "UEPAutoRespawnStartResetListener", "UEPAutoRespawnResetSubscribedGate"
RESET, END = "UEPAutoRespawnResetMessageGate", "UEPAutoRespawnEndGate"


def transports(bp, originals, event_transport):
    graph = bp.UbergraphPages[0]
    action, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_AsyncAction_ListenForGameplayMessages"]
    owner_break, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_BreakStruct"
        and node.StructType == ue.find_struct("LyraPlayerResetMessage")]
    end, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "K2_OnEndAbility"]
    parent, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallParentFunction" and str(node.FunctionReference.MemberName) == "K2_OnEndAbility"]
    if "GameplayEvent.Reset" not in action.node_find_pin("Channel").default_value or action.node_find_pin("MatchType").default_value != "ExactMatch":
        raise RuntimeError("original exact native Reset listener differs")
    ignored = set(map(tuple, event_transport["dispatch_transport_endpoints"]))
    for node, output in ((action, "then"), (action, "OnMessageReceived"), (end, "then")):
        target, = node.node_find_pin(output).get_linked_to()
        ignored.update(((node.get_name(), output), (target.owning_node.get_name(), target.name)))
    before = {item.get_name(): semantics(item, names, ignored if item == graph else set()) for item, names in originals}
    old_nodes = {node.get_name() for node in graph.Nodes}
    ue.blueprint_add_member_variable(bp, PROXY, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("AsyncAction_ListenForGameplayMessage")))
    ue.blueprint_add_member_variable(bp, ENDED, EdGraphPinType(PinCategory="bool"))
    make_gate(bp, SUBSCRIBED, None); make_gate(bp, RESET, "OwnerPlayerState", owner_break.node_find_pin("OwnerPlayerState"))
    make_gate(bp, END, None)
    start = graph.graph_add_node(K2Node_CustomEvent); start.CustomFunctionName = START; graph.graph_reconstruct_node(start)
    connect(start, "then", action, "execute")
    ue.compile_blueprint(bp)
    insert_gate(graph, action, "then", getattr(bp.GeneratedClass, SUBSCRIBED))
    destination, = action.node_find_pin("then").get_linked_to()
    action.node_find_pin("then").break_link_to(destination)
    store = graph.graph_add_node_variable_set(PROXY)
    connect(action, "then", store, "execute"); connect(action, "AsyncTaskProxy", store, PROXY)
    store.node_find_pin("then").make_link_to(destination)
    insert_gate(graph, action, "OnMessageReceived", getattr(bp.GeneratedClass, RESET))
    reset_call, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallFunction" and str(node.FunctionReference.MemberName) == RESET]
    connect(owner_break, "OwnerPlayerState", reset_call, "OwnerPlayerState")
    insert_gate(graph, end, "then", getattr(bp.GeneratedClass, END))
    end_call, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallFunction" and str(node.FunctionReference.MemberName) == END]
    condition, = end_call.node_find_pin("ReturnValue").get_linked_to()
    branch = condition.owning_node
    connect(branch, "else", parent, "execute")
    added = [node for node in graph.Nodes if node.get_name() not in old_nodes]
    if len(added) != 8 or len(ignored) != 10: raise RuntimeError("native Reset/end transport footprint differs")
    event_transport["original_graphs"] = before
    event_transport["dispatch_transport_endpoints"] = sorted(ignored)
    return dict(native_listener_node_reused=True, native_listener_channel="GameplayEvent.Reset", payload_type="LyraPlayerResetMessage",
        exact_match=True, entry_event=START, gate_functions=[SUBSCRIBED, RESET, END],
        additional_entry_nodes=1, proxy_capture_nodes=1, additional_dispatch_nodes=6, additional_gate_body_nodes=6,
        reflected_proxy_property=PROXY, reflected_ended_property=ENDED, native_parent_end_forwarding_preserved=True,
        original_graphs=before, dispatch_transport_endpoints=sorted(ignored))


def generate(stage, default_profile="Python"):
    return helpers(stage, listener_transports=listeners, event_transports=events,
        activation_transports=transports, default_profile=default_profile)
