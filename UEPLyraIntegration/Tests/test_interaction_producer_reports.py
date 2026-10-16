"""The external gate must reject incomplete/overclaimed original-world proof."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1]/"Tools/validate_interaction_producer_reports.py"
spec = importlib.util.spec_from_file_location("_interaction_producer_gate", path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def reports():
    result = {}
    for peer in ("server", "A", "B0"):
        result[peer] = dict(schema_version=1, status="passed", error=None, peer=peer, cases=[],
            native_interaction_producer_tested=True, original_world_restored=True, test_owned_ui_pair=True,
            player_id=1 if peer == "A" else 2, server_waited_for_client_process_exit=peer == "server",
            shutdown=dict(active_count=0, errors=[], scopes_created=3, scopes_closed=3))
        result[peer].update({name: False for name in gate.FALSE})
    for index, target in enumerate(("A", "B0")):
        first = dict(duration=.5, start=2., visibility=0, text="0.5", percent=.1)
        final = dict(duration=.5, start=2., visibility=1, text="0", percent=1.1)
        row = dict(case_index=index, target=target, passed=True, same_class=True, native_api="TriggerInteraction",
            original_sit_class=gate.SIT, original_interactor_count=2, original_native_options=1,
            native_duration_deliveries=1, automatic_ticks=10,
            first_observed=dict(native_sit_instances=2, python=first, blueprint=copy.deepcopy(first)),
            final_python=final, final_blueprint=copy.deepcopy(final))
        result[target]["cases"] = [copy.deepcopy(row)]
        result["server"]["cases"].append(copy.deepcopy(row))
    return result


class OriginalInteractionGate(unittest.TestCase):
    def test_two_original_owners_and_exact_models_pass_bounded_gate(self):
        self.assertEqual(gate.validate(reports())["owners"], 2)
        self.assertFalse(gate.validate(reports())["full_acceptance"])

    def test_rejects_fake_broadcast_and_unsupported_input_claim(self):
        for field in ("synthetic_duration_broadcast", "python_handler_replayed", "enhanced_input_pipeline_tested",
                      "replicated_duration_message_tested", "production_widget_reachability_tested"):
            data = reports(); data["A"][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(data)

    def test_rejects_host_first_exit_race(self):
        data = reports(); data["server"]["server_waited_for_client_process_exit"] = False
        with self.assertRaises(RuntimeError): gate.validate(data)

    def test_rejects_scope_leak_and_same_player(self):
        for change in (lambda data: data["A"]["shutdown"].update(active_count=1),
                       lambda data: data["A"].update(player_id=2)):
            data = reports(); change(data)
            with self.assertRaises(RuntimeError): gate.validate(data)

    def test_rejects_original_grant_silently_deduplicated(self):
        data = reports()
        for row in (data["server"]["cases"][0], data["A"]["cases"][0]): row["original_interactor_count"] = 1
        with self.assertRaises(RuntimeError): gate.validate(data)

    def test_rejects_missing_native_ability_and_unobserved_visible_countdown(self):
        for field in ("native_sit_instances", "visibility"):
            data = reports()
            for row in (data["server"]["cases"][0], data["A"]["cases"][0]):
                if field == "native_sit_instances": row["first_observed"][field] = 0
                else:
                    row["first_observed"]["python"][field] = row["first_observed"]["blueprint"][field] = 1
            with self.assertRaises(RuntimeError): gate.validate(data)

    def test_rejects_inconsistent_or_nonfinite_model(self):
        for value in (float("nan"), .8):
            data = reports()
            for row in (data["server"]["cases"][0], data["A"]["cases"][0]): row["first_observed"]["python"]["percent"] = value
            with self.assertRaises(RuntimeError): gate.validate(data)
