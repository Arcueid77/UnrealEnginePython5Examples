"""Synthetic report rejection tests; not Unreal/multiplayer execution proof."""

import ast
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_ability_progress_protocol import validate_progress, validate_scopes
from uep_lyra_weapon_protocol import validate_reports
from test_reticle_host_protocol import reports_fixture as host_fixture


def checkpoint():
    ack = {"phase": "join_a", "player": {"controller_path": "pc-a", "pawn_path": "pawn-a", "world_token": "world-a"}}
    values = {"duration": 1.25, "start": 30.0, "visibility": 1, "text": "-0", "percent": 1.01, "active_range": [0.0] * 4}
    value = {"production_widget": True, "class": "W_AbilityProgress_C", "profile": "Python", "widget": "production-progress",
             "controller": "pc-a", "pawn": "pawn-a", "world_token": "world-a", "phase": "join_a", "completed": True,
             "synthetic_local_messages": True, "native_interaction_producer_tested": False,
             "replicated_duration_message_tested": False, "python_tick_called_by_probe": False,
             "automatic_tick_delta": 80, "owner_deliveries": 1, "foreign_rejections": 1,
             "comparisons": 20, "visible_comparisons": 18,
             "foreign_instigator_kind": "owning-controller-not-pawn", "blueprint": dict(values), "python": dict(values)}
    return value, ack


def reports_fixture():
    reports = host_fixture()
    for row in reports["server"]["phases"]:
        for ack in row["acks"].values():
            value, _ = checkpoint()
            value.update(controller=ack["player"]["controller_path"], pawn=ack["player"]["pawn_path"],
                         world_token=ack["player"]["world_token"], phase=ack["phase"])
            ack["combat_hud"]["ability_progress"] = value
    for peer, report in reports.items():
        report["ability_progress_slice"] = {"enabled": True}
        report["shutdown"]["ability_progress_observers"] = {"active_count": 0, "scopes_created": 0 if peer == "server" else 3,
                                                           "scopes_closed": 0 if peer == "server" else 3, "errors": []}
        if peer != "server":
            report["phases"] = copy.deepcopy([row for row in reports["server"]["phases"] if peer in row["acks"]])
    return reports


def validate(reports):
    return validate_reports(reports, "run", combat_hud=True, production_reticles=True, reticle_hosts=True, ability_progress=True)


class AbilityProgressProtocolTests(unittest.TestCase):
    def test_complete_checkpoint(self):
        validate_progress(*checkpoint())

    def test_complete_synthetic_lane(self):
        self.assertTrue(validate(reports_fixture())["ability_progress_acceptance"])

    def test_ownership_world_and_phase_must_match(self):
        for key in ("controller", "pawn", "world_token", "phase"):
            value, ack = checkpoint()
            value[key] = "foreign"
            with self.assertRaises(RuntimeError):
                validate_progress(value, ack)

    def test_wrong_class_profile_and_nonproduction_fail(self):
        for key, changed in (("class", "other"), ("profile", "BlueprintFallback"), ("production_widget", False)):
            value, ack = checkpoint()
            value[key] = changed
            with self.assertRaises(RuntimeError):
                validate_progress(value, ack)

    def test_manufactured_or_missing_tick_fails(self):
        for key, changed in (("automatic_tick_delta", 0), ("automatic_tick_delta", True), ("python_tick_called_by_probe", True)):
            value, ack = checkpoint()
            value[key] = changed
            with self.assertRaises(RuntimeError):
                validate_progress(value, ack)

    def test_missing_visible_comparison_fails(self):
        for key, changed in (("comparisons", 1), ("comparisons", True), ("visible_comparisons", 0), ("visible_comparisons", True)):
            value, ack = checkpoint()
            value[key] = changed
            with self.assertRaises(RuntimeError):
                validate_progress(value, ack)

    def test_producer_boundary_must_be_declared(self):
        for key, changed in (("synthetic_local_messages", False), ("native_interaction_producer_tested", True),
                             ("replicated_duration_message_tested", True), ("foreign_instigator_kind", "remote-player")):
            value, ack = checkpoint()
            value[key] = changed
            with self.assertRaises(RuntimeError):
                validate_progress(value, ack)

    def test_missing_duplicate_and_bool_delivery_counts_fail(self):
        for key in ("owner_deliveries", "foreign_rejections"):
            for changed in (0, 2, True):
                value, ack = checkpoint()
                value[key] = changed
                with self.assertRaises(RuntimeError):
                    validate_progress(value, ack)

    def test_invalid_numeric_and_unfinished_state_fail(self):
        for key, changed in (("duration", 0.0), ("duration", True), ("start", float("nan")),
                             ("percent", float("inf")), ("percent", 0.99), ("visibility", 0), ("visibility", True),
                             ("text", "different"), ("active_range", [1.0] * 4)):
            value, ack = checkpoint()
            value["python"][key] = changed
            with self.assertRaises(RuntimeError):
                validate_progress(value, ack)

    def test_old_lane_cannot_certify_progress(self):
        with self.assertRaisesRegex(RuntimeError, "progress validation lane"):
            validate(host_fixture())

    def test_missing_checkpoint_fails(self):
        reports = reports_fixture()
        del reports["server"]["phases"][0]["acks"]["A"]["combat_hud"]["ability_progress"]
        with self.assertRaisesRegex(RuntimeError, "progress checkpoint"):
            validate(reports)

    def test_progress_requires_combat_lane(self):
        with self.assertRaisesRegex(RuntimeError, "requires combat"):
            validate_reports({}, "run", ability_progress=True)

    def test_scope_leak_or_invalid_counter_fails(self):
        for key, changed in (("active_count", 1), ("active_count", False), ("scopes_closed", 2), ("errors", ["failure"])):
            final = {"active_count": 0, "scopes_created": 3, "scopes_closed": 3, "errors": []}
            final[key] = changed
            with self.assertRaises(RuntimeError):
                validate_scopes(final, "A")

    def test_server_ui_or_missing_client_evidence_fails(self):
        for peer, count in (("server", 1), ("A", 0)):
            reports = reports_fixture()
            final = reports[peer]["shutdown"]["ability_progress_observers"]
            final["scopes_created"] = final["scopes_closed"] = count
            with self.assertRaisesRegex(RuntimeError, "server duration UI or missing client"):
                validate(reports)

    def test_phase_activation_is_not_in_frame_input_loop(self):
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_weapon_network.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        locations = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                     and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                             and call.func.attr == "begin" for call in ast.walk(node))]
        self.assertEqual(locations, ["_client_tick"])


if __name__ == "__main__":
    unittest.main()
