"""Five original EnhancedInput receiver bodies; engine input dispatch stays native."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from .health_changed_mixin import LyraCharacterHealthChangedPythonProfile as HealthPython, LyraCharacterHealthChangedBlueprintFallbackProfile as HealthBlueprint
from .enhanced_input_contract import ACTIONS
from .enhanced_input_bindings import receiver


def evidence(actor):
    value = getattr(actor, "_uep_character_enhanced_input", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, **dict.fromkeys(ACTIONS, 0))
        actor._uep_character_enhanced_input = value
    return value


def dispatch(actor, action):
    counts = evidence(actor); counts["python_calls"] += 1; counts[action] += 1
    _, _, index, tag = ACTIONS[action]
    actor.call_function("ChangeQuickbarSlot", index, GameplayTag(TagName=tag))


class LyraCharacterEnhancedInputPythonProfile:
    ClearInventory = HealthPython.ClearInventory
    GetEmoteAudioComponent = HealthPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = HealthPython.SetEmoteAudioComponent
    ChangeQuickbarSlot = HealthPython.ChangeQuickbarSlot
    AddInitialInventory = HealthPython.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = HealthPython.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = HealthPython.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = HealthPython.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = HealthPython.K2_OnDeathFinished
    K2_OnReset = HealthPython.K2_OnReset
    PythonCharacterPartsChanged = HealthPython.PythonCharacterPartsChanged
    PythonHealthChanged = HealthPython.PythonHealthChanged

    @receiver("slot-0")
    def PythonQuickSlotZero(self, ActionValue, ElapsedTime: float, TriggeredTime: float, SourceAction): dispatch(self, "slot-0")

    @receiver("slot-1")
    def PythonQuickSlotOne(self, ActionValue, ElapsedTime: float, TriggeredTime: float, SourceAction): dispatch(self, "slot-1")

    @receiver("slot-2")
    def PythonQuickSlotTwo(self, ActionValue, ElapsedTime: float, TriggeredTime: float, SourceAction): dispatch(self, "slot-2")

    @receiver("back")
    def PythonQuickSlotBackward(self, ActionValue, ElapsedTime: float, TriggeredTime: float, SourceAction): dispatch(self, "back")

    @receiver("forward")
    def PythonQuickSlotForward(self, ActionValue, ElapsedTime: float, TriggeredTime: float, SourceAction): dispatch(self, "forward")


class LyraCharacterEnhancedInputBlueprintFallbackProfile:
    # Deliberately omit the five generated input overrides. UEP's native
    # Original dispatch preserves the full FInputActionValue parameter frame;
    # its friendly Python bool/vector conversion has no generic inverse yet.
    ClearInventory = HealthBlueprint.ClearInventory
    GetEmoteAudioComponent = HealthBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = HealthBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = HealthBlueprint.ChangeQuickbarSlot
    AddInitialInventory = HealthBlueprint.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = HealthBlueprint.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = HealthBlueprint.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = HealthBlueprint.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = HealthBlueprint.K2_OnDeathFinished
    K2_OnReset = HealthBlueprint.K2_OnReset
    PythonCharacterPartsChanged = HealthBlueprint.PythonCharacterPartsChanged
    PythonHealthChanged = HealthBlueprint.PythonHealthChanged
