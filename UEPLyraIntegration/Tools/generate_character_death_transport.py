"""Audit the actual inherited death span; declare only an empty int32 resume."""
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from mixin_graph_gates import semantics
from generate_character_inventory_wait_stub import generate as declare
from uep_lyra_characters.death_started_mixin import BOUND_EVENT, RESUME


def audit():
    parent = ue.load_object(Blueprint, "/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default")
    graph, = [value for value in ue.blueprint_get_all_graphs(parent) if value.get_name() == "EventGraph"]
    event, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_ComponentBoundEvent" and str(node.CustomFunctionName) == BOUND_EVENT]
    if str(event.DelegatePropertyName) != "OnDeathStarted" or str(event.ComponentPropertyName) != "HealthComponent" or event.node_find_pin("OwningActor").get_linked_to():
        raise RuntimeError("original inherited Health death binding/payload use differs")
    current, selected = event, {event.get_name()}
    calls = {}
    for name in ("PlayAnimMontage", "UnregisterFromSense", "Delay", "Ragdoll", "HideEquippedWeapons", "Death"):
        pin, = current.node_find_pin("then").get_linked_to(); current = pin.owning_node
        if current.get_class().get_name() != "K2Node_CallFunction" or str(current.FunctionReference.MemberName) != name:
            raise RuntimeError("original inherited death execution order differs")
        calls[name] = current; selected.add(current.get_name())
    if current.node_find_pin("then").get_linked_to(): raise RuntimeError("original death has extra continuation")
    sight = calls["UnregisterFromSense"].node_find_pin("SenseClass")
    if sight.get_linked_to() or sight.default_object != ue.find_class("AISense_Sight"): raise RuntimeError("original death sense class differs")
    component, = calls["UnregisterFromSense"].node_find_pin("self").get_linked_to()
    if str(component.owning_node.VariableReference.MemberName) != "AIPerceptionStimuliSource": raise RuntimeError("original death sense component differs")
    duration, = calls["Delay"].node_find_pin("Duration").get_linked_to(); random_float = duration.owning_node
    if str(random_float.FunctionReference.MemberName) != "RandomFloatInRange" or random_float.node_find_pin("Min").default_value != "0.100000" or random_float.node_find_pin("Max").default_value != "0.600000":
        raise RuntimeError("original native death delay random bounds differ")
    for pin in ("WorldContextObject", "LatentInfo"):
        if calls["Delay"].node_find_pin(pin).get_linked_to(): raise RuntimeError("original death Delay context/linkage differs")
    montage, = calls["PlayAnimMontage"].node_find_pin("AnimMontage").get_linked_to(); item = montage.owning_node
    if item.get_class().get_name() != "K2Node_GetArrayItem": raise RuntimeError("original death montage array indexing differs")
    array, = item.node_find_pin("Array").get_linked_to()
    index, = item.node_find_pin("Dimension 1").get_linked_to(); random_int = index.owning_node
    if str(array.owning_node.VariableReference.MemberName) != "Death Montages" or str(random_int.FunctionReference.MemberName) != "RandomIntegerInRange" or random_int.node_find_pin("Min").default_value != "0":
        raise RuntimeError("original random montage selection differs")
    maximum, = random_int.node_find_pin("Max").get_linked_to(); subtract = maximum.owning_node
    length, = subtract.node_find_pin("A").get_linked_to(); length = length.owning_node
    length_array, = length.node_find_pin("TargetArray").get_linked_to()
    if str(subtract.FunctionReference.MemberName) != "Subtract_IntInt" or subtract.node_find_pin("B").default_value != "1" or str(length.FunctionReference.MemberName) != "Array_Length" or length_array.owning_node != array.owning_node:
        raise RuntimeError("original montage upper bound is not array length minus one")
    for node in (random_float, component.owning_node, item, array.owning_node, random_int, subtract, length): selected.add(node.get_name())
    if len(selected) != 14: raise RuntimeError("original death reachable node count differs")
    death, = [value for value in ue.blueprint_get_all_graphs(parent) if value.get_name() == "Death"]
    if len(death.Nodes) != 1 or death.Nodes[0].get_class().get_name() != "K2Node_FunctionEntry" or death.Nodes[0].node_find_pin("then").get_linked_to(): raise RuntimeError("original Death endpoint is no longer empty")
    return dict(callback=BOUND_EVENT, delegate="OnDeathStarted", component="HealthComponent", payload_ignored=True,
        order=["montage", "sight", "delay", "ragdoll", "hide", "death"], random_delay=[.1, .6], native_backend="Delay",
        montage_random_index="0..length-1", reachable_nodes=14, empty_death_endpoint_retained=True,
        graph=semantics(graph, selected, set()))


def generate(bp): return declare(bp, RESUME)
