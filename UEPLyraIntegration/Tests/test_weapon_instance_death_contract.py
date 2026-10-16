"""Dead-equipment gate negatives; these models are not native death evidence."""
import copy
import unittest
from test_death_contract import report as death_report
from uep_lyra_weapons import weapon_instance_death_contract as gate
from uep_lyra_hud.startup import validation_module


def report():
    value = death_report()
    value.update(equipment_observer_profiles_restored=True, equipment_observation_errors=[],
        fixture_native_empty_slot_switch=True, equipment_lifecycle_replayed=False,
        equipment_animation_state_written=False, natural_destroy_unequip_tested=False,
        equipment_policy_shutdown=dict(errors=[], active_count=0, script_subscriptions_created=0))
    for row in value["cases"]:
        for side, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
            state = dict(dead_or_dying=True, linked_layer="original-native-layer", montage_playing=False)
            counts = dict(equips=0, tag_queries=0, layer_picks=0, layers_linked=0, montage_calls=0,
                unequips=int(side == "python"), dead_unequips_skipped=int(side == "python"), fallback_unequips=int(side == "blueprint"))
            row[side]["equipment_death"] = dict(profile=profile, source_item_matches=True, fixture_profile_restored=True,
                native_empty_slot=True, respawn_inventory_model_restored=True,
                original_inventory_model={"original": True}, respawn_inventory_model={"original": True},
                native_class="/ShooterCore/Weapons/Pistol/B_WeaponInstance_Pistol.B_WeaponInstance_Pistol_C",
                events=[dict(instance="original-native-instance", profile=profile, before=copy.deepcopy(state), after=copy.deepcopy(state), counters=counts)])
    return value


class EquipmentDeathGate(unittest.TestCase):
    def test_complete_death_matrix(self): self.assertEqual(gate.validate(report())["bounded_dead_equipment_pairs"], 5)

    def test_only_explicit_lane_starts(self):
        self.assertEqual(validation_module(["-UEPWeaponInstanceDeathResult=report.json"]), "uep_lyra_weapons.weapon_instance_death_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPWeaponInstanceDeathResult=report.json"]))

    def test_reject_alive_state_changed_animation_and_replayed_hook(self):
        for field, replacement in (("dead_or_dying", False), ("linked_layer", "changed-layer")):
            value = report(); event = value["cases"][0]["python"]["equipment_death"]["events"][0]
            event["after"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["equipment_lifecycle_replayed"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_skip_native_play_or_restore(self):
        for field, replacement in (("dead_unequips_skipped", 0), ("montage_calls", 1)):
            value = report(); value["cases"][0]["python"]["equipment_death"]["events"][0]["counters"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["python"]["equipment_death"]["fixture_profile_restored"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_duplicate_callback_and_missing_observer_restore(self):
        value = report(); events = value["cases"][0]["blueprint"]["equipment_death"]["events"]; events.append(copy.deepcopy(events[0]))
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["equipment_observer_profiles_restored"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
