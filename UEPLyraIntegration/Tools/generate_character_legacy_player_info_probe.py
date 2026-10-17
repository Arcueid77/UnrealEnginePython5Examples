"""Stage-only typed cross-BP call; no fabricated replication notification."""
import hashlib
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect

PATH = "/Game/UEPValidation/BP_CharacterLegacyPlayerInfoProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterLegacyPlayerInfoProbe.uasset"


def generate(stage, character_class):
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh legacy typed BP caller required")
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    graph = ue.blueprint_add_function(bp, "Refresh"); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=character_class), "CharacterRef")
    call = graph.graph_add_node_call_function(character_class.OnRep_PlayerInfo); result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "then", call, "execute"); connect(entry, "CharacterRef", call, "self"); connect(call, "then", result, "execute")
    if len(graph.Nodes) != 3: raise RuntimeError("legacy caller has business nodes")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("legacy typed BP caller compile failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, function="Refresh", target="OnRep_PlayerInfo", typed_actor_reference=True,
        virtual_bp_function_call=True, nodes=3, real_repnotify_ingress=False, asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
