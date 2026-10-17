"""Original per-call factory -> exact named native delegate -> activation."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .team_observer_mixin import LyraCharacterTeamObserverPythonProfile as ObserverPython, LyraCharacterTeamObserverBlueprintFallbackProfile as ObserverBlueprint

BIND = "UEPBindCharacterTeamObserver"


def evidence(actor):
    value = getattr(actor, "_uep_character_team_listener", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, factories=0, binds=0, activations=0, null_factories=0)
        actor._uep_character_team_listener = value
    return value


class LyraCharacterTeamListenerPythonProfile:
    ClearInventory = ObserverPython.ClearInventory
    GetEmoteAudioComponent = ObserverPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = ObserverPython.SetEmoteAudioComponent
    ChangeQuickbarSlot = ObserverPython.ChangeQuickbarSlot
    AddInitialInventory = ObserverPython.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = ObserverPython.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = ObserverPython.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = ObserverPython.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = ObserverPython.K2_OnDeathFinished
    K2_OnReset = ObserverPython.K2_OnReset
    PythonCharacterPartsChanged = ObserverPython.PythonCharacterPartsChanged
    PythonHealthChanged = ObserverPython.PythonHealthChanged
    PythonQuickSlotZero = ObserverPython.__dict__["PythonQuickSlotZero"]
    PythonQuickSlotOne = ObserverPython.__dict__["PythonQuickSlotOne"]
    PythonQuickSlotTwo = ObserverPython.__dict__["PythonQuickSlotTwo"]
    PythonQuickSlotBackward = ObserverPython.__dict__["PythonQuickSlotBackward"]
    PythonQuickSlotForward = ObserverPython.__dict__["PythonQuickSlotForward"]
    PythonObservedTeamChanged = ObserverPython.PythonObservedTeamChanged

    def ListenForTeam(self):
        counts = evidence(self); counts["python_calls"] += 1
        proxy = ue.find_class("AsyncAction_ObserveTeamColors").get_cdo().call_function("ObserveTeamColors", self)
        if not valid(proxy):
            counts["null_factories"] += 1
            return
        counts["factories"] += 1
        # Multicast binding stays an exact native (Actor, UFunction) reference.
        # No persistent Python callback, proxy root, cancellation or deduplication.
        self.call_function(BIND, proxy); counts["binds"] += 1
        proxy.call_function("Activate"); counts["activations"] += 1


class LyraCharacterTeamListenerBlueprintFallbackProfile:
    ClearInventory = ObserverBlueprint.ClearInventory
    GetEmoteAudioComponent = ObserverBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = ObserverBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = ObserverBlueprint.ChangeQuickbarSlot
    AddInitialInventory = ObserverBlueprint.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = ObserverBlueprint.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = ObserverBlueprint.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = ObserverBlueprint.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = ObserverBlueprint.K2_OnDeathFinished
    K2_OnReset = ObserverBlueprint.K2_OnReset
    PythonCharacterPartsChanged = ObserverBlueprint.PythonCharacterPartsChanged
    PythonHealthChanged = ObserverBlueprint.PythonHealthChanged
    PythonObservedTeamChanged = ObserverBlueprint.PythonObservedTeamChanged

    def ListenForTeam(self):
        evidence(self)["fallback_calls"] += 1
        self.call_mixin_original("ListenForTeam")
