"""Team/cosmetic orchestration only; displays, stencil and device engines remain."""
import unreal_engine as ue
from unreal_engine.structs import ActivateDevicePropertyParams
from uep_lyra_world.effect_pad_mixin import valid
from .outline_mixin import LyraCharacterOutlinePythonProfile as OutlinePython, LyraCharacterOutlineBlueprintFallbackProfile as OutlineBlueprint

DEVICE = "/ShooterCore/Game/B_TeamColor_DeviceProperty.B_TeamColor_DeviceProperty_C"
FALLBACK = (.645833, 0., .568715, 1.)


def evidence(actor):
    value = getattr(actor, "_uep_character_team_cosmetics", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, color_queries=0, outline_calls=0, stencil_calls=0,
            display_applies=0, invalid_platform_noops=0, device_activation_attempts=0, last_call=None)
        actor._uep_character_team_cosmetics = value
    return value


def record(actor, team, display):
    evidence(actor)["last_call"] = dict(team_id=int(team), display_asset=display.get_path_name() if valid(display) else None)


class LyraCharacterTeamPythonProfile:
    ClearInventory = OutlinePython.ClearInventory
    GetEmoteAudioComponent = OutlinePython.GetEmoteAudioComponent
    SetEmoteAudioComponent = OutlinePython.SetEmoteAudioComponent
    ChangeQuickbarSlot = OutlinePython.ChangeQuickbarSlot
    AddInitialInventory = OutlinePython.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = OutlinePython.CreateOrUpdateOutlineIfNeeded

    def OnTeamOrCosmeticsChanged(self, TeamID, TeamDisplayAsset):
        counts = evidence(self); counts["python_calls"] += 1
        display, team = TeamDisplayAsset, TeamID
        record(self, team, display)
        # Preserve the original three-way Sequence: color/outline/stencil,
        # optional display application (including child actors), then devices.
        color = ue.find_class("LyraTeamStatics").get_cdo().call_function("GetTeamColorWithFallback", display, "TeamColor", ue.FLinearColor(*FALLBACK))
        counts["color_queries"] += 1
        self.call_function("CreateOrUpdateOutlineIfNeeded", team, color); counts["outline_calls"] += 1
        self.call_function("UpdateCustomStencilFromTeamID", team); counts["stencil_calls"] += 1
        if valid(display):
            display.call_function("ApplyToActor", self, True); counts["display_applies"] += 1
        user = self.call_function("GetPlatformUserId")
        if not ue.find_class("InputDeviceLibrary").get_cdo().call_function("IsValidPlatformId", user):
            counts["invalid_platform_noops"] += 1; return
        devices = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetEngineSubsystem", ue.find_class("InputDeviceSubsystem"))
        # Native struct defaults retain invalid DeviceId and all three false
        # flags. The original BP discards the native scheduler-owned handle.
        devices.call_function("ActivateDevicePropertyOfClass", ue.load_class(DEVICE), ActivateDevicePropertyParams(UserId=user))
        counts["device_activation_attempts"] += 1


class LyraCharacterTeamBlueprintFallbackProfile:
    ClearInventory = OutlineBlueprint.ClearInventory
    GetEmoteAudioComponent = OutlineBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = OutlineBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = OutlineBlueprint.ChangeQuickbarSlot
    AddInitialInventory = OutlineBlueprint.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = OutlineBlueprint.CreateOrUpdateOutlineIfNeeded

    def OnTeamOrCosmeticsChanged(self, TeamID, TeamDisplayAsset):
        evidence(self)["fallback_calls"] += 1
        record(self, TeamID, TeamDisplayAsset)
        self.call_mixin_original("OnTeamOrCosmeticsChanged", TeamID, TeamDisplayAsset)
