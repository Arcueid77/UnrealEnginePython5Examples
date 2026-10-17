"""Component callback decisions only; native part spawning/replication remain."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .lifecycle_mixin import LyraCharacterLifecyclePythonProfile as LifecyclePython, LyraCharacterLifecycleBlueprintFallbackProfile as LifecycleBlueprint

BOUND_EVENT = "BndEvt__B_Hero_ShooterMannequin_PawnCosmeticsComponent_K2Node_ComponentBoundEvent_2_LyraSpawnedCharacterPartsChanged__DelegateSignature"


def evidence(actor):
    value = getattr(actor, "_uep_character_parts_changed", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, team_queries=0, team_updates=0, no_team_noops=0, last_query=None)
        actor._uep_character_parts_changed = value
    return value


class LyraCharacterPartsChangedPythonProfile:
    ClearInventory = LifecyclePython.ClearInventory
    GetEmoteAudioComponent = LifecyclePython.GetEmoteAudioComponent
    SetEmoteAudioComponent = LifecyclePython.SetEmoteAudioComponent
    ChangeQuickbarSlot = LifecyclePython.ChangeQuickbarSlot
    AddInitialInventory = LifecyclePython.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = LifecyclePython.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = LifecyclePython.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = LifecyclePython.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = LifecyclePython.K2_OnDeathFinished
    K2_OnReset = LifecyclePython.K2_OnReset

    def PythonCharacterPartsChanged(self, ComponentWithChangedParts):
        counts = evidence(self); counts["python_calls"] += 1
        # The original BP ignores the component payload and queries Self.
        found, team, display = ue.find_class("LyraTeamStatics").get_cdo().call_function("FindTeamFromObject", self, False)
        counts["team_queries"] += 1
        counts["last_query"] = dict(part_of_team=bool(found), team_id=int(team), display_asset=display.get_path_name() if valid(display) else None)
        if found:
            self.call_function("OnTeamOrCosmeticsChanged", team, display); counts["team_updates"] += 1
        else: counts["no_team_noops"] += 1

    PythonCharacterPartsChanged.override = BOUND_EVENT


class LyraCharacterPartsChangedBlueprintFallbackProfile:
    ClearInventory = LifecycleBlueprint.ClearInventory
    GetEmoteAudioComponent = LifecycleBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = LifecycleBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = LifecycleBlueprint.ChangeQuickbarSlot
    AddInitialInventory = LifecycleBlueprint.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = LifecycleBlueprint.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = LifecycleBlueprint.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = LifecycleBlueprint.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = LifecycleBlueprint.K2_OnDeathFinished
    K2_OnReset = LifecycleBlueprint.K2_OnReset

    def PythonCharacterPartsChanged(self, ComponentWithChangedParts):
        counts = evidence(self); counts["fallback_calls"] += 1; counts["last_query"] = None
        self.call_mixin_original(BOUND_EVENT, ComponentWithChangedParts)

    PythonCharacterPartsChanged.override = BOUND_EVENT
