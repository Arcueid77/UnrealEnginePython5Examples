"""Two-owner native Melee report mutations, not actual network execution."""
import copy
import unittest
from test_melee_activation_contract import report as single_report
from uep_lyra_abilities.melee_activation_network_contract import TRIALS, validate


def reports():
    base = single_report(); by_case = {(row["name"], row["profile"]): row for row in base["cases"]}
    values = {}
    for peer, player in (("A", 1), ("B0", 2)):
        value = copy.deepcopy(base); value.update(peer=peer, player_id=player, run_id="same-run", native_role=2, native_net_mode="Client", native_network_activation_tested=True, cases=[])
        for index, pair in enumerate(TRIALS):
            row = copy.deepcopy(by_case[pair]); row["index"] = index; row["stats"]["authority_trace_entries"] = 0
            if row["intervention"] is not None:
                row["intervention"].update(authority_confirmed=True, native_entry="ue.set_mixin_profile" if pair[0] == "profile-switch" else "GameplayAbility.K2_CancelAbility")
            value["cases"].append(row)
        value["shutdown"] = dict(active_count=0, scopes_created=3, scopes_closed=3, errors=[])
        values[peer] = value
    server = dict(status="passed", error=None, peer="server", run_id="same-run", native_net_mode="DedicatedServer", actual_granted_primary_instances=True,
        server_waited_for_client_process_exit=True, profiles_restored=True, specs_config_unchanged=True, player_ids=dict(A=1, B0=2),
        activation_event_replayed=False, task_callbacks_replayed=False, ability_granted_by_fixture=False, health_or_raw_velocity_written=False,
        trace_damage_business_migrated=False, full_acceptance=False, packaged_runtime=False,
        shutdown=dict(active_count=0, scopes_created=6, scopes_closed=6, errors=[]), cases=[])
    for peer in ("A", "B0"):
        for index, pair in enumerate(TRIALS):
            owner = values[peer]["cases"][index]; python = pair[1] == "Python"
            row = copy.deepcopy(owner); row.update(target=peer, native_role=3, authority_ready_sent=True, foreign_owner_unchanged=True,
                client=dict(run_id="same-run", peer=peer, index=index, row=copy.deepcopy(owner)))
            row["stats"].update(authority_trace_entries=int(python), native_ends=int(python), fallback_native_ends=int(not python),
                completed=0, blend_out=0, interrupted=0, cancelled=0)
            server["cases"].append(row)
    values["server"] = server; return values


class MeleeNetworkActivationModels(unittest.TestCase):
    def setUp(self): self.values = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError)): validate(self.values)
    def test_complete_synthetic_shape_not_native_execution(self): self.assertEqual(validate(self.values)["actual_native_owner_requests"], 12)
    def test_no_fake_native_client_role(self): self.values["A"]["native_role"] = 3; self.reject()
    def test_two_actual_owners_required(self): self.values["B0"]["player_id"] = 1; self.reject()
    def test_authority_activation_not_local_replay(self): self.values["server"]["activation_event_replayed"] = True; self.reject()
    def test_authority_real_montage_confirmation_required(self): self.values["server"]["cases"][0]["authority_ready_sent"] = False; self.reject()
    def test_owner_intervention_waits_for_authority(self): self.values["A"]["cases"][1]["intervention"]["authority_confirmed"] = False; self.reject()
    def test_foreign_native_owner_stays_unchanged(self): self.values["server"]["cases"][0]["foreign_owner_unchanged"] = False; self.reject()
    def test_authority_trace_entry_is_server_only(self): self.values["A"]["cases"][3]["stats"]["authority_trace_entries"] = 1; self.reject()
    def test_native_scope_must_close(self): self.values["server"]["shutdown"]["active_count"] = 1; self.reject()
    def test_both_worlds_without_any_montage_callback_rejected(self):
        row = self.values["A"]["cases"][3]; row["stats"]["blend_out"] = 0
        self.values["server"]["cases"][3]["client"]["row"] = copy.deepcopy(row); self.reject()
    def test_actual_client_process_exit_required(self): self.values["server"]["server_waited_for_client_process_exit"] = False; self.reject()
    def test_cannot_accept_damage_from_no_damage_activation(self): self.values["server"]["trace_damage_business_migrated"] = True; self.reject()
    def test_commandlet_is_disarmed(self):
        from uep_lyra_hud.startup import validation_module
        flag = "-UEPMeleeActivationNetworkResult=x"
        self.assertEqual(validation_module([flag]), "uep_lyra_abilities.melee_activation_network_validation")
        self.assertIsNone(validation_module(["-run=Py", flag]))
