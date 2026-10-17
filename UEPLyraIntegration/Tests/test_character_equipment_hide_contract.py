"""Synthetic inherited-function report guards, including real-death claims."""
import unittest
import test_character_begin_play_contract as begin_models
from uep_lyra_characters.equipment_hide_contract import validate, SCENARIOS, CLASS


def counts(py, calls=1, instances=1, actors=1, missing=False):
    return dict(python_calls=calls if py else 0, fallback_calls=0 if py else calls, missing_manager_noops=calls if py and missing else 0,
        instances=instances*calls if py else 0, hidden_actors=actors*calls if py else 0, null_actor_noops=0)


def upgrade(value):
    value.update(inherited_equipment_hide_migrated=True, ragdoll_physics_or_animation_migrated=False, equipment_hidden_fields_written_directly=False, equipment_hide_caller_roots=dict(created=1, released=1))
    return value


def report():
    value = upgrade(begin_models.report()); value["equipment_hide_cases"] = []
    value.update(native_ai_isolated_throughout_fixture=True, original_bot_identities_and_health_preserved=True,
        original_bots_before=[dict(controller="native-bot", pawn="original-pawn", health=100)], original_bots_after=[dict(controller="native-bot", pawn="original-pawn", health=100)])
    for name, calls, profile in SCENARIOS:
        empty = name in ("empty", "missing-manager"); py = profile == "Python"
        value["equipment_hide_cases"].append(dict(name=name, calls=calls, profile=profile, actual_character_class=CLASS, callback_manually_replayed=False,
            native_lethal_gas_death=name == "native-death", bp_reference_call=name != "native-death", native_all_spawned_actors_hidden=True,
            actor_was_not_rooted=True, owned_new_pawn_destroyed=True, no_late_script_work_after_owned_destruction=True, owned_team_observers_collected=True,
            original_active_proxies_preserved=True, hide_quiet_after_destroy=True, cleanup=dict(owned_pawn_controller_playerstate_producer_destroyed=True, original_bot_producer_list_preserved=True),
            counters=counts(py, calls, int(not empty), int(not empty), name == "missing-manager"), instances_before=int(not empty), spawned_actor_paths=[] if empty else ["native-weapon"],
            native_health_after=0 if name == "native-death" else None, native_pawn_hidden_unchanged=True, inventory_unchanged_by_hide=True,
            native_pooled_cue_observers=[], native_death_delay_observed=name == "native-death", native_death_elapsed_game_seconds=.3 if name == "native-death" else None,
            original_active_observer_paths=["persistent"], final_active_observer_paths=["persistent"], original_character_observers_preserved=True,
            preexisting_observers_explicitly_cancelled=False, preexisting_native_cue_observers=[]))
    return value


class CharacterEquipmentHideReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.report)
    def test_complete_shape_is_only_model(self): self.assertEqual(validate(self.report)["native_equipment_hide_pairs"], 6)
    def test_real_death_not_manual_callback(self): self.report["equipment_hide_cases"][-1]["callback_manually_replayed"] = True; self.reject()
    def test_native_lethal_health_required(self): self.report["equipment_hide_cases"][-1]["native_health_after"] = 100; self.reject()
    def test_native_death_delay_required(self): self.report["equipment_hide_cases"][-1]["native_death_delay_observed"] = False; self.reject()
    def test_immediate_replayed_death_hide_rejected(self): self.report["equipment_hide_cases"][-1]["native_death_elapsed_game_seconds"] = 0; self.reject()
    def test_unproven_native_pool_ownership_rejected(self):
        row = self.report["equipment_hide_cases"][1]
        row["native_pooled_cue_observers"] = [dict(cue="cue", observer="handle", cue_class="/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C",
            observed_target_was_test_owned=False, inactive=True, unrooted=True, native_cue_field_never_written=True, native_cue_handle_still_matches=True, native_cue_hidden_owner_cleared=True)]
        self.reject()
    def preexisting_cue(self):
        row = self.report["equipment_hide_cases"][1]; row["original_active_observer_paths"].append("native-cue-handle")
        row["original_active_proxies_preserved"] = False
        row["preexisting_native_cue_observers"] = [dict(cue="native-cue", cue_class="/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C", observer="native-cue-handle",
            original_was_active=True, fixture_never_cancels_or_writes=True, final_active=False, collected=True, native_cue_handle_still_matches=False)]
        return row
    def test_exact_preexisting_native_cue_may_naturally_retire(self): self.preexisting_cue(); validate(self.report)
    def test_persistent_character_observer_may_not_retire(self):
        row = self.preexisting_cue(); row["final_active_observer_paths"] = []; self.reject()
    def test_unknown_new_observer_rejected(self): self.report["equipment_hide_cases"][1]["final_active_observer_paths"].append("unknown"); self.reject()
    def test_cannot_invent_preexisting_cue_exemption(self): self.preexisting_cue()["preexisting_native_cue_observers"][0]["observer"] = "not-original"; self.reject()
    def test_preexisting_cue_never_explicitly_cancelled(self): self.preexisting_cue()["preexisting_observers_explicitly_cancelled"] = True; self.reject()
    def test_whole_original_proxy_set_change_reported_honestly(self): self.preexisting_cue()["original_active_proxies_preserved"] = True; self.reject()
    def test_original_bot_may_not_die_and_respawn_during_fixture(self): self.report["original_bots_after"][0]["pawn"] = "replacement"; self.reject()
    def test_original_bot_health_not_written_or_damaged(self): self.report["original_bots_after"][0]["health"] = 50; self.reject()
    def test_ai_isolation_during_all_inherited_fixture_phases_required(self): self.report["native_ai_isolated_throughout_fixture"] = False; self.reject()
    def test_native_spawned_actor_must_hide(self): self.report["equipment_hide_cases"][1]["native_all_spawned_actors_hidden"] = False; self.reject()
    def test_pawn_not_hidden_by_weapon_method(self): self.report["equipment_hide_cases"][1]["native_pawn_hidden_unchanged"] = False; self.reject()
    def test_no_inventory_change(self): self.report["equipment_hide_cases"][1]["inventory_unchanged_by_hide"] = False; self.reject()
    def test_missing_manager_control_required(self): self.report["equipment_hide_cases"][9]["counters"]["missing_manager_noops"] = 0; self.reject()
    def test_no_ragdoll_migration_claim(self): self.report["ragdoll_physics_or_animation_migrated"] = True; self.reject()
    def test_caller_root_released(self): self.report["equipment_hide_caller_roots"]["released"] = 0; self.reject()
    def test_prior_begin_play_regression_still_required(self): self.report["natural_startup_begin_play"]["parent_calls"] = 0; self.reject()
    def test_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterEquipmentHideResult=x"]), "uep_lyra_characters.equipment_hide_validation")
