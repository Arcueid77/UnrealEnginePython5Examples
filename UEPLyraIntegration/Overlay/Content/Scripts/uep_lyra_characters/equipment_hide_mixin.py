"""Inherited project decisions only; equipment/Actor visibility remain native."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from . import begin_play_mixin as begin


def evidence(actor):
    value = getattr(actor, "_uep_character_equipment_hide", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, missing_manager_noops=0, instances=0, hidden_actors=0, null_actor_noops=0)
        actor._uep_character_equipment_hide = value
    return value


class LyraCharacterEquipmentHidePythonProfile:
    def HideEquippedWeapons(self):
        counts = evidence(self); counts["python_calls"] += 1
        manager = self.call_function("GetComponentByClass", ue.find_class("LyraEquipmentManagerComponent"))
        if not valid(manager): counts["missing_manager_noops"] += 1; return
        for instance in manager.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance")):
            counts["instances"] += 1
            for actor in instance.call_function("GetSpawnedActors"):
                # Blueprint calls on a null object are no-ops. Keep that effect
                # during unresolved native actor-reference replication too.
                if not valid(actor): counts["null_actor_noops"] += 1; continue
                actor.call_function("SetActorHiddenInGame", True); counts["hidden_actors"] += 1


class LyraCharacterEquipmentHideBlueprintFallbackProfile:
    def HideEquippedWeapons(self):
        evidence(self)["fallback_calls"] += 1; self.call_mixin_original("HideEquippedWeapons")


for profile, parent in ((LyraCharacterEquipmentHidePythonProfile, begin.LyraCharacterBeginPlayPythonProfile),
                        (LyraCharacterEquipmentHideBlueprintFallbackProfile, begin.LyraCharacterBeginPlayBlueprintFallbackProfile)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__"): setattr(profile, name, method)
