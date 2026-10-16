"""Stage-only typed BP caller of the original loadout UFunction; no business."""
import hashlib
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect

PATH = "/Game/UEPValidation/BP_CharacterLoadoutCallProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterLoadoutCallProbe.uasset"


def generate(stage, character_class):
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh stage-only Character loadout caller required")
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    graph = ue.blueprint_add_function(bp, "Grant"); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=character_class), "CharacterRef")
    call = graph.graph_add_node_call_function(character_class.AddInitialInventory)
    result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "then", call, "execute"); connect(call, "then", result, "execute"); connect(entry, "CharacterRef", call, "self")
    if len(graph.Nodes) != 3: raise RuntimeError("Character loadout transport footprint differs")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("Character loadout caller compile failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, function="Grant", target="AddInitialInventory",
        typed_actor_reference=True, virtual_bp_function_call=True, nodes=3, asset=str(stage/RELATIVE),
        sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
