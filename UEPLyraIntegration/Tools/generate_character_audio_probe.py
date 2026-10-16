"""Stage-only second BP caller: original typed Interface messages, no business."""
import hashlib
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_Message, K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect

PATH = "/Game/UEPValidation/BP_CharacterAudioInterfaceProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterAudioInterfaceProbe.uasset"
NOTIFY = "Content/Audio/Sounds/Emotes/ANS_EmoteSound.uasset"


def generate(stage, official):
    original, staged = official/NOTIFY, stage/NOTIFY
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256(staged.read_bytes()).hexdigest() != digest: raise RuntimeError("original animation notify changed")
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh stage-only Character audio caller required")
    source = ue.load_object(Blueprint, "/Game/Audio/Sounds/Emotes/ANS_EmoteSound.ANS_EmoteSound")
    references = {str(node.FunctionReference.MemberName): node.FunctionReference
        for graph in source.FunctionGraphs for node in graph.Nodes if node.get_class().get_name() == "K2Node_Message"}
    if not {"GetEmoteAudioComponent", "SetEmoteAudioComponent"}.issubset(references): raise RuntimeError("original Interface message references missing")
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    rows = []
    for name, method in (("Read", "GetEmoteAudioComponent"), ("Write", "SetEmoteAudioComponent")):
        graph = ue.blueprint_add_function(bp, name); entry = graph.Nodes[0]
        entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("Actor")), "CharacterRef")
        if name == "Write": entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("AudioComponent")), "AudioComponent")
        message = graph.graph_add_node(K2Node_Message); message.FunctionReference = references[method]; graph.graph_reconstruct_node(message)
        result = graph.graph_add_node(K2Node_FunctionResult)
        if name == "Read": result.node_create_pin(0, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("AudioComponent")), "AudioComponent")
        connect(entry, "then", message, "execute"); connect(entry, "CharacterRef", message, "self"); connect(message, "then", result, "execute")
        connect(message, "AudioComponent", result, "AudioComponent") if name == "Read" else connect(entry, "AudioComponent", message, "AudioComponent")
        if len(graph.Nodes) != 3: raise RuntimeError("Interface transport node footprint differs")
        rows.append(dict(function=name, message=method, nodes=3))
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("Character Interface probe compile failed")
    bp.save_package()
    if hashlib.sha256(staged.read_bytes()).hexdigest() != digest or hashlib.sha256(original.read_bytes()).hexdigest() != digest:
        raise RuntimeError("retained animation notify modified")
    return dict(stage_only=True, gameplay_business=False, functions=rows, original_animation_notify_unchanged=True,
        asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest(),
        reference_hashes={str(original): digest, str(staged): digest})
