"""Keep original latent nodes; add native entries and explicit continuation gates."""
import unreal_engine as ue
from unreal_engine.classes import K2Node_CustomEvent
from mixin_graph_gates import semantics, make_gate, insert_gate
from message_payload_graphs import connect
from generate_auto_respawn_helper_assets import generate as helpers
from generate_auto_respawn_listener_assets import transports as listeners

START_LONG, START_SHORT = "UEPAutoRespawnStartDeathDelay", "UEPAutoRespawnStartRestartDelay"
AFTER_LONG, AFTER_SHORT = "UEPAutoRespawnAfterDeathDelay", "UEPAutoRespawnAfterRestartDelay"


def transports(bp, originals):
    graph = bp.UbergraphPages[0]
    delays = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallFunction"
        and str(node.FunctionReference.MemberName) == "Delay"]
    if len(delays) != 2: raise RuntimeError("exactly two original native AutoRespawn Delay nodes required")
    long, = [node for node in delays if node.node_find_pin("Duration").get_linked_to()]
    short, = [node for node in delays if not node.node_find_pin("Duration").get_linked_to()]
    if float(short.node_find_pin("Duration").default_value) != .1: raise RuntimeError("original next-frame delay changed")
    ignored = set()
    for node in (long, short):
        target, = node.node_find_pin("then").get_linked_to()
        ignored.update(((node.get_name(), "then"), (target.owning_node.get_name(), target.name)))
    before = {item.get_name(): semantics(item, names, ignored if item == graph else set()) for item, names in originals}
    old_nodes = {node.get_name() for node in graph.Nodes}
    for entry_name, delay, gate in ((START_LONG, long, AFTER_LONG), (START_SHORT, short, AFTER_SHORT)):
        event = graph.graph_add_node(K2Node_CustomEvent)
        event.CustomFunctionName = entry_name; graph.graph_reconstruct_node(event)
        connect(event, "then", delay, "execute")
        make_gate(bp, gate, None)
    ue.compile_blueprint(bp)
    for delay, gate in ((long, AFTER_LONG), (short, AFTER_SHORT)):
        insert_gate(graph, delay, "then", getattr(bp.GeneratedClass, gate))
    added = [node for node in graph.Nodes if node.get_name() not in old_nodes]
    if len(added) != 6: raise RuntimeError("two native entries and four continuation dispatch nodes required")
    return dict(original_graphs=before, dispatch_graph=graph.get_name(), dispatch_transport_endpoints=sorted(ignored),
        original_delay_nodes=[long.get_name(), short.get_name()], native_delay_nodes_reused=2,
        entry_events=[START_LONG, START_SHORT], gate_functions=[AFTER_LONG, AFTER_SHORT],
        native_entry_nodes=2, continuation_dispatch_nodes=4, gate_function_nodes=4)


def generate(stage): return helpers(stage, listener_transports=listeners, event_transports=transports)
