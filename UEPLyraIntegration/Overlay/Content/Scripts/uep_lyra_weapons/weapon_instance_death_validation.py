"""Actual lethal GAS death plus native Quickbar unequip, never replayed hooks."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities.death_validation import Validation as NativeDeath
from uep_lyra_world.inventory_pad_network_state import capture, services
from uep_lyra_world.effect_pad_mixin import valid
from . import weapon_instance_mixin as equipment, weapon_instance_observation as observation
from .weapon_instance_death_contract import require


class Validation(NativeDeath):
    def __init__(self, result):
        super().__init__(result)
        self.target_path, self.equipment_events, self.equipment_errors = None, [], []
        self.report.update(equipment_observer_profiles_restored=False, equipment_lifecycle_replayed=False,
            equipment_animation_state_written=False, fixture_native_empty_slot_switch=True,
            natural_destroy_unequip_tested=False)

    def attach(self, world, bridge, controller):
        if not super().attach(world, bridge, controller): return False
        if not hasattr(self, "equipment_root"):
            self.equipment_root = ue.load_class(equipment.CLASS)
            owner = self
            def around(handler):
                def observed(instance):
                    watched = instance.get_path_name() == owner.target_path
                    before, counts, profile = None, None, None
                    if watched:
                        try:
                            before = observation.capture(instance, True)
                            counts, profile = equipment.instance_snapshot(instance), str(ue.get_mixin_profile(instance))
                        except Exception: owner.equipment_errors.append(traceback.format_exc())
                    handler(instance)
                    if watched and before is not None:
                        try:
                            after_counts = equipment.instance_snapshot(instance)
                            owner.equipment_events.append(dict(instance=instance.get_path_name(), profile=profile,
                                before=before, after=observation.capture(instance, True),
                                counters={key: after_counts[key]-value for key, value in counts.items()}))
                        except Exception: owner.equipment_errors.append(traceback.format_exc())
                return observed
            for name, cls in (("Python", equipment.LyraWeaponInstancePythonProfile), ("BlueprintFallback", equipment.LyraWeaponInstanceBlueprintFallbackProfile)):
                ue.register_mixin_profile(self.equipment_root, name, type("DeathObservedWeapon"+name, (), dict(
                    K2_OnEquipped=cls.K2_OnEquipped, DetermineCosmeticTags=cls.DetermineCosmeticTags,
                    K2_OnUnequipped=around(cls.K2_OnUnequipped))))
        return capture(controller) is not None

    def begin(self):
        self.inventory_before = copy.deepcopy(capture(self.controller))
        require("ID_Pistol" in self.inventory_before["definition"], "dead equipment fixture requires original pistol")
        _, quickbar = services(self.controller)
        require(not valid(quickbar.call_function("GetSlots")[1]), "do not overwrite a nonempty fixture slot")
        item = quickbar.call_function("GetActiveSlotItem")
        manager = self.pawn.get_component_by_type(ue.find_class("LyraEquipmentManagerComponent"))
        matches = [value for value in manager.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance"))
            if valid(value) and value.call_function("GetInstigator") == item]
        require(len(matches) == 1, "dead equipment source instance is ambiguous")
        instance = matches[0]
        self.target_path, original_profile = instance.get_path_name(), str(ue.get_mixin_profile(instance))
        self.equipment_events = []
        selected = ("BlueprintFallback", "Python")[self.index % 2]
        ue.set_mixin_profile(instance, selected)
        try:
            super().begin()  # Native GE -> HealthSet -> actual Death ability/Cue.
            require(self.health.call_function("IsDeadOrDying"), "native health is not dead/dying")
            quickbar.call_function("SetActiveSlotIndex", 1)
        finally:
            if valid(instance): ue.set_mixin_profile(instance, original_profile)
        require(not self.equipment_errors and len(self.equipment_events) == 1, "dead native equipment callback missing/duplicated")
        self.row["equipment_death"] = dict(profile=selected, events=copy.deepcopy(self.equipment_events),
            source_item_matches=instance.call_function("GetInstigator") == item,
            native_class=instance.get_class().get_path_name(), fixture_profile_restored=str(ue.get_mixin_profile(instance)) == original_profile,
            native_empty_slot=int(quickbar.call_function("GetActiveSlotIndex")) == 1 and not valid(quickbar.call_function("GetActiveSlotItem")))
        self.target_path = None

    def respawn(self):
        pawn = self.controller.get_controlled_pawn()
        if valid(pawn) and pawn.get_path_name() != self.old_pawn:
            snap = self.bridge.call_function("CaptureSnapshot")
            if snap.bHeroInputReady and snap.bHealthReady and snap.Health > 0 and not snap.bDamageImmune:
                _, quickbar = services(self.controller)
                quickbar.call_function("SetActiveSlotIndex", 0)
                current = capture(self.controller)
                if current is None: return
                self.row["equipment_death"]["respawn_inventory_model"] = current
                self.row["equipment_death"]["original_inventory_model"] = self.inventory_before
                self.row["equipment_death"]["respawn_inventory_model_restored"] = current == self.inventory_before
        super().respawn()

    def finish(self, error=None):
        if self.finished: return
        self.target_path = None
        try:
            if hasattr(self, "equipment_root"):
                observation.restore(self.equipment_root)
                self.report["equipment_observer_profiles_restored"] = True
        except Exception: error = (error or "")+traceback.format_exc()
        self.report["equipment_observation_errors"] = list(self.equipment_errors)
        super().finish(error)

    def finalize(self):
        self.report["equipment_policy_shutdown"] = equipment.snapshot()
        super().finalize()


if any(value.startswith("-UEPWeaponInstanceDeathResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPWeaponInstanceDeathResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
