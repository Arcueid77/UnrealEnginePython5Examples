"""Synthetic helper evidence rejects missing routes/output/state/cleanup."""
import copy
import ast
import math
from pathlib import Path
import types
import unittest
from uep_lyra_abilities.dash_selector_contract import PLAN, FIELDS, CLASS, validate, network


def report():
    montages = {field: field+"-asset" for field in FIELDS}
    value = dict(status="passed", error=None, dash_selector_business_migrated=True, dash_activation_business_migrated=False, dash_rpc_movement_tested=False,
        fixture_activated_ability=False, fixture_granted_ability=False, gameplay_state_delivered_by_files=False, full_acceptance=False,
        packaged_runtime=False, physical_input_tested=False, actual_granted_primary_instance=True, ability_was_not_rooted=True,
        original_profile_restored=True, instance_configuration_restored=True, cdo_configuration_unchanged=True, native_specs_unchanged=True,
        quiet_after_helper_calls=True, actual_ability_class=CLASS, caller_roots=dict(created=1, released=1), original_montages=montages, cases=[])
    for case in PLAN:
        facing, movement = case["facing"], case["movement"]
        yaw = (math.degrees(math.atan2(movement[1], movement[0]))-math.degrees(math.atan2(facing[1], facing[0]))+180.)%360.-180.
        magnitude = abs(yaw); index = 0 if magnitude < 45. else 1 if magnitude > 135. else 2 if yaw < 0. else 3
        result = dict(DirectionalMontage=None if case["null_field"] == FIELDS[index] else montages[FIELDS[index]], BiasForwardMovement=index == 0)
        value["cases"].append(dict(input=copy.deepcopy(case), configuration_restored=True, native_state_before=dict(active=False), native_state_after=dict(active=False),
            blueprint=dict(profile="BlueprintFallback", result=copy.deepcopy(result), counters=dict(python_calls=0, fallback_calls=1)),
            python=dict(profile="Python", result=copy.deepcopy(result), counters=dict(python_calls=1, fallback_calls=0),
                last=dict(yaw=yaw, magnitude=magnitude, field=FIELDS[index], forward=index == 0))))
    return value


def reports():
    result = {peer: report() for peer in ("server", "A", "B0")}
    for index, (peer, value) in enumerate(result.items()): value.update(peer=peer, run_id="run", player_id=index, native_role=3 if peer == "server" else 2)
    result["server"].update(server_waited_for_client_process_exit=True, all_helper_owners_restored_before_release=True, other_authority_owner_unchanged=True)
    return result


class DashSelectorContractModels(unittest.TestCase):
    def setUp(self): self.value = report()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.value)
    def test_complete_shape_is_only_model(self): self.assertEqual(validate(self.value)["native_bp_python_selector_pairs"], 42)
    def test_exact_matrix(self): self.value["cases"].pop(); self.reject()
    def test_no_activation_claim(self): self.value["dash_activation_business_migrated"] = True; self.reject()
    def test_no_granted_test_ability(self): self.value["fixture_granted_ability"] = True; self.reject()
    def test_actual_primary_instance_required(self): self.value["actual_granted_primary_instance"] = False; self.reject()
    def test_actual_named_outputs_must_match_bp(self): self.value["cases"][0]["python"]["result"]["DirectionalMontage"] = "wrong"; self.reject()
    def test_named_boolean_must_match(self): self.value["cases"][0]["python"]["result"]["BiasForwardMovement"] = True; self.reject()
    def test_route_counter_not_original_fallthrough(self): self.value["cases"][0]["python"]["counters"]["fallback_calls"] = 1; self.reject()
    def test_no_gameplay_state_change(self): self.value["cases"][0]["native_state_after"]["active"] = True; self.reject()
    def test_null_configuration_restored(self): self.value["cases"][-1]["configuration_restored"] = False; self.reject()
    def test_profile_restored(self): self.value["original_profile_restored"] = False; self.reject()
    def test_cdo_is_not_changed(self): self.value["cdo_configuration_unchanged"] = False; self.reject()
    def test_no_actor_rooting(self): self.value["ability_was_not_rooted"] = False; self.reject()
    def test_caller_root_released(self): self.value["caller_roots"]["released"] = 0; self.reject()
    def test_quiet_window_required(self): self.value["quiet_after_helper_calls"] = False; self.reject()
    def test_native_spec_identity_preserved(self): self.value["native_specs_unchanged"] = False; self.reject()
    def test_native_three_world_shape(self): self.assertEqual(network(reports())["peer_worlds"], 3)
    def test_real_client_role_not_authority(self):
        values = reports(); values["A"]["native_role"] = 3
        with self.assertRaises(RuntimeError): network(values)
    def test_two_distinct_actual_owners(self):
        values = reports(); values["B0"]["player_id"] = values["A"]["player_id"]
        with self.assertRaises(RuntimeError): network(values)
    def test_server_last_actual_exit_gate(self):
        values = reports(); values["server"]["server_waited_for_client_process_exit"] = False
        with self.assertRaises(RuntimeError): network(values)
    def test_explicit_selectors_and_no_commandlet_fixture(self):
        from uep_lyra_hud.startup import validation_module
        for suffix, module in (("Result", "dash_selector_validation"), ("NetworkResult", "dash_selector_network_validation")):
            flag = "-UEPDashSelector"+suffix+"=x"
            self.assertEqual(validation_module([flag]), "uep_lyra_abilities."+module)
            self.assertIsNone(validation_module(["-run=Py", flag]))
    def test_server_checks_foreign_owner_before_release_not_after_disconnect(self):
        tree = ast.parse((Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/dash_selector_network_validation.py").read_text(encoding="utf-8"))
        server = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Server")
        tick = next(node for node in server.body if isinstance(node, ast.FunctionDef) and node.name == "tick")
        observed = dict(reads=0, releases=0, exits_ready=False)
        def token(root, name, run):
            if name.endswith("-exited.json"): return dict(exit_code=0) if observed["exits_ready"] else None
            return dict(complete=True)
        def publish(*args): observed["releases"] += 1
        namespace = dict(time=types.SimpleNamespace(monotonic=lambda: 0.), require=lambda good, message: self.assertTrue(good, message),
            token=token, atomic_write=publish)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[tick], type_ignores=[])), "dash-server-tick-model", "exec"), namespace)
        obj = types.SimpleNamespace(finished=False, started=0., phase="release", release_issued=False,
            root=Path("."), run="run", other_before=dict(owner="stable"), report={})
        def other_state():
            self.assertFalse(obj.release_issued, "released native Controller must not be read")
            observed["reads"] += 1; return obj.other_before
        obj.other_state = other_state
        obj.finish = lambda: setattr(obj, "finished", True)
        self.assertTrue(namespace["tick"](obj, .016))
        observed["exits_ready"] = True
        self.assertFalse(namespace["tick"](obj, .016))
        self.assertEqual((observed["reads"], observed["releases"]), (1, 1))
        self.assertTrue(obj.report["server_waited_for_client_process_exit"])
