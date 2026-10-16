"""Stage-only second BP invokes the retained Character's normal virtual function."""
import hashlib
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect

PATH = "/Game/UEPValidation/BP_CharacterQuickbarCallProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterQuickbarCallProbe.uasset"


def generate(stage, character_class):
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh stage-only Character slot caller required")
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    graph = ue.blueprint_add_function(bp, "SelectSlot"); entry = graph.Nodes[0]
    for name, kind, cls in (("CharacterRef", "object", character_class), ("NewSlotIndex", "int", None),
            ("SlotActionTag", "struct", ue.find_struct("GameplayTag"))):
        entry.node_create_pin(1, EdGraphPinType(PinCategory=kind, PinSubCategoryObject=cls), name)
    call = graph.graph_add_node_call_function(character_class.ChangeQuickbarSlot)
    result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "then", call, "execute"); connect(call, "then", result, "execute")
    for source, target in (("CharacterRef", "self"), ("NewSlotIndex", "NewSlotIndex"), ("SlotActionTag", "SlotActionTag")):
        connect(entry, source, call, target)
    if len(graph.Nodes) != 3: raise RuntimeError("Character slot transport footprint differs")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("Character slot caller compile failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, function="SelectSlot", target="ChangeQuickbarSlot",
        typed_actor_reference=True, virtual_bp_function_call=True, nodes=3, asset=str(stage/RELATIVE),
        sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
