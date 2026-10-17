"""Only original ObserveTeamColors result decisions; listener creation remains BP."""
from uep_lyra_world.effect_pad_mixin import valid
from .enhanced_input_mixin import LyraCharacterEnhancedInputPythonProfile as InputPython, LyraCharacterEnhancedInputBlueprintFallbackProfile as InputBlueprint

BOUND_EVENT = "OnTeamChanged_3748935144EB51297FADDCB51CE362DF"


def evidence(actor):
    value = getattr(actor, "_uep_character_team_observer", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, team_updates=0, no_team_noops=0, last_payload=None)
        actor._uep_character_team_observer = value
    return value


def received(actor, assigned, number, display):
    evidence(actor)["last_payload"] = dict(team_set=bool(assigned), team_id=int(number), display_asset=display.get_path_name() if valid(display) else None)


class LyraCharacterTeamObserverPythonProfile:
    ClearInventory = InputPython.ClearInventory
    GetEmoteAudioComponent = InputPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = InputPython.SetEmoteAudioComponent
    ChangeQuickbarSlot = InputPython.ChangeQuickbarSlot
    AddInitialInventory = InputPython.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = InputPython.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = InputPython.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = InputPython.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = InputPython.K2_OnDeathFinished
    K2_OnReset = InputPython.K2_OnReset
    PythonCharacterPartsChanged = InputPython.PythonCharacterPartsChanged
    PythonHealthChanged = InputPython.PythonHealthChanged
    # Preserve descriptors, not the raw functions returned by descriptor access.
    PythonQuickSlotZero = InputPython.__dict__["PythonQuickSlotZero"]
    PythonQuickSlotOne = InputPython.__dict__["PythonQuickSlotOne"]
    PythonQuickSlotTwo = InputPython.__dict__["PythonQuickSlotTwo"]
    PythonQuickSlotBackward = InputPython.__dict__["PythonQuickSlotBackward"]
    PythonQuickSlotForward = InputPython.__dict__["PythonQuickSlotForward"]

    def PythonObservedTeamChanged(self, bTeamSet: bool, TeamId: int, DisplayAsset):
        counts = evidence(self); counts["python_calls"] += 1; received(self, bTeamSet, TeamId, DisplayAsset)
        if bTeamSet:
            self.call_function("OnTeamOrCosmeticsChanged", TeamId, DisplayAsset); counts["team_updates"] += 1
        else: counts["no_team_noops"] += 1

    PythonObservedTeamChanged.override = BOUND_EVENT


class LyraCharacterTeamObserverBlueprintFallbackProfile:
    ClearInventory = InputBlueprint.ClearInventory
    GetEmoteAudioComponent = InputBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = InputBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = InputBlueprint.ChangeQuickbarSlot
    AddInitialInventory = InputBlueprint.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = InputBlueprint.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = InputBlueprint.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = InputBlueprint.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = InputBlueprint.K2_OnDeathFinished
    K2_OnReset = InputBlueprint.K2_OnReset
    PythonCharacterPartsChanged = InputBlueprint.PythonCharacterPartsChanged
    PythonHealthChanged = InputBlueprint.PythonHealthChanged

    def PythonObservedTeamChanged(self, bTeamSet: bool, TeamId: int, DisplayAsset):
        counts = evidence(self); counts["fallback_calls"] += 1; received(self, bTeamSet, TeamId, DisplayAsset)
        self.call_mixin_original(BOUND_EVENT, bTeamSet, TeamId, DisplayAsset)

    PythonObservedTeamChanged.override = BOUND_EVENT
