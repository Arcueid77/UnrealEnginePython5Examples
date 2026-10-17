"""Synthetic native-report rejection models, never proof of an RPC transmission."""
import ast
import copy
from pathlib import Path
import unittest
from uep_lyra_abilities.dash_rpc_input_contract import PLAN, TRIALS, PEERS, CLASS, validate


def reports():
    server = dict(status="passed", error=None, server_waited_for_client_process_exit=True,
        original_profiles_restored=True, specs_and_configuration_preserved=True, native_playing_gate=dict(native_playing_phase=True),
        rpc_receiver_replayed=False, activation_event_replayed=False, native_rpc_bypassed=False, gameplay_state_delivered_by_files=False,
        whole_dash_activation_migrated=False, full_acceptance=False, player_ids=dict(A=1, B0=2), run_id="run", cases=[], native_pose_resets=[])
    values = dict(server=server)
    for peer in PEERS:
        client = dict(status="passed", error=None, native_role=2, native_net_mode="Client", peer=peer, run_id="run", player_id=server["player_ids"][peer],
            rpc_receiver_replayed=False, activation_event_replayed=False, ability_granted_by_fixture=False, ability_direction_montage_written_by_fixture=False,
            health_written_by_fixture=False, raw_velocity_written_by_fixture=False, gameplay_state_delivered_by_files=False, physical_input_tested=False,
            enhanced_input_tested=False, whole_dash_activation_migrated=False, dash_task_business_migrated=False, movement_parity_certified=False,
            full_acceptance=False, packaged_runtime=False, request_entry="ASC.TryActivateAbilityByClass", movement_intent_entry="Pawn.AddMovementInput",
            actual_ability_class=CLASS, actual_granted_primary_instance=True, profile_restored=True, specs_unchanged=True, native_configuration_unchanged=True, cases=[])
        values[peer] = client
        previous = dict(direction=[0., 0., 0.], montage=None)
        for index, (name, profile) in enumerate(TRIALS):
            python = profile == "Python"; payload = dict(direction=[1., 0., 0.] if name == "forward" else [0., -1., 0.], montage="native-"+name)
            row = dict(index=index, name=name, profile=profile, native_request_accepted=True,
                native_active_observed=True, native_root_motion_task_observed=True, native_montage_task_observed=True, native_ability_ended=True,
                quiet_after_end=True, cooldown_repeat_rejected=True, native_configuration_unchanged=True, specs_unchanged=True,
                native_tasks_after=0, max_motion_distance=20., max_native_speed=1850., chosen=copy.deepcopy(payload),
                rpc_counters=dict(python_calls=0, fallback_calls=0), selector_counters=dict(python_calls=int(python), fallback_calls=int(not python)))
            client["cases"].append(row)
            authority = dict(target=peer, index=index, profile=row["profile"], name=row["name"], native_role=3, actual_ability_class=CLASS,
                actual_receiver_authority=True, native_active_observed=True, native_root_motion_task_observed=True, native_montage_task_observed=True,
                native_tasks_after=0, native_ability_ended=True, foreign_owner_unchanged=True, quiet_after_end=True, native_configuration_unchanged=True,
                specs_unchanged=True, rpc_counters=dict(python_calls=int(python), fallback_calls=int(not python)), received=copy.deepcopy(payload), stored=copy.deepcopy(payload),
                stores_before_rpc=copy.deepcopy(previous),
                client=dict(row=copy.deepcopy(row)))
            server["cases"].append(authority); server["native_pose_resets"].append(dict(native_api="K2_TeleportTo", succeeded=True))
            previous = copy.deepcopy(payload)
    return values


class DashRPCInputContractModels(unittest.TestCase):
    def setUp(self): self.values = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError, TypeError)): validate(self.values)
    def test_complete_report_shape_is_only_a_model(self): self.assertEqual(validate(self.values)["actual_native_server_rpc_trials"], 8)
    def test_missing_owner_trial(self): self.values["A"]["cases"].pop(); self.reject()
    def test_missing_authority_trial(self): self.values["server"]["cases"].pop(); self.reject()
    def test_no_receiver_replay(self): self.values["server"]["rpc_receiver_replayed"] = True; self.reject()
    def test_no_activation_event_replay(self): self.values["A"]["activation_event_replayed"] = True; self.reject()
    def test_no_native_rpc_bypass(self): self.values["server"]["native_rpc_bypassed"] = True; self.reject()
    def test_no_gameplay_file_transport(self): self.values["server"]["gameplay_state_delivered_by_files"] = True; self.reject()
    def test_selected_python_exact_once(self): self.values["server"]["cases"][2]["rpc_counters"]["python_calls"] = 2; self.reject()
    def test_python_cannot_also_execute_fallback(self): self.values["server"]["cases"][2]["rpc_counters"]["fallback_calls"] = 1; self.reject()
    def test_client_must_not_run_authority_receiver(self): self.values["A"]["cases"][0]["rpc_counters"]["fallback_calls"] = 1; self.reject()
    def test_rpc_payload_not_just_native_task_success(self): self.values["server"]["cases"][0]["stored"]["direction"][0] = -1.; self.reject()
    def test_montage_identity_not_just_motion(self): self.values["server"]["cases"][0]["stored"]["montage"] = "wrong"; self.reject()
    def test_received_payload_must_match_independent_owner(self): self.values["server"]["cases"][0]["received"]["direction"][0] = .5; self.reject()
    def test_real_server_authority_required(self): self.values["server"]["cases"][0]["actual_receiver_authority"] = False; self.reject()
    def test_real_owned_primary_class_required(self): self.values["A"]["actual_ability_class"] = "fake"; self.reject()
    def test_two_actual_owners_required(self): self.values["server"]["player_ids"]["B0"] = 1; self.reject()
    def test_foreign_owner_invariance(self): self.values["server"]["cases"][0]["foreign_owner_unchanged"] = False; self.reject()
    def test_retained_root_motion_task_must_be_observed(self): self.values["server"]["cases"][0]["native_root_motion_task_observed"] = False; self.reject()
    def test_native_task_cleanup_required(self): self.values["server"]["cases"][0]["native_tasks_after"] = 1; self.reject()
    def test_late_dispatch_is_failure(self): self.values["server"]["cases"][0]["quiet_after_end"] = False; self.reject()
    def test_collision_checked_pose_fixture_required(self): self.values["server"]["native_pose_resets"][0]["succeeded"] = False; self.reject()
    def test_repeat_request_still_native_rejected(self): self.values["A"]["cases"][0]["cooldown_repeat_rejected"] = False; self.reject()
    def test_not_full_dash_migration(self): self.values["server"]["whole_dash_activation_migrated"] = True; self.reject()
    def test_waits_for_real_client_process_exits(self): self.values["server"]["server_waited_for_client_process_exit"] = False; self.reject()
    def test_fixture_does_not_call_rpc_or_write_input_fields(self):
        source = (Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/dash_rpc_input_network_validation.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args or not isinstance(node.func, ast.Attribute): continue
            first = node.args[0]
            if node.func.attr == "call_function" and isinstance(first, ast.Constant): self.assertNotIn(first.value, ("SendInfo", "K2_ActivateAbility", "UEPDashStoreRemoteInput"))
            if node.func.attr == "set_property" and isinstance(first, ast.Constant): self.assertNotIn(first.value, ("Direction", "Montage", "Velocity"))
    def test_startup_is_explicit_and_commandlets_disarmed(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPDashRPCInputNetworkResult=x"]), "uep_lyra_abilities.dash_rpc_input_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPDashRPCInputNetworkResult=x"]))
    def test_native_net_mode_is_read_not_a_fixture_label(self):
        source = (Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/dash_rpc_input_network_validation.py").read_text(encoding="utf-8")
        self.assertIn('net_mode = str(bridge.call_function("CaptureSnapshot").NetMode)', source)
        self.assertIn('native_net_mode=net_mode', source)
        self.assertNotIn('native_net_mode="Client"', source)
    def test_stale_matching_native_values_cannot_mask_missing_python_stores(self):
        row = self.values["server"]["cases"][2]; row["stores_before_rpc"] = copy.deepcopy(row["received"]); self.reject()
    def test_python_trials_alternate_native_data_without_fixture_sentinel_writes(self):
        self.assertEqual(TRIALS, (("forward", "BlueprintFallback"), ("left", "BlueprintFallback"), ("forward", "Python"), ("left", "Python")))
