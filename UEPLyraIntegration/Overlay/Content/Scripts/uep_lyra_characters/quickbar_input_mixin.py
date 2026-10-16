"""Character slot-input policy only; GAS, QuickBar RPC and equipment stay native."""
import unreal_engine as ue
from unreal_engine.structs import GameplayEventData
from uep_lyra_world.effect_pad_mixin import valid
from .emote_audio_mixin import LyraCharacterAudioPythonProfile as AudioPython, LyraCharacterAudioBlueprintFallbackProfile as AudioBlueprint


def evidence(actor):
    value = getattr(actor, "_uep_character_slot_counts", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, events_sent=0, empty_slot_noops=0,
            invalid_index_noops=0, missing_controller_noops=0, missing_quickbar_noops=0)
        actor._uep_character_slot_counts = value
    return value


class LyraCharacterQuickbarPythonProfile:
    ClearInventory = AudioPython.ClearInventory
    GetEmoteAudioComponent = AudioPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = AudioPython.SetEmoteAudioComponent

    def ChangeQuickbarSlot(self, NewSlotIndex, SlotActionTag):
        counts = evidence(self); counts["python_calls"] += 1
        controller = self.call_function("GetController")
        if not valid(controller): counts["missing_controller_noops"] += 1; return
        quickbar = controller.call_function("GetComponentByClass", ue.find_class("LyraQuickBarComponent"))
        if not valid(quickbar): counts["missing_quickbar_noops"] += 1; return
        slots = quickbar.call_function("GetSlots")
        if not 0 <= NewSlotIndex < len(slots): counts["invalid_index_noops"] += 1; return
        if not valid(slots[NewSlotIndex]): counts["empty_slot_noops"] += 1; return
        # Original MakeStruct leaves all object/tag fields at native defaults.
        # WaitGameplayEvent supplies MatchingTag in its native callback copy.
        payload = GameplayEventData(EventMagnitude=float(NewSlotIndex))
        ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function(
            "SendGameplayEventToActor", self, SlotActionTag, payload)
        counts["events_sent"] += 1


class LyraCharacterQuickbarBlueprintFallbackProfile:
    ClearInventory = AudioBlueprint.ClearInventory
    GetEmoteAudioComponent = AudioBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = AudioBlueprint.SetEmoteAudioComponent

    def ChangeQuickbarSlot(self, NewSlotIndex, SlotActionTag):
        evidence(self)["fallback_calls"] += 1
        self.call_mixin_original("ChangeQuickbarSlot", NewSlotIndex, SlotActionTag)
