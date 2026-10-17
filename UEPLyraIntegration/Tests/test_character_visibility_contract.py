"""Native visibility report-shape models do not certify pixels or runtime."""
import copy
import unittest
import test_character_possessed_contract as possession_models
from uep_lyra_characters.visibility_contract import validate, SCENARIOS


def evidence(*, py=True, calls=1, destroyed=False, actor="actor", component="component"):
    return dict(python_calls=calls if py else 0, fallback_calls=0 if py else calls, delay_requests=calls if py else 0,
        resumes=int(py and not destroyed), show_calls=int(py and not destroyed), uuid=111 if py else None,
        pending=py and destroyed, last_payload=dict(actor=actor, feature="PawnExtension", state="InitState.GameplayReady", implementer=component), trace=[])


def upgrade(value):
    value.update(visibility_callback_business_migrated=True, visibility_native_backend="DelayUntilNextTick", visibility_python_ticker_registered=False, visibility_physical_pixels_tested=False)
    return value


def report():
    value = upgrade(possession_models.report())
    value.update(natural_startup_visibility=evidence(), natural_startup_visibility_actor="actor", natural_startup_hidden=False)
    for row in value["readiness_transition_cases"]:
        row.update(visibility_before_destroy=evidence(py=row["profile"] == "Python"), native_hidden_after_spawn=True, native_hidden_before_destroy=False,
            native_visibility_actor_path="actor", inventory_latent_uuids=[222, 333, 444])
    value["visibility_cases"] = []
    for name, calls, profile in SCENARIOS:
        py, destroyed = profile == "Python", name == "destroy-pending"; data = evidence(py=py, calls=calls, destroyed=destroyed)
        value["visibility_cases"].append(dict(name=name, profile=profile, native_registration_calls=calls,
            native_character_class=possession_models.wait_models.CLASS, actual_native_initstate_registration=True, hidden_before_resume=True,
            actor_was_not_rooted=True, owned_new_pawn_destroyed=True, no_late_script_work_after_owned_destruction=True,
            owned_team_observers_collected=True, original_active_proxies_preserved=True, visibility_quiet_after_destroy=True,
            callback_manually_replayed=False, native_hidden_fields_written_directly=False, native_hidden_before_destroy=destroyed,
            cleanup=dict(owned_pawn_controller_playerstate_producer_destroyed=True, original_bot_producer_list_preserved=True),
            payload=data["last_payload"], native_actor_path="actor", native_component_path="component",
            visibility_delta={key: data[key] for key in ("python_calls", "fallback_calls", "delay_requests", "resumes", "show_calls")},
            profile_before_resume=("Python" if profile == "BlueprintFallback" else "BlueprintFallback") if name == "switch-pending" else profile))
    return value


class CharacterVisibilityReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def row(self): return self.report["visibility_cases"][1]
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.report)
    def test_complete_shape_is_a_model(self): self.assertEqual(validate(self.report)["native_visibility_pairs"], 4)
    def test_natural_callback_required(self): self.report["natural_startup_visibility"]["python_calls"] = 0; self.reject()
    def test_actual_natural_show_required(self): self.report["natural_startup_hidden"] = True; self.reject()
    def test_actual_delayed_transition_required(self): self.report["readiness_transition_cases"][1]["native_hidden_before_destroy"] = True; self.reject()
    def test_native_payload_actor_matches(self): self.row()["payload"]["actor"] = "other"; self.reject()
    def test_native_payload_component_matches(self): self.row()["payload"]["implementer"] = "other"; self.reject()
    def test_native_payload_state_matches(self): self.row()["payload"]["state"] = "InitState.Spawned"; self.reject()
    def test_no_manual_callback(self): self.row()["callback_manually_replayed"] = True; self.reject()
    def test_no_early_show(self): self.row()["hidden_before_resume"] = False; self.reject()
    def test_repeated_signal_has_one_continuation(self): self.report["visibility_cases"][3]["visibility_delta"]["show_calls"] = 2; self.reject()
    def test_destroyed_owner_has_no_resume(self): self.report["visibility_cases"][5]["visibility_delta"]["resumes"] = 1; self.reject()
    def test_no_late_visibility_work(self): self.row()["visibility_quiet_after_destroy"] = False; self.reject()
    def test_pending_profile_really_switched(self): self.report["visibility_cases"][7]["profile_before_resume"] = "Python"; self.reject()
    def test_python_delay_keys_do_not_collide(self): self.report["readiness_transition_cases"][1]["inventory_latent_uuids"] = [111]; self.reject()
    def test_no_python_ticker(self): self.report["visibility_python_ticker_registered"] = True; self.reject()
    def test_no_pixels_claim(self): self.report["visibility_physical_pixels_tested"] = True; self.reject()
    def test_full_matrix_required(self): self.report["visibility_cases"].pop(); self.reject()
    def test_native_possession_regression_remains_required(self): self.report["natural_startup_possession"]["factories"] = 0; self.reject()
    def test_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterVisibilityResult=x"]), "uep_lyra_characters.visibility_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterVisibilityResult=x"]))
