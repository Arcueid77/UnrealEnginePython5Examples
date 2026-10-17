"""Stage-only second BP invoking the inherited virtual Character function."""
import hashlib
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect

PATH = "/Game/UEPValidation/BP_CharacterEquipmentHideProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterEquipmentHideProbe.uasset"


def generate(stage, cls):
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh inherited equipment-hide probe required")
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    graph = ue.blueprint_add_function(bp, "Hide"); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=cls), "CharacterRef")
    call = graph.graph_add_node_call_function(cls.HideEquippedWeapons); result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "then", call, "execute"); connect(entry, "CharacterRef", call, "self"); connect(call, "then", result, "execute")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2 or len(graph.Nodes) != 3: raise RuntimeError("inherited equipment-hide probe compile/shape failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, nodes=3, typed_actor_reference=True, virtual_bp_function_call=True,
        target="HideEquippedWeapons", asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
