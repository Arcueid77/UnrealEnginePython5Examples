"""Retained Actor BP Interface state only; animation/audio playback stay native."""
from .inventory_clear_mixin import LyraCharacterInventoryPythonProfile as ClearPython, LyraCharacterInventoryBlueprintFallbackProfile as ClearBlueprint

FIELD = "Emote_AudioComponent"


def evidence(actor):
    value = getattr(actor, "_uep_character_audio_counts", None)
    if value is None:
        value = dict(python_gets=0, python_sets=0, fallback_gets=0, fallback_sets=0)
        actor._uep_character_audio_counts = value
    return value


class LyraCharacterAudioPythonProfile:
    ClearInventory = ClearPython.ClearInventory

    def GetEmoteAudioComponent(self):
        evidence(self)["python_gets"] += 1
        return {"AudioComponent": self.get_property(FIELD)}
    GetEmoteAudioComponent.uep_named_outputs = True

    def SetEmoteAudioComponent(self, AudioComponent):
        evidence(self)["python_sets"] += 1
        self.set_property(FIELD, AudioComponent)


class LyraCharacterAudioBlueprintFallbackProfile:
    ClearInventory = ClearBlueprint.ClearInventory

    def GetEmoteAudioComponent(self):
        evidence(self)["fallback_gets"] += 1
        component, = self.call_mixin_original("GetEmoteAudioComponent")
        return {"AudioComponent": component}
    GetEmoteAudioComponent.uep_named_outputs = True

    def SetEmoteAudioComponent(self, AudioComponent):
        evidence(self)["fallback_sets"] += 1
        self.call_mixin_original("SetEmoteAudioComponent", AudioComponent)
