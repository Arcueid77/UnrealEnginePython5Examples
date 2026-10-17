"""Original BeginPlay order; Engine, parent and named native delegates remain."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from . import visibility_mixin as visibility

PARENT = "UEPCharacterParentBeginPlay"


def evidence(actor):
    value = getattr(actor, "_uep_character_begin_play", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, parent_calls=0, listen_calls=0, hide_calls=0, register_calls=0, order=[])
        actor._uep_character_begin_play = value
    return value


class LyraCharacterBeginPlayPythonProfile:
    def ReceiveBeginPlay(self):
        counts = evidence(self); counts["python_calls"] += 1
        self.call_function(PARENT); counts["parent_calls"] += 1; counts["order"].append("parent")
        self.call_function("ListenForTeam"); counts["listen_calls"] += 1; counts["order"].append("listen")
        self.call_function("SetActorHiddenInGame", True); counts["hide_calls"] += 1; counts["order"].append("hide")
        self.call_function(visibility.REGISTER, self.get_property("PawnExtComponent"), GameplayTag(TagName="InitState.GameplayReady"), True)
        counts["register_calls"] += 1; counts["order"].append("register")


class LyraCharacterBeginPlayBlueprintFallbackProfile:
    def ReceiveBeginPlay(self):
        evidence(self)["fallback_calls"] += 1; self.call_mixin_original("ReceiveBeginPlay")


for profile, parent in ((LyraCharacterBeginPlayPythonProfile, visibility.LyraCharacterVisibilityPythonProfile),
                        (LyraCharacterBeginPlayBlueprintFallbackProfile, visibility.LyraCharacterVisibilityBlueprintFallbackProfile)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__"): setattr(profile, name, method)
