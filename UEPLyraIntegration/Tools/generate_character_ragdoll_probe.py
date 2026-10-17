"""Stage-only typed virtual BP call, plus exact original Ragdoll graph audit."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from mixin_graph_gates import semantics

PATH = "/Game/UEPValidation/BP_CharacterRagdollProbe"
RELATIVE = "Content/UEPValidation/BP_CharacterRagdollProbe.uasset"
PHYSICS = "/Game/UEPValidation/PA_CharacterRagdollProbe"
PHYSICS_RELATIVE = "Content/UEPValidation/PA_CharacterRagdollProbe.uasset"


def physics_fixture(stage, cls):
    if (stage/PHYSICS_RELATIVE).exists(): raise RuntimeError("fresh quantitative Ragdoll fixture required")
    mesh = cls.get_cdo().get_property("Mesh")
    source = mesh.get_property("PhysicsAssetOverride") or mesh.call_function("GetSkinnedAsset").get_property("PhysicsAsset")
    source_root = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    package = source.get_path_name().split(".")[0]
    if not package.startswith("/Game/"): raise RuntimeError("unexpected original Ragdoll physics asset mount")
    relative = "Content/"+package[len("/Game/"):]+".uasset"
    original_hashes = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (source_root, stage)}
    if len(set(original_hashes.values())) != 1: raise RuntimeError("official/staged original physics asset differs")
    asset = ue.duplicate_asset(source.get_path_name(), PHYSICS, "PA_CharacterRagdollProbe")
    bone = str(cls.get_cdo().get_property("RagdollImpulseBone"))
    body, = [body for body in asset.get_property("SkeletalBodySetups") if str(body.get_property("BoneName")).lower() == bone.lower()]
    if body.get_outer() != asset: raise RuntimeError("fixture body is not a deep copy owned by the new asset")
    asset.set_property("SkeletalBodySetups", [body]); asset.set_property("ConstraintSetup", []); asset.set_property("BoundsBodies", [0])
    asset.post_edit_change(); asset.save_package()
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in original_hashes.items()):
        raise RuntimeError("original physics asset was modified")
    return dict(stage_only=True, gameplay_business=False, original_assets_unmodified=True, bodies=1, constraints=0, bone=bone,
        source=source.get_path_name(), source_hashes=original_hashes, fixture_owned_body=True,
        asset=str(stage/PHYSICS_RELATIVE), sha256=hashlib.sha256((stage/PHYSICS_RELATIVE).read_bytes()).hexdigest())


def audit():
    parent = ue.load_object(Blueprint, "/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default")
    graph, = [value for value in ue.blueprint_get_all_graphs(parent) if value.get_name() == "Ragdoll"]
    calls = {str(node.FunctionReference.MemberName): node for node in graph.Nodes if node.get_class().get_name() in ("K2Node_CallFunction", "K2Node_CommutativeAssociativeBinaryOperator")}
    expected = {"SetCollisionProfileName", "SetAllBodiesBelowSimulatePhysics", "AddImpulse", "GetLastUpdateVelocity", "Normal", "Multiply_VectorFloat", "Add_VectorVector"}
    if set(calls) != expected or len(graph.Nodes) != 14: raise RuntimeError("original inherited Ragdoll node inventory differs")
    entry, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_FunctionEntry"]
    current = entry
    for name in ("SetCollisionProfileName", "SetAllBodiesBelowSimulatePhysics", "AddImpulse"):
        pin, = current.node_find_pin("then").get_linked_to()
        if pin.owning_node != calls[name]: raise RuntimeError("original Ragdoll execution order differs")
        current = calls[name]
    if current.node_find_pin("then").get_linked_to(): raise RuntimeError("original Ragdoll has extra continuation")
    for function, pin, literal in (("SetCollisionProfileName", "InCollisionProfileName", "Ragdoll"), ("SetCollisionProfileName", "bUpdateOverlaps", "true"),
        ("SetAllBodiesBelowSimulatePhysics", "bNewSimulate", "true"), ("SetAllBodiesBelowSimulatePhysics", "bIncludeSelf", "true"), ("AddImpulse", "bVelChange", "true"), ("Normal", "Tolerance", "0.000100")):
        value = calls[function].node_find_pin(pin)
        if value.get_linked_to() or value.default_value != literal: raise RuntimeError("original Ragdoll literal differs: "+function+"/"+pin)
    def source(function, pin, expected_node, output="ReturnValue"):
        linked, = calls[function].node_find_pin(pin).get_linked_to()
        if linked.owning_node != calls[expected_node] or linked.name != output: raise RuntimeError("original Ragdoll impulse dataflow differs")
    source("AddImpulse", "Impulse", "Add_VectorVector")
    source("Add_VectorVector", "A", "GetLastUpdateVelocity")
    source("Add_VectorVector", "B", "Multiply_VectorFloat")
    source("Multiply_VectorFloat", "A", "Normal"); source("Normal", "A", "GetLastUpdateVelocity")
    for function, pin, variable in (("Multiply_VectorFloat", "B", "RagdollImpulseStrength"), ("AddImpulse", "BoneName", "RagdollImpulseBone"), ("SetAllBodiesBelowSimulatePhysics", "InBoneName", "RagdollImpulseBone"), ("GetLastUpdateVelocity", "self", "CharacterMovement"), ("SetCollisionProfileName", "self", "Mesh")):
        linked, = calls[function].node_find_pin(pin).get_linked_to()
        if str(linked.owning_node.VariableReference.MemberName) != variable: raise RuntimeError("original Ragdoll variable source differs")
    return dict(nodes=14, order=["collision", "simulation", "impulse"], normalize_tolerance=.0001, collision_profile="Ragdoll",
        include_self=True, velocity_change=True, impulse_formula="velocity + Normal(velocity, 0.0001) * RagdollImpulseStrength",
        graph=semantics(graph, {node.get_name() for node in graph.Nodes}, set()))


def generate(stage, cls):
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh inherited Ragdoll probe required")
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    graph = ue.blueprint_add_function(bp, "Run"); entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=cls), "CharacterRef")
    call = graph.graph_add_node_call_function(cls.Ragdoll); result = graph.graph_add_node(K2Node_FunctionResult)
    connect(entry, "then", call, "execute"); connect(entry, "CharacterRef", call, "self"); connect(call, "then", result, "execute")
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2 or len(graph.Nodes) != 3: raise RuntimeError("Ragdoll probe compile/shape failed")
    bp.save_package()
    return dict(stage_only=True, gameplay_business=False, nodes=3, typed_actor_reference=True, virtual_bp_function_call=True,
        target="Ragdoll", asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
