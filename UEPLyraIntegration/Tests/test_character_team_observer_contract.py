"""Native factory/proxy/callback/cleanup evidence, not a manually replayed result."""
import copy
import unittest
from uep_lyra_characters.team_observer_contract import CLASS, PLAN, validate


def row(profile, calls, assigned=True, user=True):
    py = profile == "Python"; count = calls*int(assigned and user)
    payload = dict(team_set=assigned, team_id=2 if assigned else -1, display_asset="native-team-display" if assigned else None)
    return dict(profile=profile, typed_bp_listen_calls=calls, native_proxies_created=calls, native_proxies_active_before_cancel=True,
        native_proxies_inactive_after_cancel=True, native_collection_checked_after_engine_ticks=True,
        native_older_current_proxies_collected=True, native_previous_proxy_released_after_next_factory=True,
        native_latest_cancelled_proxy_retained=0, native_retained_proxy_inactive=True,
        counters=dict(python_calls=calls*int(py), fallback_calls=calls*int(not py), team_updates=calls*int(py and assigned), no_team_noops=calls*int(py and not assigned)),
        team_counters=dict(python_calls=calls*int(py and assigned), fallback_calls=calls*int(not py and assigned)),
        payload=payload, native_team_query=copy.deepcopy(payload), native_device_properties_created=count,
        native_device_properties=[dict(color="native-color", counters=dict(evaluations=1, valid_controllers=1, colors_written=1, fallback_evaluations=0)) for _ in range(count)],
        native_scheduler_removed_owned_properties=True, visual=dict(native_visual=True))


def report():
    cases = []
    for name, target, calls, profile in PLAN:
        value = row(profile, calls, target == "owner", target == "owner"); value.update(name=name, target=target, calls=calls); cases.append(value)
    return dict(status="passed", error=None, retained_character_class=CLASS, cases=cases,
        cleanup=dict(original_actor_visual_camera_profiles_restored=True, original_inventory_restored=True, cdo_profile_restored=True, original_active_proxies_preserved=True,
            owned_observers_cancelled_and_deregistered=True, older_owned_proxies_collected=True, owned_bare_actor_startup_proxy_collected=True,
            native_collection_checked_after_engine_ticks=True, native_latest_cancelled_proxies_retained=0,
            native_observation_markers_removed=True, owned_bare_actor_and_startup_proxy_destroyed=True,
            native_observation_markers=16, device_roots_created=22, device_roots_released=22, caller_roots_created=1, caller_roots_released=1),
        **dict.fromkeys(("callback_replayed", "team_properties_written", "observer_delegate_broadcast_by_fixture", "all_native_observers_cancelled", "replicated_team_changes_tested", "listener_factory_orchestration_migrated", "hardware_output_tested", "pixels_verified", "whole_character_migrated", "full_acceptance"), False))


class CharacterTeamObserverReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(self.report)
    def test_complete_model_shape_not_native_acceptance(self): self.assertEqual(validate(self.report)["native_observer_callbacks"], 8)
    def test_no_missing_real_factory_trials(self): self.report["cases"] = []; self.reject()
    def test_python_counts_without_new_native_proxy_rejected(self): self.report["cases"][0]["native_proxies_created"] = 0; self.reject()
    def test_proxy_must_really_register_with_game_instance(self): self.report["cases"][0]["native_proxies_active_before_cancel"] = False; self.reject()
    def test_cancel_does_not_only_mean_called_function(self): self.report["cases"][0]["native_proxies_inactive_after_cancel"] = False; self.reject()
    def test_gc_request_alone_is_not_collection_evidence(self): self.report["cases"][0]["native_collection_checked_after_engine_ticks"] = False; self.reject()
    def test_older_current_proxy_must_collect(self): self.report["cases"][0]["native_older_current_proxies_collected"] = False; self.reject()
    def test_overwritten_factory_return_must_release_previous_proxy(self): self.report["cases"][0]["native_previous_proxy_released_after_next_factory"] = False; self.reject()
    def test_latest_native_factory_return_must_also_collect(self): self.report["cases"][0]["native_latest_cancelled_proxy_retained"] = 1; self.reject()
    def test_retained_native_return_must_be_inactive(self): self.report["cases"][0]["native_retained_proxy_inactive"] = False; self.reject()
    def test_older_owned_proxy_retention_rejected(self): self.report["cleanup"]["older_owned_proxies_collected"] = False; self.reject()
    def test_destroyed_bare_actor_startup_observer_must_collect(self): self.report["cleanup"]["owned_bare_actor_startup_proxy_collected"] = False; self.reject()
    def test_cleanup_must_wait_for_engine_collection(self): self.report["cleanup"]["native_collection_checked_after_engine_ticks"] = False; self.reject()
    def test_final_native_player_return_must_also_collect(self): self.report["cleanup"]["native_latest_cancelled_proxies_retained"] = 1; self.reject()
    def test_callback_payload_matches_independent_native_team_query(self): self.report["cases"][0]["payload"]["team_id"] = 0; self.reject()
    def test_unassigned_result_does_not_invent_virtual_team_update(self): self.report["cases"][-1]["team_counters"]["python_calls"] = 1; self.reject()
    def test_actual_device_scheduler_lifetime_required(self): self.report["cases"][0]["native_scheduler_removed_owned_properties"] = False; self.reject()
    def test_original_bp_python_visual_results_must_match(self): self.report["cases"][1]["visual"] = dict(different=True); self.reject()
    def test_only_fixture_observers_may_be_cancelled(self): self.report["all_native_observers_cancelled"] = True; self.reject()
    def test_original_live_proxy_set_preserved(self): self.report["cleanup"]["original_active_proxies_preserved"] = False; self.reject()
    def test_no_root_or_caller_pin_leak(self): self.report["cleanup"]["device_roots_released"] = 21; self.reject()
    def test_initial_activation_not_certification_of_team_replication(self): self.report["replicated_team_changes_tested"] = True; self.reject()
    def test_original_listener_creation_is_still_bp(self): self.report["listener_factory_orchestration_migrated"] = True; self.reject()
    def test_private_selector_and_commandlet_no_autoquit(self):
        from uep_lyra_hud.startup import validation_module
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterObserverResult=x"]))
        self.assertEqual(validation_module(["-UEPCharacterObserverResult=x"]), "uep_lyra_characters.team_observer_validation")
    def test_cached_cleanup_is_pod_only_after_native_actor_destruction(self):
        import ast
        from pathlib import Path
        import types
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/team_observer_observation.py"
        cls = next(value for value in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(value, ast.ClassDef) and value.name == "Context")
        method = next(value for value in cls.body if isinstance(value, ast.FunctionDef) and value.name == "cleanup")
        namespace = {}; exec(compile(ast.Module(body=[method], type_ignores=[]), str(file), "exec"), namespace)
        expected = dict(cached=True); self.assertIs(namespace["cleanup"](types.SimpleNamespace(closed=True, cleanup_report=expected)), expected)
