"""Inherited stencil decisions for the retained Shooter Character only."""
import unreal_engine as ue
from .team_cosmetics_mixin import LyraCharacterTeamPythonProfile as TeamPython, LyraCharacterTeamBlueprintFallbackProfile as TeamBlueprint


def evidence(actor):
    value = getattr(actor, "_uep_character_stencil", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, local_player_zeroes=0, component_queries=0, component_writes=0)
        actor._uep_character_stencil = value
    return value


class LyraCharacterStencilPythonProfile:
    ClearInventory = TeamPython.ClearInventory
    GetEmoteAudioComponent = TeamPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = TeamPython.SetEmoteAudioComponent
    ChangeQuickbarSlot = TeamPython.ChangeQuickbarSlot
    AddInitialInventory = TeamPython.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = TeamPython.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = TeamPython.OnTeamOrCosmeticsChanged

    def UpdateCustomStencilFromTeamID(self, TeamId):
        counts = evidence(self); counts["python_calls"] += 1
        # StencilValue is an original function local, not an Actor property.
        local = bool(self.call_function("IsLocallyControlled"))
        player = bool(self.call_function("IsPlayerControlled"))
        value = 0 if local and player else TeamId
        counts["local_player_zeroes"] += int(local and player)
        components = ue.find_class("LyraSystemStatics").get_cdo().call_function("FindComponentsByClass", self, ue.find_class("PrimitiveComponent"), True)
        counts["component_queries"] += 1
        for component in components:
            # Keep the native setter's clamping/render-state behavior.
            component.call_function("SetCustomDepthStencilValue", value); counts["component_writes"] += 1


class LyraCharacterStencilBlueprintFallbackProfile:
    ClearInventory = TeamBlueprint.ClearInventory
    GetEmoteAudioComponent = TeamBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = TeamBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = TeamBlueprint.ChangeQuickbarSlot
    AddInitialInventory = TeamBlueprint.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = TeamBlueprint.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = TeamBlueprint.OnTeamOrCosmeticsChanged

    def UpdateCustomStencilFromTeamID(self, TeamId):
        evidence(self)["fallback_calls"] += 1
        self.call_mixin_original("UpdateCustomStencilFromTeamID", TeamId)
