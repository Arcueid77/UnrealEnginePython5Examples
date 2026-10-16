"""Stage-only BP reference call to the inherited parent stencil signature."""
import hashlib
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect

PATH = "/Game/UEPValidation/BP_CharacterStencilCallProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterStencilCallProbe.uasset"


def generate(stage, character_class):
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh stage-only stencil probe required")
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    graph = ue.blueprint_add_function(bp, "UpdateStencil"); entry = graph.Nodes[0]
    for name, category, cls in (("CharacterRef", "object", character_class), ("TeamId", "int", None)):
        entry.node_create_pin(1, EdGraphPinType(PinCategory=category, PinSubCategoryObject=cls), name)
    call = graph.graph_add_node_call_function(character_class.UpdateCustomStencilFromTeamID)
    result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "then", call, "execute"); connect(call, "then", result, "execute")
    connect(entry, "CharacterRef", call, "self"); connect(entry, "TeamId", call, "TeamId")
    if len(graph.Nodes) != 3: raise RuntimeError("stencil caller has business nodes")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("stencil caller compile failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, function="UpdateStencil", target="UpdateCustomStencilFromTeamID",
        original_parameters=["TeamId"], typed_actor_reference=True, virtual_bp_function_call=True, nodes=3,
        asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
