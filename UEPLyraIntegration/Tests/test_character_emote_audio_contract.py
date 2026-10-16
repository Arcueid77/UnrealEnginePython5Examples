"""Reject invented Interface transport/reference/lifetime evidence."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_characters import emote_audio_contract as gate
from uep_lyra_hud.startup import validation_module


def report():
    paths = ("native-component-a", "native-component-b")
    rows = []
    for name, writer, reader, kind in gate.PLAN:
        value = None if kind == "null" else paths[0] if kind == "a" else paths[1]
        rows.append(dict(name=name, writer=writer, reader=reader, kind=kind, field_after_write=value, bp_read_result=value,
            reference_identity_matches=True, native_actor_type_preserved=True, counters=gate.expected_counts(writer, reader)))
    mixed = [dict(primary_profile=a, secondary_profile=b, primary_result=paths[0], secondary_result=paths[1],
        primary_counters=gate.expected_counts(a, a), secondary_counters=gate.expected_counts(b, b), both_native_types_preserved=True)
        for a, b in (("Python", "BlueprintFallback"), ("BlueprintFallback", "Python"))]
    return dict(status="passed", error=None, retained_character_class=gate.CLASS, second_bp_interface_message_caller=True,
        two_native_same_class_actors=True, primary_actor="existing-player", secondary_actor="existing-bot", native_component_paths=paths,
        hardware_sound_verified=False, audio_playback_called_by_fixture=False, animation_notify_modified=False, character_subclass_created=False,
        full_acceptance=False, whole_character_migrated=False, cases=rows, mixed_instances=mixed,
        native_gc=dict(native_collect_garbage_called=True, both_components_valid=True, primary_result=paths[0], secondary_result=paths[1]),
        non_targets=[dict(target="null", result_is_null=True, character_counters_unchanged=True),
            dict(target="non-interface-controller", result_is_null=True, character_counters_unchanged=True)],
        native_components_created=2, native_components_destroyed=2, original_fields_restored=True, original_profiles_restored=True,
        cdo_unchanged=True, inventory_unchanged=True)


class CharacterAudioReportModels(unittest.TestCase):
    def test_bounded_software_shape(self): self.assertEqual(gate.validate(report())["cases"], 12)

    def test_every_original_python_null_object_repeat_replace_cross_profile_case_required(self):
        value = report(); value["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_matching_but_wrong_property_and_bp_result_cannot_pass(self):
        value = report(); value["cases"][2].update(field_after_write="wrong", bp_read_result="wrong")
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_selected_profile_exact_dispatch_and_native_reference_identity_required(self):
        for fields in (dict(reference_identity_matches=False), dict(counters=gate.expected_counts("Python", "Python")), dict(native_actor_type_preserved=False)):
            value = report(); value["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_same_class_mixed_instance_profiles_cannot_share_component_or_dispatch(self):
        for fields in (dict(secondary_result="native-component-a"), dict(secondary_profile="Python"), dict(both_native_types_preserved=False)):
            value = report(); value["mixed_instances"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_real_native_gc_and_two_distinct_components_required(self):
        for mutate in (lambda r: r["native_gc"].update(native_collect_garbage_called=False), lambda r: r["native_gc"].update(both_components_valid=False),
            lambda r: r.update(native_component_paths=("same", "same"))):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_interface_non_target_is_a_native_noop_not_an_actor_fallback(self):
        value = report(); value["non_targets"][1]["character_counters_unchanged"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_actual_native_owned_cleanup_and_restoration_required(self):
        for fields in (dict(native_components_destroyed=1), dict(original_fields_restored=False), dict(original_profiles_restored=False),
            dict(cdo_unchanged=False), dict(inventory_unchanged=False)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_no_hardware_animation_or_whole_character_overclaim(self):
        for key in ("hardware_sound_verified", "animation_notify_modified", "character_subclass_created", "whole_character_migrated", "full_acceptance"):
            value = report(); value[key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_startup_is_explicit_and_commandlets_never_start_a_runtime_probe(self):
        self.assertEqual(validation_module(["-UEPCharacterAudioResult=x"]), "uep_lyra_characters.emote_audio_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterAudioResult=x"]))
        self.assertIsNone(validation_module(["-UEPCharacterAudio"]))
