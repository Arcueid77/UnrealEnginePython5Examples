"""Synthetic native-death/lifetime/montage report guards, not runtime proof."""
import copy
import ast
from pathlib import Path
import unittest
import test_character_ragdoll_contract as ragdoll_models
from test_character_equipment_hide_contract import counts as hide_counts
from uep_lyra_characters.death_started_contract import validate, SCENARIOS, SIGHT


def entry(profile, *, resumed=True, current=None, configured=None):
    current = current or profile; configured = ["montage-A", "montage-B"] if configured is None else configured; py = profile == "Python"
    events = (["montage", "sight", "delay"]+(["resume", "ragdoll", "hide", "death"] if resumed else [])) if py else ["fallback"]
    return dict(python_calls=int(py), fallback_calls=int(not py), montage_calls=int(py), unregister_calls=int(py), missing_sense_noops=0,
        delay_requests=int(py), resumes=int(py and resumed), fallback_resumes=int(py and resumed and current == "BlueprintFallback"),
        ragdoll_forwards=int(py and resumed), hide_forwards=int(py and resumed), death_forwards=int(py and resumed), uuid=123 if py else None,
        pending=py and not resumed, trace=[dict(event=value, frame=10 if index < 3 else 30, game_seconds=1. if index < 3 else 1.3) for index, value in enumerate(events)],
        last_start=dict(owning_actor="actual-actor", montage=configured[0] if configured else None, montage_count=len(configured), montage_index=0,
            duration=.3, frame=10, game_seconds=1.) if py else None, last_resume=dict(frame=30, game_seconds=1.3) if py and resumed else None)


def add_native(row, profile, **kwargs):
    configured = kwargs.get("configured", ["montage-A", "montage-B"])
    row.update(actor_path="actual-actor", death_started_counters=entry(profile, **kwargs), health_delegate_manually_replayed=False,
        native_prefix_health=0, native_sight_sources_before=[SIGHT], native_prefix_sight_sources=[], native_sight_sources_after=[],
        configured_death_montages=list(configured), native_prefix_current_montage=configured[0] if configured else None,
        maximum_observed_world_delta=.016, signal_actual_owning_actor="actual-actor",
        death_signal_observer=dict(created=1, closed=1, active=0, callbacks=1, errors=[]), native_after_damage_current_montage="later-hit-react")
    return row


def upgrade(value):
    value.update(death_started_business_migrated=True, death_receiver_called_by_fixture=False, death_native_delay_backend="Delay",
        death_python_ticker_or_rooting=False, empty_death_endpoint_retained=True)
    return value


def report():
    value = upgrade(ragdoll_models.report()); value["death_started_cases"] = []
    for row in value["equipment_hide_cases"][-2:]: add_native(row, row["profile"])
    for name, profile in SCENARIOS:
        destroyed = name == "destroy-pending"; current = ("Python" if profile == "BlueprintFallback" else "BlueprintFallback") if name == "switch-pending" else profile
        configured = [] if name == "empty-montages" else ["montage-A"] if name == "single-montage" else ["montage-A", "montage-B"]
        row = add_native(copy.deepcopy(value["equipment_hide_cases"][-1]), profile, resumed=not destroyed, current=current, configured=configured)
        row.update(death_case=name, entry_profile=profile, profile_before_resume=current, native_lethal_gas_death=True, native_health_after=0,
            destroyed_pending=destroyed, callback_receiver_called_by_fixture=False, montage_configuration_restored_before_destroy=True,
            death_started_quiet_after_destroy=True, destroyed_owner_observed_for_game_seconds=.8, no_ragdoll_after_destroy=True,
            natural_ragdoll_counters=ragdoll_models.counts(current), counters=hide_counts(current == "Python"))
        value["death_started_cases"].append(row)
    return value


class CharacterDeathStartedReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.report)
    def row(self): return self.report["death_started_cases"][1]
    def test_complete_shape_is_only_model(self): self.assertEqual(validate(self.report)["native_death_started_pairs"], 5)
    def test_real_health_death_not_receiver_replay(self): self.row()["health_delegate_manually_replayed"] = True; self.reject()
    def test_actual_native_signal_witness_required(self): self.row()["death_signal_observer"]["callbacks"] = 0; self.reject()
    def test_signal_observer_must_close(self): self.row()["death_signal_observer"]["active"] = 1; self.reject()
    def test_actual_signal_actor_required(self): self.row()["signal_actual_owning_actor"] = "foreign"; self.reject()
    def test_later_hit_react_is_recorded_not_used_as_death_montage(self): self.assertTrue(validate(self.report)["native_death_started_orchestration_accepted"])
    def test_native_health_must_be_zero(self): self.row()["native_prefix_health"] = 100; self.reject()
    def test_sight_registered_before_required(self): self.row()["native_sight_sources_before"] = []; self.reject()
    def test_sight_actually_removed_required(self): self.row()["native_prefix_sight_sources"] = [SIGHT]; self.reject()
    def test_other_native_senses_must_remain_registered(self): self.row()["native_sight_sources_before"].append("native-hearing"); self.reject()
    def test_actual_montage_not_just_python_selection(self): self.row()["native_prefix_current_montage"] = "foreign"; self.reject()
    def test_original_order_required(self): self.row()["death_started_counters"]["trace"].reverse(); self.reject()
    def test_native_random_bounds_required(self): self.row()["death_started_counters"]["last_start"]["duration"] = 2.; self.reject()
    def test_actual_actor_payload_required(self): self.row()["death_started_counters"]["last_start"]["owning_actor"] = "foreign"; self.reject()
    def test_native_game_clock_resume_required(self): self.row()["death_started_counters"]["last_resume"]["game_seconds"] = 1.; self.reject()
    def test_destroyed_owner_observed_beyond_maximum_delay(self): self.report["death_started_cases"][7]["destroyed_owner_observed_for_game_seconds"] = .1; self.reject()
    def test_destroyed_owner_may_not_resume(self): self.report["death_started_cases"][7]["death_started_counters"]["resumes"] = 1; self.reject()
    def test_python_pending_action_uses_current_fallback_without_prefix_replay(self): self.report["death_started_cases"][-1]["death_started_counters"]["fallback_resumes"] = 0; self.reject()
    def test_empty_montage_control_is_actually_empty(self): self.report["death_started_cases"][5]["configured_death_montages"] = ["montage-A"]; self.reject()
    def test_no_python_ticker_or_rooting_claim(self): self.report["death_python_ticker_or_rooting"] = True; self.reject()
    def test_prior_native_ragdoll_impulse_still_required(self): self.report["ragdoll_cases"][3]["native_after_physics_step"]["velocity"] = [0., 0., 0.]; self.reject()
    def test_owned_observer_cleanup_required(self): self.row()["owned_team_observers_collected"] = False; self.reject()
    def test_native_owner_wait_has_initialized_delta_before_first_tick(self):
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/death_started_observation.py"
        cls = next(node for node in ast.parse(source.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "NaturalTrial")
        constructor = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
        self.assertIsInstance(constructor.body[0], ast.Assign); self.assertEqual(constructor.body[0].targets[0].attr, "max_delta")
    def test_native_uuid_is_identity_not_counter_delta(self):
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/death_started_observation.py"
        node = next(node for node in ast.parse(source.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef) and node.name == "delta")
        namespace = dict(copy=copy); exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(source), "exec"), namespace)
        self.assertEqual(namespace["delta"](dict(python_calls=1, uuid=123, trace=[]), dict(python_calls=0, uuid=None, trace=[])), dict(python_calls=1, uuid=123, trace=[]))
