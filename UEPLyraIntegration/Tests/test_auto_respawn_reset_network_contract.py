"""Reject manufactured/two-owner Reset evidence independently of the fixture."""
import ast
import copy
from pathlib import Path
import unittest
from test_auto_respawn_reset_contract import report as standalone
from uep_lyra_abilities import auto_respawn_reset_network_contract as gate


def reports():
    base = standalone(); rows = base["cases"]
    result = {}
    for peer in ("server",)+gate.PEERS:
        result[peer] = dict(base, cases=[], peer=peer, run_id="test", network_acceptance=True, foreign_cases=[],
            gameplay_state_delivered_by_files=False, native_rpc_bypassed=False,
            observer_shutdown=dict(created=16, closed=16, active=0))
    server = result["server"]
    server.update(server_waited_for_client_process_exit=True, all_owners_restored=True, owners_restored_before_client_release=True,
        native_playing_gate=dict(native_playing_phase=True), player_ids=dict(A=1, B0=2),
        owner_restoration={peer: dict(profile=True, specs=True, delay=True, alive=True) for peer in gate.PEERS})
    for peer in gate.PEERS:
        result[peer].update(player_id=server["player_ids"][peer], native_net_mode="Client", local_reset_requests=0,
            local_damage_applied=False, authority_phase_gate_observed=True)
    for position, (target, index) in enumerate((target, index) for target in gate.PEERS for index in range(gate.TRIALS)):
        owner_id = server["player_ids"][target]
        authority, owner = copy.deepcopy(rows[index]), copy.deepcopy(rows[index])
        authority["ui_valid_before"] = authority["ui_valid_after"] = False
        for row in (authority, owner):
            row.update(position=position, target=target, index=index, player_id=owner_id)
            for message in row["event_messages"]+row["reset_messages"]: message["player_id"] = owner_id
        authority["event_messages"] = [row for row in authority["event_messages"] if row["channel"] != "Ability.Respawn.Completed.Message"]
        authority["event_counters"]["cosmetic_completion_messages"] = 0
        owner["event_counters"].update(native_restarts=0, native_completion_rpcs=0, cosmetic_completion_messages=0)
        result[target]["cases"].append(owner)
        other = "B0" if target == "A" else "A"
        foreign_counts = {key: 0 for key in authority["activation_counters"]}
        foreign = dict(position=position, target=target, local_owner_unchanged=True, observer_closed=True, reset_messages=[],
            activation_counters=foreign_counts, event_messages=[dict(channel="Ability.Respawn.Completed.Message", player_id=owner_id,
                owner_matches=False, verb="Ability.Respawn.Completed.Message", magnitude=1., target_is_null=True, instigator_tags=[], target_tags=[], context_tags=[])])
        result[other]["foreign_cases"].append(foreign)
        stats = copy.deepcopy(foreign_counts)
        if authority["profile"] == "Python": stats.update(reset_messages=1, foreign_resets=1)
        else: stats["fallback_reset_messages"] = 1
        authority.update(foreign_owner_unchanged=True, foreign_activation_counters=stats,
            owner_ack=dict(run_id="test", peer=target, position=position, index=index, row=copy.deepcopy(owner)),
            foreign_ack=dict(run_id="test", peer=other, position=position, row=copy.deepcopy(foreign)))
        server["cases"].append(authority)
    return result


class NativeResetNetworkModels(unittest.TestCase):
    def test_bounded_synthetic_shape(self): self.assertEqual(gate.validate(reports())["authority_trials"], 16)

    def test_both_actual_owners_and_every_pair_required(self):
        for mutate in (lambda r: r.pop("B0"), lambda r: r["server"]["cases"].pop(), lambda r: r["A"]["cases"].pop()):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_client_cannot_trigger_reset_damage_or_restart(self):
        for mutate in (lambda r: r["A"].update(local_reset_requests=1), lambda r: r["A"].update(local_damage_applied=True),
            lambda r: r["A"]["cases"][1]["event_counters"].update(native_restarts=1)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_server_foreign_owner_must_filter_native_reset(self):
        for mutate in (lambda r: r.update(foreign_owner_unchanged=False), lambda r: r["foreign_activation_counters"].update(foreign_resets=0),
            lambda r: r["foreign_activation_counters"].update(resets_handled=1)):
            value = reports(); mutate(value["server"]["cases"][1])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_foreign_client_receives_completion_not_replicated_reset_router_payload(self):
        for mutate in (lambda r: r.update(reset_messages=[dict(channel="GameplayEvent.Reset")]),
            lambda r: r.update(event_messages=[]), lambda r: r["activation_counters"].update(reset_messages=1)):
            value = reports(); mutate(value["B0"]["foreign_cases"][0])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_ack_must_equal_independently_read_reports(self):
        value = reports(); value["server"]["cases"][0]["owner_ack"]["row"]["new_pawn"] = "fabricated"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_real_exit_restoration_scopes_and_no_full_asset_overclaim(self):
        for mutate in (lambda r: r.update(server_waited_for_client_process_exit=False), lambda r: r.update(all_owners_restored=False),
            lambda r: r["observer_shutdown"].update(active=1), lambda r: r.update(full_auto_respawn_acceptance=True)):
            value = reports(); mutate(value["server"])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_client_has_no_gameplay_producer_or_native_equipment_recovery(self):
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_reset_network_validation.py"
        source = path.read_text(encoding="utf-8"); tree = ast.parse(source)
        client = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Client")
        body = ast.get_source_segment(source, client)
        calls = [node for node in ast.walk(client) if isinstance(node, ast.Call)]
        for call in calls:
            if isinstance(call.func, ast.Attribute):
                self.assertNotIn(call.func.attr, ("trigger_reset", "apply", "add_to_root"))
                if call.func.attr == "call_function" and call.args and isinstance(call.args[0], ast.Constant):
                    self.assertNotIn(call.args[0].value, ("SendGameplayEventToActor", "K2_GiveAbility", "SetActiveSlotIndex"))
        self.assertIn("self.allow_native_equipment_recovery = False", body)

    def test_ui_must_preserve_measured_role_baseline_not_invent_a_server_registration(self):
        for mutate in (lambda r: r.update(ui_valid_after=True), lambda r: r.update(ui_valid_before=True)):
            value = reports(); mutate(value["server"]["cases"][0])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)
