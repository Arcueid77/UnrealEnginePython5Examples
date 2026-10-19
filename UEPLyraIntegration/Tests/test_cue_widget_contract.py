"""Reject missing native descendants, source cache differences and replay claims."""
import copy
import unittest
from uep_lyra_hud.cue_widget_contract import PROFILES,CLASSES,CASES,validate


def report():
    value = dict(status="passed",error=None,native_mode="Standalone",cases=[],manager_cases=[])
    for key in ("full_acceptance","network_acceptance","packaged_runtime","pixels_tested","audio_playback_tested","native_remote_controller_branch_tested","message_widget_business_migrated","cue_manager_callbacks_replayed","health_properties_written"): value[key] = False
    for key in ("all_owned_widgets_removed","all_owned_regular_actors_destroyed","all_owned_cue_actors_recycled","health_unchanged","player_array_restored","base_providers_restored","widget_observer_restored","probe_unrooted","music_dependency_fields_restored","abstract_base_verified_through_concrete_fixture"): value[key] = True
    value["native_end_cue_owner"] = "/Script/GameplayAbilities.GameplayCueNotify_Actor"
    value["native_recycled_cue_actor_states"] = [dict(path="cue-"+str(i),hidden=True,owner_none=True,tick_disabled=True) for i in range(42)]
    for cls in CLASSES:
        for profile in PROFILES:
            for name in CASES:
                seeded = name not in ("local","none"); creates = 2 if name == "repeat-start" else 1
                state = dict(controller_is_local=name != "none",widget_valid=name != "missing-widget",in_viewport=name != "missing-widget",widget_owner_is_local=True)
                value["cases"].append(dict(**{"class":cls},profile=profile,name=name,actual_start_entries=2 if seeded else 1,actual_remove_entries=2,
                    native_event_returns=[False,None,False,False] if seeded else [False,False,False],explicit_second_business_event=seeded,
                    native_looping_sound_slots=1,actual_native_spawn_audio_slots=1,created_widgets=creates,actual_interface_entries=creates if cls == "match" else 0,
                    pre_remove=state,retained_fields_after_removal=True,old_widget_visible_after_removal=name in ("repeat-start","missing-widget"),
                    removed_widget_not_visible=True,same_seed_widget=name in ("foreign","orphan","bot"),interface_payloads=[{"raw":1.}]*(creates if cls == "match" else 0)))
    for cls in ("match","waiting"):
        value["manager_cases"].append(dict(**{"class":cls},selected_profile="Python",actual_manager_start_entries=1,actual_manager_remove_entries=1,
            bp_library_caller=True,native_target_has_no_asc=True,widget_added=True,widget_removed=True,source_cached_reference_preserved=True,borrowed_a_matrix_actor_returned_to_native_pool=True,
            duplicate_add_respected_native_guard=True,native_looping_sound_slots=1,actual_native_spawn_audio_slots=1))
    return value


class CueWidgetContractTests(unittest.TestCase):
    def test_complete_matrix_and_manager_children(self): self.assertEqual(validate(report())["native_matrix_cases"],42)
    def test_native_default_python_manager_dispatch_required(self):
        value = report(); value["manager_cases"][0]["actual_manager_remove_entries"] = 0
        with self.assertRaises(RuntimeError): validate(value)
    def test_each_child_must_have_actual_matrix_evidence(self):
        value = report(); value["cases"] = [r for r in value["cases"] if r["class"] != "waiting"]
        with self.assertRaises(RuntimeError): validate(value)
    def test_none_instigator_must_leave_optional_controller_none(self):
        value = report(); next(r for r in value["cases"] if r["name"] == "none")["pre_remove"]["controller_is_local"] = True
        with self.assertRaises(RuntimeError): validate(value)
    def test_repeated_start_must_preserve_original_old_widget_behavior(self):
        value = report(); next(r for r in value["cases"] if r["name"] == "repeat-start")["old_widget_visible_after_removal"] = False
        with self.assertRaises(RuntimeError): validate(value)
    def test_remove_must_not_clear_source_fields(self):
        value = report(); value["cases"][0]["retained_fields_after_removal"] = False
        with self.assertRaises(RuntimeError): validate(value)
    def test_actual_interface_payloads_must_match_original(self):
        value = report(); row = next(r for r in value["cases"] if r["class"] == "match" and r["profile"] == "Python")
        row["interface_payloads"] = [{"raw":9.}]
        with self.assertRaises(RuntimeError): validate(value)
    def test_unrun_widget_migration_and_remote_network_claims_rejected(self):
        for key in ("message_widget_business_migrated","native_remote_controller_branch_tested","network_acceptance","cue_manager_callbacks_replayed"):
            value = report(); value[key] = True
            with self.subTest(key=key),self.assertRaises(RuntimeError): validate(value)
    def test_observer_and_world_state_restoration_required(self):
        value = report(); value["widget_observer_restored"] = False
        with self.assertRaises(RuntimeError): validate(value)
    def test_actual_native_pool_state_and_roundtrip_are_required(self):
        value = report(); value["native_recycled_cue_actor_states"][0]["hidden"] = False
        with self.assertRaises(RuntimeError): validate(value)
    def test_native_effect_slot_and_duplicate_guard_cannot_be_bypassed(self):
        value = report(); value["cases"][0]["native_looping_sound_slots"] = 0
        with self.assertRaises(RuntimeError): validate(value)
        value = report(); value["manager_cases"][0]["duplicate_add_respected_native_guard"] = False
        with self.assertRaises(RuntimeError): validate(value)
        value = report(); value["manager_cases"][0]["borrowed_a_matrix_actor_returned_to_native_pool"] = False
        with self.assertRaises(RuntimeError): validate(value)
