"""Only immediately-ready continuation; deferred original BP waits stay native."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .legacy_player_info_mixin import LyraCharacterLegacyPlayerInfoPythonProfile as LegacyPython, LyraCharacterLegacyPlayerInfoBlueprintFallbackProfile as LegacyBlueprint

READY = "OnReady_252DE88843B2BB430BD2FBA7ABD46447"


def evidence(actor):
    value = getattr(actor, "_uep_character_inventory_ready", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, immediate_grants=0, original_wait_fallbacks=0,
            missing_controller=0, missing_inventory=0, missing_quickbar=0)
        actor._uep_character_inventory_ready = value
    return value


def missing(actor):
    controller = actor.call_function("GetController")
    if not valid(controller): return "missing_controller"
    inventory = controller.call_function("GetComponentByClass", ue.find_class("LyraInventoryManagerComponent"))
    if not valid(inventory): return "missing_inventory"
    quickbar = controller.call_function("GetComponentByClass", ue.find_class("LyraQuickBarComponent"))
    if not valid(quickbar): return "missing_quickbar"
    return None


class LyraCharacterInventoryReadyPythonProfile:
    def PythonExperienceReady(self):
        counts = evidence(self); counts["python_calls"] += 1
        reason = missing(self)
        if reason is not None:
            counts[reason] += 1; counts["original_wait_fallbacks"] += 1
            self.call_mixin_original(READY)
        else:
            self.call_function("AddInitialInventory"); counts["immediate_grants"] += 1

    PythonExperienceReady.override = READY


class LyraCharacterInventoryReadyBlueprintFallbackProfile:
    def PythonExperienceReady(self):
        evidence(self)["fallback_calls"] += 1
        self.call_mixin_original(READY)

    PythonExperienceReady.override = READY


for profile, parent in ((LyraCharacterInventoryReadyPythonProfile, LegacyPython),
                        (LyraCharacterInventoryReadyBlueprintFallbackProfile, LegacyBlueprint)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__"):
            setattr(profile, name, method)
