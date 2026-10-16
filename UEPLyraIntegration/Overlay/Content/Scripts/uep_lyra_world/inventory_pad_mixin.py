"""Inventory pad policy; native inventory, RPC, audio and components retained.

Four parent-owned virtual gates also serve the mesh child's BP entries. A gate
returns RunOriginal=True only in the baseline profile; Python performs the
business and returns False. The original BP blocks remain behind the gates.
No related parent/child mixin routers or automatic fallback after error.
"""
import copy
import unreal_engine as ue
from unreal_engine import FVector, FRotator
from .effect_pad_mixin import valid

CLASS = "/ShooterCore/Blueprint/B_GrantInventory_Pad.B_GrantInventory_Pad_C"
MESH_CLASS = "/ShooterCore/Blueprint/B_GrantInventoryPad_WithMesh.B_GrantInventoryPad_WithMesh_C"
CONSTRUCT = "UEPDispatchInventoryPadConstruction"
OVERLAP = "UEPDispatchInventoryPadOverlap"
MESH_CONSTRUCT = "UEPDispatchInventoryPadMeshConstruction"
MESH_TICK = "UEPDispatchInventoryPadMeshTick"
_stats = {"constructions": 0, "mesh_constructions": 0, "overlaps": 0, "mesh_ticks": 0,
          "non_pawns": 0, "no_controller": 0, "full_slots": 0, "authority_grants": 0,
          "remote_audio": 0, "destroy_requests": 0, "teardowns": 0, "errors": []}


def snapshot():
    return copy.deepcopy(_stats)  # Stateless policy: no actor/widget/listener registry.


def library(name):
    return ue.find_class(name).get_cdo()


def construct(actor):
    fragment = library("LyraInventoryFunctionLibrary").call_function("FindItemDefinitionFragment",
        actor.ItemDefinition, ue.find_class("InventoryFragment_PickupIcon"))
    # Blueprint property reads through a null fragment yield zero/empty values.
    text = fragment.DisplayName if valid(fragment) else library("KismetTextLibrary").call_function("Conv_StringToText", "")
    mesh = fragment.SkeletalMesh if valid(fragment) else None
    color = library("KismetMathLibrary").call_function("Conv_LinearColorToVector", fragment.PadColor) if valid(fragment) else FVector()
    actor.Text.call_function("K2_SetText", text)
    actor.set_property("PickUpMesh", mesh)  # No Editor reconstruction notification.
    actor.Pad.call_function("SetVectorParameterValueOnMaterials", "Color", color)
    _stats["constructions"] += 1


def overlap(actor, other):
    _stats["overlaps"] += 1
    if not valid(other) or not other.is_a(ue.find_class("Pawn")):
        _stats["non_pawns"] += 1
        return
    controller = other.call_function("GetController")
    if not valid(controller):
        _stats["no_controller"] += 1
        return
    if actor.call_function("HasAuthority"):
        quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
        inventory = controller.get_component_by_type(ue.find_class("LyraInventoryManagerComponent"))
        # Preserve K2's null-target return defaults without manufacturing an
        # inventory service. Native acceptance separately records this domain.
        slot = int(quickbar.call_function("GetNextFreeItemSlot")) if valid(quickbar) else 0
        if slot < 0:
            _stats["full_slots"] += 1
            return
        item = inventory.call_function("AddItemDefinition", actor.ItemDefinition, 1) if valid(inventory) else None
        if valid(quickbar):
            quickbar.call_function("AddItemToSlot", slot, item)
            quickbar.call_function("SetActiveSlotIndex", slot)  # Existing native Server RPC.
        _stats["authority_grants"] += 1
        if actor.bDestroyOnPickup:
            actor.call_function("K2_DestroyActor")
            _stats["destroy_requests"] += 1
    else:
        library("GameplayStatics").call_function("PlaySound2D", actor, actor.PickUpSound, 1.0, 1.0, 0.0, None, None, True)
        _stats["remote_audio"] += 1


def guarded(function, actor, *arguments):
    try:
        function(actor, *arguments)
    except Exception as error:
        _stats["errors"].append(str(error))
        raise
    return False  # Do not execute the preserved BP business afterwards.


class LyraInventoryPadPythonProfile:
    def __init__(self):
        pass

    def Construction(self):
        return guarded(construct, self)

    Construction.override = CONSTRUCT

    def Overlap(self, OtherActor):
        return guarded(overlap, self, OtherActor)

    Overlap.override = OVERLAP

    def MeshConstruction(self):
        def apply(actor):
            actor.call_function(CONSTRUCT)
            actor.SkeletalMesh.call_function("SetSkinnedAssetAndUpdate", actor.PickUpMesh, True)
            _stats["mesh_constructions"] += 1
        return guarded(apply, self)

    MeshConstruction.override = MESH_CONSTRUCT

    def MeshTick(self, DeltaSeconds):
        def apply(actor):
            # UEP's legacy positional Rotator API is (roll, pitch, yaw), not
            # Unreal's native constructor order (pitch, yaw, roll).
            # The generic positional API includes the native out-hit slot.
            # Name the later input rather than converting False to FHitResult.
            actor.SkeletalMesh.call_function("K2_AddRelativeRotation", FRotator(0.0, 0.0, float(DeltaSeconds)*25.0),
                                            False, bTeleport=False)
            _stats["mesh_ticks"] += 1
        return guarded(apply, self)

    MeshTick.override = MESH_TICK

    def __uep_mixin_teardown__(self):
        _stats["teardowns"] += 1


class LyraInventoryPadBlueprintFallbackProfile:
    def Construction(self):
        return self.call_mixin_original(CONSTRUCT)

    Construction.override = CONSTRUCT

    def Overlap(self, OtherActor):
        return self.call_mixin_original(OVERLAP, OtherActor)

    Overlap.override = OVERLAP

    def MeshConstruction(self):
        return self.call_mixin_original(MESH_CONSTRUCT)

    MeshConstruction.override = MESH_CONSTRUCT

    def MeshTick(self, DeltaSeconds):
        return self.call_mixin_original(MESH_TICK, DeltaSeconds)

    MeshTick.override = MESH_TICK
