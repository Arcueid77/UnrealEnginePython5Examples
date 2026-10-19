"""Child continuation decisions on base-owned bindings and retained latent nodes."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from . import music_manager_mixin as controls,music_manager_lifecycle_mixin as lifecycle

DELAY_ENTRY="UEPMusicChildNativeDelay"
CP_ENTRY="UEPMusicControlPointNativeListener"
START="UEPMusicChildStartGate"
AFTER="UEPMusicChildAfterDelayGate"
CAPTURED="UEPMusicControlPointCapturedGate"
METHODS=(*lifecycle.METHODS,START,AFTER,CAPTURED)


def evidence(component):
    value=getattr(component,"_uep_music_family",None)
    if value is None:value=dict(start_python=0,after_python=0,captured_python=0,start_fallback=0,after_fallback=0,captured_fallback=0);component._uep_music_family=value
    return value
def start(component):evidence(component)["start_python"]+=1;component.call_function(DELAY_ENTRY);return False
def after(component,menu,control_point):
    evidence(component)["after_python"]+=1;component.call_function("SetIsMenu",menu)
    if control_point:component.call_function(CP_ENTRY)
    return False
def captured(component,owner_team):
    evidence(component)["captured_python"]+=1
    teams=controls.lib("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem",component,ue.find_class("LyraTeamSubsystem"))
    if not valid(teams):return True
    pawn=controls.lib("GameplayStatics").call_function("GetPlayerPawn",component,0)
    part,team=teams.call_function("FindTeamFromActor",pawn)
    # The original ignores bIsPartOfTeam and compares only TeamId.
    component.call_function("Fire Stinger",int(team)==int(owner_team));return False


class LyraMusicFamilyPythonProfile:
    SetIsMenu=lifecycle.LyraMusicLifecyclePythonProfile.SetIsMenu
    Death=lifecycle.LyraMusicLifecyclePythonProfile.Death
    Fire=lifecycle.LyraMusicLifecyclePythonProfile.Fire
    Stinger=lifecycle.LyraMusicLifecyclePythonProfile.Stinger
    ReceiveTick=lifecycle.LyraMusicLifecyclePythonProfile.ReceiveTick
    ReceiveBeginPlay=lifecycle.LyraMusicLifecyclePythonProfile.ReceiveBeginPlay
    EliminationMessage=lifecycle.LyraMusicLifecyclePythonProfile.EliminationMessage
    DamageMessage=lifecycle.LyraMusicLifecyclePythonProfile.DamageMessage
    def StartChild(self):return start(self)
    StartChild.override=START
    def AfterChild(self,Menu,ControlPoint):return after(self,Menu,ControlPoint)
    AfterChild.override=AFTER
    def Captured(self,OwnerTeamID):return captured(self,OwnerTeamID)
    Captured.override=CAPTURED


class LyraMusicFamilyBlueprintFallbackProfile:
    SetIsMenu=lifecycle.LyraMusicLifecycleBlueprintFallbackProfile.SetIsMenu
    Death=lifecycle.LyraMusicLifecycleBlueprintFallbackProfile.Death
    Fire=lifecycle.LyraMusicLifecycleBlueprintFallbackProfile.Fire
    Stinger=lifecycle.LyraMusicLifecycleBlueprintFallbackProfile.Stinger
    ReceiveTick=lifecycle.LyraMusicLifecycleBlueprintFallbackProfile.ReceiveTick
    ReceiveBeginPlay=lifecycle.LyraMusicLifecycleBlueprintFallbackProfile.ReceiveBeginPlay
    EliminationMessage=lifecycle.LyraMusicLifecycleBlueprintFallbackProfile.EliminationMessage
    DamageMessage=lifecycle.LyraMusicLifecycleBlueprintFallbackProfile.DamageMessage
    def StartChild(self):evidence(self)["start_fallback"]+=1;return True
    StartChild.override=START
    def AfterChild(self,Menu,ControlPoint):evidence(self)["after_fallback"]+=1;return True
    AfterChild.override=AFTER
    def Captured(self,OwnerTeamID):evidence(self)["captured_fallback"]+=1;return True
    Captured.override=CAPTURED
