"""Native part lifetime, callback identity and BP/Python visual comparison gate."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_characters import parts_changed_contract as gate
from uep_lyra_hud.startup import validation_module


def report():
    cases = []; properties = 0
    for name, initial, target, switch in gate.PLAN:
        found = user = target == "owner"; query = dict(part_of_team=found, team_id=1 if found else -1, display_asset="display" if found else None)
        case = dict(name=name, initial_profile=initial, target=target, switch=switch, original_parts=[dict(cls="original")],
            native_authority=True, native_team_query=query, platform_user_valid=user, operations=[],
            original_part_entries_and_actor_identities_restored=True, owned_temporary_actors_destroyed=True)
        for index, operation in enumerate(("add", "remove", "remove-again")):
            profile = ("Python" if initial == "BlueprintFallback" else "BlueprintFallback") if switch and index else initial
            py = profile == "Python"; active = index < 2; size = int(active and found and user); properties += size
            stats = dict(python_calls=int(active and py), fallback_calls=int(active and not py), team_queries=int(active and py),
                team_updates=int(active and py and found), no_team_noops=int(active and py and not found))
            case["operations"].append(dict(operation=operation, profile=profile, native_operation_called=True, native_callback_count=int(active), native_delegate_payload_matches=True,
                counters=stats, team_counters=dict(python_calls=int(active and py and found), fallback_calls=int(active and not py and found)),
                last_query=query if py and active else None, native_team_query=query, part_entries=1+int(index == 0), temporary_actors=int(index == 0),
                visual=dict(materials="native"), native_device_properties_created=size, native_scheduler_removed_owned_properties=True,
                native_device_properties=[dict(counters=dict(evaluations=1, valid_controllers=1, colors_written=1, fallback_evaluations=0), color=dict(rgba=[1, 2, 3, 255])) for _ in range(size)]))
        cases.append(case)
    markers = len(gate.PLAN)*6
    return dict(status="passed", retained_character_class=gate.CLASS, natural_startup_python_dispatch=dict(python_calls=2, fallback_calls=0), cases=cases,
        delegate_fixture_shutdown=dict(created=1, closed=1, bindings_created=2, bindings_closed=2, active=0, deliveries=12, errors=[]),
        original_player_visual_camera_profile_cdo_inventory_restored=True, owned_unassigned_actor_destroyed=True, native_observation_markers_removed=True,
        native_observation_markers=markers, device_roots_created=markers+properties, device_roots_released=markers+properties,
        **{key: False for key in ("callback_replayed", "component_delegate_broadcast_by_fixture", "all_parts_removed_by_fixture", "parts_properties_written", "hardware_output_tested", "pixels_verified", "full_acceptance", "whole_character_migrated")})


class CharacterPartsChangedReportModels(unittest.TestCase):
    def test_six_real_native_cycles_eighteen_operations_twelve_callbacks(self):
        value = gate.validate(report()); self.assertEqual((value["native_part_cycles"], value["native_part_operations"], value["native_callback_entries"], value["native_device_properties"]), (6, 18, 12, 8))

    def test_missing_or_reordered_native_cases_fail(self):
        for mutate in (lambda r: r["cases"].pop(), lambda r: r["cases"].reverse()):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_selected_native_receiver_and_nested_team_calls_are_exact(self):
        for fields in (dict(python_calls=0), dict(fallback_calls=1), dict(team_queries=0), dict(team_updates=0)):
            value = report(); value["cases"][1]["operations"][0]["counters"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][1]["operations"][0]["team_counters"]["python_calls"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_remove_again_cannot_manufacture_an_extra_callback(self):
        value = report(); value["cases"][0]["operations"][2]["native_callback_count"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_spawned_actor_and_entry_delta_must_match_real_producer(self):
        for fields in (dict(temporary_actors=0), dict(part_entries=1)):
            value = report(); value["cases"][0]["operations"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_profile_switch_between_add_remove_is_not_optional(self):
        value = report(); value["cases"][2]["operations"][1]["profile"] = "BlueprintFallback"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_unassigned_team_uses_real_noop_not_a_fabricated_color_update(self):
        value = report(); value["cases"][5]["operations"][0]["counters"]["team_updates"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_device_properties_must_actually_evaluate_and_end(self):
        value = report(); value["cases"][0]["operations"][0]["native_device_properties"][0]["counters"]["evaluations"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_two_matching_native_parts_lists_do_not_hide_visual_disagreement(self):
        value = report(); value["cases"][1]["operations"][0]["visual"] = dict(materials="wrong")
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_original_entries_visual_state_owned_actor_and_device_roots_restore(self):
        for fields in (dict(original_player_visual_camera_profile_cdo_inventory_restored=False), dict(owned_unassigned_actor_destroyed=False), dict(device_roots_released=0)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["original_part_entries_and_actor_identities_restored"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_callback_replay_multicast_broadcast_property_writes_and_hardware_claims_rejected(self):
        for key in ("callback_replayed", "component_delegate_broadcast_by_fixture", "all_parts_removed_by_fixture", "parts_properties_written", "hardware_output_tested", "pixels_verified", "full_acceptance", "whole_character_migrated"):
            value = report(); value[key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_explicit_parts_fixture_selector_is_disabled_for_authoring_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterPartsResult=x"]), "uep_lyra_characters.parts_changed_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterPartsResult=x"]))

    def test_independent_delegate_payload_cannot_name_a_foreign_component_owner(self):
        value = report(); value["cases"][0]["operations"][0]["native_delegate_payload_matches"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_independent_multicast_bindings_close_and_real_delivery_counts_match(self):
        for fields in (dict(active=1), dict(bindings_closed=1), dict(deliveries=11)):
            value = report(); value["delegate_fixture_shutdown"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
