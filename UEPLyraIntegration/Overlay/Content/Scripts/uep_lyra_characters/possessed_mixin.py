"""Authority -> actual Experience factory -> named delegate -> activation."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from . import inventory_wait_mixin as wait

BIND = "UEPBindCharacterExperienceReady"


def evidence(actor):
    value = getattr(actor, "_uep_character_possessed", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, authority_noops=0, factories=0,
            binds=0, activations=0, null_factories=0, last_controller=None, last_proxy=None)
        actor._uep_character_possessed = value
    return value


class LyraCharacterPossessedPythonProfile:
    def ReceivePossessed(self, NewController):
        counts = evidence(self); counts["python_calls"] += 1
        counts["last_controller"] = NewController.get_path_name() if valid(NewController) else None
        if not self.call_function("HasAuthority"):
            counts["authority_noops"] += 1; return
        # NewController is intentionally not a gate: the original ignores it.
        proxy = ue.find_class("AsyncAction_ExperienceReady").get_cdo().call_function("WaitForExperienceReady", self)
        if not valid(proxy): counts["null_factories"] += 1; return
        counts["factories"] += 1; counts["last_proxy"] = proxy.get_path_name()
        self.call_function(BIND, proxy); counts["binds"] += 1
        proxy.call_function("Activate"); counts["activations"] += 1


class LyraCharacterPossessedBlueprintFallbackProfile:
    def ReceivePossessed(self, NewController):
        counts = evidence(self); counts["fallback_calls"] += 1
        counts["last_controller"] = NewController.get_path_name() if valid(NewController) else None
        self.call_mixin_original("ReceivePossessed", NewController)


for profile, parent in ((LyraCharacterPossessedPythonProfile, wait.LyraCharacterInventoryWaitPythonProfile),
                        (LyraCharacterPossessedBlueprintFallbackProfile, wait.LyraCharacterInventoryWaitBlueprintFallbackProfile)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__"): setattr(profile, name, method)
