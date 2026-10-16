"""Original native death/Reset events forward once; destruction stays native."""
from .stencil_mixin import LyraCharacterStencilPythonProfile as StencilPython, LyraCharacterStencilBlueprintFallbackProfile as StencilBlueprint


def evidence(actor):
    value = getattr(actor, "_uep_character_lifecycle", None)
    if value is None:
        value = dict(death_python=0, death_fallback=0, reset_python=0, reset_fallback=0, clear_forwards=0, last_event=None)
        actor._uep_character_lifecycle = value
    return value


class LyraCharacterLifecyclePythonProfile:
    ClearInventory = StencilPython.ClearInventory
    GetEmoteAudioComponent = StencilPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = StencilPython.SetEmoteAudioComponent
    ChangeQuickbarSlot = StencilPython.ChangeQuickbarSlot
    AddInitialInventory = StencilPython.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = StencilPython.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = StencilPython.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = StencilPython.UpdateCustomStencilFromTeamID

    def K2_OnDeathFinished(self):
        counts = evidence(self); counts["death_python"] += 1; counts["last_event"] = "K2_OnDeathFinished"
        self.call_function("ClearInventory"); counts["clear_forwards"] += 1

    def K2_OnReset(self):
        counts = evidence(self); counts["reset_python"] += 1; counts["last_event"] = "K2_OnReset"
        self.call_function("ClearInventory"); counts["clear_forwards"] += 1


class LyraCharacterLifecycleBlueprintFallbackProfile:
    ClearInventory = StencilBlueprint.ClearInventory
    GetEmoteAudioComponent = StencilBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = StencilBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = StencilBlueprint.ChangeQuickbarSlot
    AddInitialInventory = StencilBlueprint.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = StencilBlueprint.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = StencilBlueprint.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = StencilBlueprint.UpdateCustomStencilFromTeamID

    def K2_OnDeathFinished(self):
        counts = evidence(self); counts["death_fallback"] += 1; counts["last_event"] = "K2_OnDeathFinished"
        self.call_mixin_original("K2_OnDeathFinished")

    def K2_OnReset(self):
        counts = evidence(self); counts["reset_fallback"] += 1; counts["last_event"] = "K2_OnReset"
        self.call_mixin_original("K2_OnReset")
