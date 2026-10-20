"""Explorer lifecycle and component callbacks with all eight prior helpers."""
from .explorer_style_mixin import LyraExplorerStylePythonProfile as StylePython,LyraExplorerStyleBlueprintFallbackProfile as StyleFallback,METHODS as STYLE_METHODS
from .lifecycle_mixin import LyraCharacterLifecyclePythonProfile as LifePython,LyraCharacterLifecycleBlueprintFallbackProfile as LifeFallback
from .parts_changed_mixin import LyraCharacterPartsChangedPythonProfile as PartsPython,LyraCharacterPartsChangedBlueprintFallbackProfile as PartsFallback,BOUND_EVENT as PARTS_EVENT
from .health_changed_mixin import LyraCharacterHealthChangedPythonProfile as HealthPython,LyraCharacterHealthChangedBlueprintFallbackProfile as HealthFallback,BOUND_EVENT as HEALTH_EVENT

METHODS=STYLE_METHODS+('K2_OnReset','K2_OnDeathFinished',PARTS_EVENT,HEALTH_EVENT)

class LyraExplorerCallbacksPythonProfile:
    K2_OnReset=LifePython.K2_OnReset
    K2_OnDeathFinished=LifePython.K2_OnDeathFinished
    PythonCharacterPartsChanged=PartsPython.PythonCharacterPartsChanged
    PythonHealthChanged=HealthPython.PythonHealthChanged

class LyraExplorerCallbacksBlueprintFallbackProfile:
    K2_OnReset=LifeFallback.K2_OnReset
    K2_OnDeathFinished=LifeFallback.K2_OnDeathFinished
    PythonCharacterPartsChanged=PartsFallback.PythonCharacterPartsChanged
    PythonHealthChanged=HealthFallback.PythonHealthChanged

for cls,parent in ((LyraExplorerCallbacksPythonProfile,StylePython),(LyraExplorerCallbacksBlueprintFallbackProfile,StyleFallback)):
    for name in STYLE_METHODS:setattr(cls,name,vars(parent)[name])
