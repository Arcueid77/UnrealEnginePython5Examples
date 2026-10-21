"""Parent stencil/hide/ragdoll policies; animation and Chaos remain native."""
from .hero_default_equipment_mixin import LyraHeroDefaultEquipmentPythonProfile,LyraHeroDefaultEquipmentBlueprintFallbackProfile,CLASS,SELECTOR
from .ragdoll_mixin import LyraCharacterRagdollPythonProfile,LyraCharacterRagdollBlueprintFallbackProfile
class LyraHeroDefaultRagdollPythonProfile:
    UpdateCustomStencilFromTeamID=LyraHeroDefaultEquipmentPythonProfile.__dict__['UpdateCustomStencilFromTeamID']
    HideEquippedWeapons=LyraHeroDefaultEquipmentPythonProfile.__dict__['HideEquippedWeapons']
    Ragdoll=LyraCharacterRagdollPythonProfile.__dict__['Ragdoll']
class LyraHeroDefaultRagdollBlueprintFallbackProfile:
    UpdateCustomStencilFromTeamID=LyraHeroDefaultEquipmentBlueprintFallbackProfile.__dict__['UpdateCustomStencilFromTeamID']
    HideEquippedWeapons=LyraHeroDefaultEquipmentBlueprintFallbackProfile.__dict__['HideEquippedWeapons']
    Ragdoll=LyraCharacterRagdollBlueprintFallbackProfile.__dict__['Ragdoll']
