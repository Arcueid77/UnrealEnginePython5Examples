"""Stage-only typed BP call to the unchanged original listener creation entry."""
import hashlib
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect

PATH = "/Game/UEPValidation/BP_CharacterTeamListenProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterTeamListenProbe.uasset"


def generate(stage, character_class, reuse=False):
    if (stage/RELATIVE).exists():
        if not reuse: raise RuntimeError("fresh stage-only team listener caller required")
        from unreal_engine.classes import Blueprint
        bp = ue.load_object(Blueprint, PATH+".BP_CharacterTeamListenProbe")
        graph, = [value for value in ue.blueprint_get_all_graphs(bp) if value.get_name() == "Listen"]
        call, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallFunction"]
        if len(graph.Nodes) != 3 or str(call.FunctionReference.MemberName) != "ListenForTeam":
            raise RuntimeError("existing typed listener transport has changed")
        return dict(stage_only=True, gameplay_business=False, function="Listen", target="ListenForTeam", typed_actor_reference=True,
            virtual_bp_function_call=True, nodes=3, asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    graph = ue.blueprint_add_function(bp, "Listen"); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=character_class), "CharacterRef")
    call = graph.graph_add_node_call_function(character_class.ListenForTeam); result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "then", call, "execute"); connect(entry, "CharacterRef", call, "self"); connect(call, "then", result, "execute")
    if len(graph.Nodes) != 3: raise RuntimeError("team listener transport has business nodes")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("typed team listener caller compile failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, function="Listen", target="ListenForTeam", typed_actor_reference=True,
        virtual_bp_function_call=True, nodes=3, asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
