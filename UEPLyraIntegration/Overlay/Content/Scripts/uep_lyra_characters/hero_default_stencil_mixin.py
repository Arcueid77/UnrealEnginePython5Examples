"""Direct Hero parent stencil policy; existing child-owned routers stay separate."""
from .stencil_mixin import LyraCharacterStencilPythonProfile,LyraCharacterStencilBlueprintFallbackProfile
CLASS='/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default_C'
SELECTOR='UEPHeroDefaultMixinProfile'
class LyraHeroDefaultStencilPythonProfile:
    UpdateCustomStencilFromTeamID=LyraCharacterStencilPythonProfile.__dict__['UpdateCustomStencilFromTeamID']
class LyraHeroDefaultStencilBlueprintFallbackProfile:
    UpdateCustomStencilFromTeamID=LyraCharacterStencilBlueprintFallbackProfile.__dict__['UpdateCustomStencilFromTeamID']
