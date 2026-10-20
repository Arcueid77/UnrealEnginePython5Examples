"""Explorer appearance helpers with the original renamed outline cache field."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .explorer_helpers_mixin import LyraExplorerHelpersPythonProfile as HelpersPython,LyraExplorerHelpersBlueprintFallbackProfile as HelpersFallback,METHODS as HELPER_METHODS
from .team_cosmetics_mixin import LyraCharacterTeamPythonProfile as TeamPython,LyraCharacterTeamBlueprintFallbackProfile as TeamFallback
from .legacy_player_info_mixin import LyraCharacterLegacyPlayerInfoPythonProfile as LegacyPython,LyraCharacterLegacyPlayerInfoBlueprintFallbackProfile as LegacyFallback

FIELD='MPP_outlineMaterial_0'
PARENT='/Game/Effects/Materials/PostProcess/MPP_Outline_Inst.MPP_Outline_Inst'
METHODS=HELPER_METHODS+('CreateOrUpdateOutlineIfNeeded','OnTeamOrCosmeticsChanged','OnRep_PlayerInfo')

def evidence(actor):
    if not hasattr(actor,'_uep_explorer_style'):actor._uep_explorer_style=dict(python_outline=0,fallback_outline=0,nonlocal_noops=0,created=0,blends_added=0,scalar_updates=0,vector_updates=0)
    return actor._uep_explorer_style

class LyraExplorerStylePythonProfile:
    ClearInventory=HelpersPython.ClearInventory
    GetEmoteAudioComponent=HelpersPython.GetEmoteAudioComponent
    SetEmoteAudioComponent=HelpersPython.SetEmoteAudioComponent
    ChangeQuickbarSlot=HelpersPython.ChangeQuickbarSlot
    AddInitialInventory=HelpersPython.AddInitialInventory
    OnTeamOrCosmeticsChanged=TeamPython.OnTeamOrCosmeticsChanged
    OnRep_PlayerInfo=LegacyPython.OnRep_PlayerInfo
    def CreateOrUpdateOutlineIfNeeded(self,TeamID,OutlineColor):
        counts=evidence(self);counts['python_outline']+=1
        if not self.call_function('IsLocallyControlled'):counts['nonlocal_noops']+=1;return
        material=self.get_property(FIELD)
        if not valid(material):
            parent=ue.load_object(ue.find_class('MaterialInterface'),PARENT)
            material=ue.find_class('KismetMaterialLibrary').get_cdo().call_function('CreateDynamicMaterialInstance',self,parent,'None',0)
            if not valid(material):raise RuntimeError('native Explorer outline material creation failed')
            self.set_property(FIELD,material);counts['created']+=1
            self.get_property('CameraComponent').call_function('AddOrUpdateBlendable',material,1.);counts['blends_added']+=1
        material.call_function('SetScalarParameterValue','TeamID',float(TeamID));counts['scalar_updates']+=1
        material.call_function('SetVectorParameterValue','TeamColor',OutlineColor);counts['vector_updates']+=1

class LyraExplorerStyleBlueprintFallbackProfile:
    ClearInventory=HelpersFallback.ClearInventory
    GetEmoteAudioComponent=HelpersFallback.GetEmoteAudioComponent
    SetEmoteAudioComponent=HelpersFallback.SetEmoteAudioComponent
    ChangeQuickbarSlot=HelpersFallback.ChangeQuickbarSlot
    AddInitialInventory=HelpersFallback.AddInitialInventory
    OnTeamOrCosmeticsChanged=TeamFallback.OnTeamOrCosmeticsChanged
    OnRep_PlayerInfo=LegacyFallback.OnRep_PlayerInfo
    def CreateOrUpdateOutlineIfNeeded(self,TeamID,OutlineColor):
        evidence(self)['fallback_outline']+=1;self.call_mixin_original('CreateOrUpdateOutlineIfNeeded',TeamID,OutlineColor)
