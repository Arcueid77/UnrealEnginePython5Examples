"""Synthetic report guards only; none of these models certifies native waits."""
import copy
import unittest
import test_character_inventory_ready_contract as ready_models
from uep_lyra_characters.inventory_ready_contract import counts
from uep_lyra_characters.inventory_wait_contract import validate, TRANSITIONS, CLASS, P


def wait(*, stage=0, grants=0, waiting=False):
    return dict(uuids=[11, 22, 33], delay_requests=3 if waiting else 4, resumes=2 if waiting else 4,
        fallback_resumes=0, grant_forwards=grants, pending=[waiting and n == stage for n in range(3)],
        stage_requests=[(3 if waiting else 4) if n == stage else 0 for n in range(3)],
        stage_resumes=[(2 if waiting else 4) if n == stage else 0 for n in range(3)], trace=[])


def transition(scenario):
    name, stage, calls, profile = scenario; py = profile == "Python"; grants = 2 if stage == 0 else 1
    ready = counts(py=calls if py else 0, fallback=0 if py else calls)
    ready[("missing_controller", "missing_inventory", "missing_quickbar")[stage]] = calls if py else 0
    after = copy.deepcopy(ready); after["python_calls" if py else "fallback_calls"] += int(stage == 0)
    before_grants = int(stage > 0 and py)
    idle = dict(uuids=None, delay_requests=0, resumes=0, fallback_resumes=0, grant_forwards=0,
        pending=[False]*3, stage_requests=[0]*3, stage_resumes=[0]*3, trace=[])
    return dict(name=name, stage=stage, calls=calls, profile=profile, native_character_class=CLASS,
        actor_was_not_rooted=True, components_manipulated_on_test_owned_controller_only=True,
        native_checkpoint_really_missing_before_release=True, no_grant_before_native_readiness=True,
        native_readiness_released=True, owned_new_pawn_destroyed=True, no_late_script_work_after_owned_destruction=True,
        owned_team_observers_collected=True, original_active_proxies_preserved=True, private_inventory_properties_written=False,
        native_pooled_cue_observers=[dict(cue="nativeCue", cue_class="/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C", observer="nativeHandle",
            collected=False, observed_target_was_test_owned=True, inactive=True, unrooted=True, native_cue_field_never_written=True,
            native_cue_handle_still_matches=True, native_cue_hidden_owner_cleared=True)],
        native_grants=grants, actual_item_definition=P, native_new_item_paths=["fresh"+str(n) for n in range(grants)],
        cleanup=dict(owned_pawn_controller_playerstate_producer_destroyed=True, original_bot_producer_list_preserved=True),
        native_model=dict(items=[P]*grants, slots=[P, None, None], active=0, definition=P,
            equipment_class=P.replace("/ID_", "/B_WeaponInstance_").replace(".ID_", ".B_WeaponInstance_"), stacks=[[P, 1]]*grants),
        before_release_ready=ready, after_ready=after,
        before_release_wait=wait(stage=stage, grants=before_grants, waiting=True) if py else copy.deepcopy(idle),
        after_wait=wait(stage=stage, grants=before_grants+grants) if py else copy.deepcopy(idle))


def report():
    value = ready_models.report()
    value.update(pending_inventory_wait_migrated=True, native_wait_backend="DelayUntilNextTick", python_wait_ticker_registered=False,
        owned_experience_proxies_created=32, native_deferred_transitions_tested=True,
        readiness_transition_cases=[transition(item) for item in TRANSITIONS])
    for row in value["deferred_original_cases"]:
        py = row["profile"] == "Python"; row["readiness_counters"]["original_wait_fallbacks"] = 0
        row["script_wait_quiet_after_destroy"] = True
        row["wait_counters"] = wait(waiting=True) if py else dict(resumes=0, delay_requests=0)
    return value


class CharacterInventoryWaitReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.report)
    def row(self): return self.report["readiness_transition_cases"][5]
    def test_complete_shape_is_not_native_acceptance(self): self.assertTrue(validate(self.report)["readiness_transition_matrix_accepted"])
    def test_smoke_alone_cannot_pass_full_transition_gate(self): self.report["native_deferred_transitions_tested"] = False; self.reject()
    def test_missing_transition_rejected(self): self.report["readiness_transition_cases"].pop(); self.reject()
    def test_no_extra_request_proxy(self): self.report["owned_experience_proxies_created"] += 1; self.reject()
    def test_actual_missing_checkpoint_required(self): self.row()["native_checkpoint_really_missing_before_release"] = False; self.reject()
    def test_test_owned_controller_only(self): self.row()["components_manipulated_on_test_owned_controller_only"] = False; self.reject()
    def test_no_early_grant(self): self.row()["no_grant_before_native_readiness"] = False; self.reject()
    def test_actual_native_readiness_required(self): self.row()["native_readiness_released"] = False; self.reject()
    def test_duplicate_requests_must_coalesce_like_bp(self): self.row()["native_grants"] += 1; self.reject()
    def test_distinct_native_item_identities(self): self.report["readiness_transition_cases"][1]["native_new_item_paths"] = ["same"]*2; self.reject()
    def test_wrong_native_item_model_rejected(self): self.row()["native_model"]["items"] = []; self.reject()
    def test_prior_natural_grant_is_not_counted_as_wait_completion(self):
        self.assertEqual(self.row()["before_release_wait"]["grant_forwards"], 1)
        self.assertTrue(validate(self.report)["readiness_transition_matrix_accepted"])
    def test_wrong_wait_grant_delta_rejected(self): self.row()["after_wait"]["grant_forwards"] += 1; self.reject()
    def test_native_int_stage_must_resume_after_release(self): self.row()["after_wait"]["stage_resumes"][1] = 2; self.reject()
    def test_pending_must_be_cleared(self): self.row()["after_wait"]["pending"][1] = True; self.reject()
    def test_no_original_wait_on_python_path(self): self.row()["after_ready"]["original_wait_fallbacks"] = 1; self.reject()
    def test_no_late_script_work(self): self.row()["no_late_script_work_after_owned_destruction"] = False; self.reject()
    def test_all_owned_team_observers_must_collect(self): self.row()["owned_team_observers_collected"] = False; self.reject()
    def test_original_observers_untouched(self): self.row()["original_active_proxies_preserved"] = False; self.reject()
    def test_native_bot_list_unchanged(self): self.row()["cleanup"]["original_bot_producer_list_preserved"] = False; self.reject()
    def test_no_python_ticker_claim(self): self.report["python_wait_ticker_registered"] = True; self.reject()
    def test_no_direct_inventory_properties(self): self.row()["private_inventory_properties_written"] = True; self.reject()
    def test_owned_proxy_cleanup_required(self): self.report["owned_experience_proxies_collected"] = False; self.reject()
    def test_destroyed_owner_stops_native_resumption(self): self.report["deferred_original_cases"][1]["script_wait_quiet_after_destroy"] = False; self.reject()
    def test_pooled_cue_retention_does_not_claim_collection(self): self.assertFalse(self.row()["native_pooled_cue_observers"][0]["collected"]); validate(self.report)
    def test_active_pooled_cue_observer_rejected(self): self.row()["native_pooled_cue_observers"][0]["inactive"] = False; self.reject()
    def test_unrelated_pooled_cue_cannot_hide_character_leak(self): self.row()["native_pooled_cue_observers"][0]["observed_target_was_test_owned"] = False; self.reject()
    def test_pooled_cue_native_handle_must_match(self): self.row()["native_pooled_cue_observers"][0]["native_cue_handle_still_matches"] = False; self.reject()
    def test_pooled_cue_never_modified_to_force_collection(self): self.row()["native_pooled_cue_observers"][0]["native_cue_field_never_written"] = False; self.reject()
    def test_pooled_cue_must_be_hidden_and_ownerless(self): self.row()["native_pooled_cue_observers"][0]["native_cue_hidden_owner_cleared"] = False; self.reject()
