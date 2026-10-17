"""Stage-only typed call to retained generated ExperienceReady continuation."""
import hashlib
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult, K2Node_AddDelegate, K2Node_CreateDelegate, K2Node_Self
from unreal_engine.structs import EdGraphPinType, MemberReference
from message_payload_graphs import connect
from uep_lyra_characters.inventory_ready_mixin import READY

PATH = "/Game/UEPValidation/BP_CharacterInventoryReadyProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterInventoryReadyProbe.uasset"
BIND = "UEPBindCharacterExperienceReady"


def transport(bp):
    graph = ue.blueprint_add_function(bp, BIND); entry = graph.Nodes[0]
    cls = ue.find_class("AsyncAction_ExperienceReady")
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=cls), "Observer")
    call = graph.graph_add_node(K2Node_AddDelegate)
    call.DelegateReference = MemberReference(MemberName="OnReady", MemberParent=cls, bSelfContext=False)
    graph.graph_reconstruct_node(call)
    delegate, owner = graph.graph_add_node(K2Node_CreateDelegate), graph.graph_add_node(K2Node_Self)
    connect(entry, "Observer", call, "self"); connect(entry, "then", call, "execute")
    connect(owner, "self", delegate, "self"); connect(delegate, "OutputDelegate", call, "Delegate")
    delegate.SelectedFunctionName = READY
    if len(graph.Nodes) != 4: raise RuntimeError("Experience named-delegate transport contains business")
    return dict(function=BIND, nodes=4, delegate="OnReady", callback=READY, gameplay_business=False, operation="add_unique")


def generate(stage, character_class):
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh inventory-ready typed caller required")
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    graph = ue.blueprint_add_function(bp, "Grant"); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=character_class), "CharacterRef")
    cls = ue.find_class("AsyncAction_ExperienceReady")
    factory = graph.graph_add_node_call_function(cls.WaitForExperienceReady)
    bind = graph.graph_add_node_call_function(getattr(character_class, BIND))
    activate = graph.graph_add_node_call_function(cls.Activate); result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "then", factory, "execute"); connect(entry, "CharacterRef", factory, "WorldContextObject")
    connect(factory, "then", bind, "execute"); connect(entry, "CharacterRef", bind, "self"); connect(factory, "ReturnValue", bind, "Observer")
    connect(bind, "then", activate, "execute"); connect(factory, "ReturnValue", activate, "self"); connect(activate, "then", result, "execute")
    if len(graph.Nodes) != 5: raise RuntimeError("inventory-ready factory caller has business nodes")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("inventory-ready typed caller compile failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, function="Grant", target=READY, typed_actor_reference=True,
        virtual_bp_function_call=True, nodes=5, actual_native_experience_factory=True, callback_directly_invoked=False,
        asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
