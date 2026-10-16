"""Character-local outline decisions; material/interface/rendering stay native."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .initial_inventory_mixin import LyraCharacterLoadoutPythonProfile as LoadoutPython, LyraCharacterLoadoutBlueprintFallbackProfile as LoadoutBlueprint

FIELD = "MPP_outlineMaterial"
PARENT = "/Game/Effects/Materials/PostProcess/MPP_Outline_Inst.MPP_Outline_Inst"


def evidence(actor):
    value = getattr(actor, "_uep_character_outline", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, nonlocal_noops=0, materials_created=0,
            blendables_added=0, scalar_updates=0, vector_updates=0)
        actor._uep_character_outline = value
    return value


class LyraCharacterOutlinePythonProfile:
    ClearInventory = LoadoutPython.ClearInventory
    GetEmoteAudioComponent = LoadoutPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = LoadoutPython.SetEmoteAudioComponent
    ChangeQuickbarSlot = LoadoutPython.ChangeQuickbarSlot
    AddInitialInventory = LoadoutPython.AddInitialInventory

    def CreateOrUpdateOutlineIfNeeded(self, TeamID, OutlineColor):
        counts = evidence(self); counts["python_calls"] += 1
        if not self.call_function("IsLocallyControlled"):
            counts["nonlocal_noops"] += 1; return
        material = self.get_property(FIELD)
        if not valid(material):
            parent = ue.load_object(ue.find_class("MaterialInterface"), PARENT)
            material = ue.find_class("KismetMaterialLibrary").get_cdo().call_function("CreateDynamicMaterialInstance", self, parent, "None", 0)
            if not valid(material): raise RuntimeError("native outline material creation failed")
            self.set_property(FIELD, material); counts["materials_created"] += 1
            self.get_property("CameraComponent").call_function("AddOrUpdateBlendable", material, 1.0)
            counts["blendables_added"] += 1
        material.call_function("SetScalarParameterValue", "TeamID", float(TeamID)); counts["scalar_updates"] += 1
        material.call_function("SetVectorParameterValue", "TeamColor", OutlineColor); counts["vector_updates"] += 1


class LyraCharacterOutlineBlueprintFallbackProfile:
    ClearInventory = LoadoutBlueprint.ClearInventory
    GetEmoteAudioComponent = LoadoutBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = LoadoutBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = LoadoutBlueprint.ChangeQuickbarSlot
    AddInitialInventory = LoadoutBlueprint.AddInitialInventory

    def CreateOrUpdateOutlineIfNeeded(self, TeamID, OutlineColor):
        evidence(self)["fallback_calls"] += 1
        self.call_mixin_original("CreateOrUpdateOutlineIfNeeded", TeamID, OutlineColor)
